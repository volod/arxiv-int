"""Unit coverage for canonical store hashing, DDL, and overlay findings."""

from pathlib import Path

import pytest

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel, load_schema_model_from_root
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.constants import (
    CANONICAL_SCHEMAS,
    HASH_MODULUS,
    HEAD_REVISION,
    PARTITIONED_TABLES,
    PROJECTION_METADATA_TABLES,
    ROLE_DBT,
    STORE_ROLES,
)
from arxiv_int.stores.postgres.ddl import (
    bucket_function_sql,
    correctness_index_sql,
    create_role_sql,
    embedding_profile_sql,
    fact_check_sql,
    grant_sql,
    owned_staging_sql,
    staging_table_sql,
)
from arxiv_int.stores.postgres.hashing import partition_bucket, partition_bucket_sql
from arxiv_int.stores.postgres.inspect_live import LiveStoreCatalog, PartitionSpec, store_findings
from arxiv_int.stores.postgres.load import (
    StagingRejectedError,
    fill_buckets,
    quality_frame,
    validate_rows,
)


def test_partition_bucket_is_stable_and_in_range() -> None:
    assert partition_bucket("doc-1") == partition_bucket("doc-1")
    assert partition_bucket("doc-1") != partition_bucket("doc-2")
    value = int(partition_bucket("doc-1"))
    assert 0 <= value < HASH_MODULUS
    assert "bit(28)" in partition_bucket_sql()
    assert "sha256" in bucket_function_sql()


def test_fill_buckets_uses_the_primary_key() -> None:
    rows = fill_buckets("corpus.documents", [{"document_id": "doc-1", "generation_id": "g"}])
    assert rows[0]["bucket"] == partition_bucket("doc-1")
    skipped = fill_buckets("corpus.documents", [{"document_id": None, "generation_id": "g"}])
    assert "bucket" not in skipped[0]


def test_fact_checks_and_grants_name_store_objects() -> None:
    checks = "\n".join(fact_check_sql())
    assert "ck_facts_object_xor_literal" in checks
    assert "ck_facts_provenance" in checks
    grants = "\n".join(grant_sql())
    assert ROLE_DBT in grants
    assert "derived" in grants
    assert "alembic_version" in grants
    assert "staging.documents" in staging_table_sql("corpus", "documents")
    assert "CREATE ROLE" in create_role_sql(ROLE_DBT)
    profiles = "\n".join(embedding_profile_sql())
    assert "enforce_embedding_profile" in profiles
    assert "ix_facts_subject_object_id" in "\n".join(correctness_index_sql())
    assert any("staging.documents" in item for item in owned_staging_sql())


def test_revision_0002_freezes_the_partitioned_table_list() -> None:
    root = discover_project_root(Path(__file__))
    text = (
        root / "src/arxiv_int/migrations/versions/0002_store_partitions_roles_constraints.py"
    ).read_text(encoding="utf-8")
    for schema, table, pk in PARTITIONED_TABLES:
        assert f'("{schema}", "{table}", "{pk}")' in text
    assert "CREATE SCHEMA IF NOT EXISTS derived" in text
    assert "arxiv_int_dbt" in text


def test_revision_0003_freezes_projection_metadata() -> None:
    root = discover_project_root(Path(__file__))
    text = (root / "src/arxiv_int/migrations/versions/0003_projection_metadata.py").read_text(
        encoding="utf-8"
    )
    for table in PROJECTION_METADATA_TABLES:
        assert f"ctl.{table}" in text
    assert 'revision: str = "0003"' in text
    assert "arxiv_int_pipeline" in text


def test_store_findings_report_missing_overlay_objects() -> None:
    catalog = LiveStoreCatalog(
        schemas=("corpus",),
        partitioned=(PartitionSpec("corpus.documents", "RANGE (bucket)", 2),),
        checks=(),
        roles=(),
        staging_tables=(),
        revision="0001",
        extensions=(),
    )
    findings = store_findings(catalog)
    assert any("missing schemas" in item for item in findings)
    assert any("HASH parents" in item for item in findings)
    assert any("expected 16" in item for item in findings)
    assert any("partition strategy" in item for item in findings)
    assert any("ck_facts_object_xor_literal" in item for item in findings)
    assert any("missing roles" in item for item in findings)
    assert any("staging.documents" in item for item in findings)
    assert any(f"expected {HEAD_REVISION!r}" in item for item in findings)


def test_store_findings_empty_when_overlay_matches() -> None:
    catalog = LiveStoreCatalog(
        schemas=(*CANONICAL_SCHEMAS, "staging", "derived"),
        partitioned=tuple(
            PartitionSpec(f"{schema}.{table}", f"HASH ({pk})", HASH_MODULUS)
            for schema, table, pk in PARTITIONED_TABLES
        ),
        checks=("ck_facts_object_xor_literal", "ck_facts_provenance", "ck_facts_status"),
        roles=STORE_ROLES,
        staging_tables=("documents",),
        revision=HEAD_REVISION,
        extensions=("vector",),
        control_tables=PROJECTION_METADATA_TABLES,
    )
    assert store_findings(catalog) == []


def test_quality_frame_keeps_omitted_strings_typed() -> None:
    from types import SimpleNamespace

    from arxiv_int.data_quality.model import KIND_TYPE

    catalog = SimpleNamespace(
        rules=(
            SimpleNamespace(
                kind=KIND_TYPE,
                column="document_id",
                logical_type="string",
                precision=None,
                scale=None,
            ),
            SimpleNamespace(
                kind=KIND_TYPE,
                column="content_hash",
                logical_type="string",
                precision=None,
                scale=None,
            ),
        )
    )
    frame = quality_frame(catalog, [{"document_id": "doc-1"}])
    assert str(frame.get_column("content_hash").dtype) == str(frame.get_column("document_id").dtype)
    assert frame.get_column("content_hash").null_count() == 1
    empty = quality_frame(SimpleNamespace(rules=()), [{"document_id": "doc-1"}])
    assert empty.get_column("document_id").to_list() == ["doc-1"]


def _document_model() -> tuple[Path, ContractSchemaModel]:
    root = discover_project_root(Path(__file__))
    return root, load_schema_model_from_root(contracts_root_for(root))


def test_validate_rows_accepts_omitted_nullable_strings() -> None:
    root, model = _document_model()
    rows = fill_buckets(
        "corpus.documents",
        [
            {
                "document_id": "doc-1",
                "generation_id": "gen-1",
                "contract_version": "1.0.0",
                "title": "fixture",
            }
        ],
    )
    validate_rows(model, "documents", rows, project_root=root, run_id="unit-docs")


def test_validate_rows_rejects_null_document_id() -> None:
    root, model = _document_model()
    with pytest.raises(StagingRejectedError, match=r"corpus\.documents"):
        validate_rows(
            model,
            "documents",
            [{"document_id": None, "generation_id": "g", "contract_version": "1.0.0"}],
            project_root=root,
            run_id="unit-bad",
        )
