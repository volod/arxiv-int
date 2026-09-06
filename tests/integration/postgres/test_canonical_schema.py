"""Declared live run of canonical schema migrations on the pinned image."""

import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.migrations.runner import downgrade, upgrade
from arxiv_int.contracts.sqlalchemy.catalog import compare_live_catalog
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.adopt import adopt_database
from arxiv_int.stores.postgres.apply import apply_revisions, inspect_and_compare, row_counts
from arxiv_int.stores.postgres.constants import ROLE_DBT
from arxiv_int.stores.postgres.disposable import disposable_store
from arxiv_int.stores.postgres.hashing import partition_bucket
from arxiv_int.stores.postgres.inspect_live import inspect_store, store_findings
from arxiv_int.stores.postgres.load import StagingRejectedError, load_canonical_batch
from arxiv_int.stores.postgres_image.pins import load_image_pins

pytestmark = [
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_SCHEMA_MIGRATIONS") != "1",
        reason="set ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1 for the declared disposable schema run",
    ),
]


def _root() -> Path:
    return discover_project_root(Path(__file__))


def _document_row(document_id: str = "doc-1") -> dict[str, str]:
    return {
        "document_id": document_id,
        "generation_id": "gen-1",
        "contract_version": "1.0.0",
        "title": "fixture",
    }


def test_empty_to_head_conformance_and_repeat(tmp_path: Path) -> None:
    root = _root()
    model = load_schema_model_from_root(contracts_root_for(root))
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        first = apply_revisions(root, url=store.url, run_id="empty-to-head", revision="head")
        assert first.ok, first.findings
        assert first.revision == "0003"
        second = apply_revisions(root, url=store.url, run_id="repeat-at-head", revision="head")
        assert second.ok, second.findings
        assert second.revision == "0003"
        findings, _payload, revision = inspect_and_compare(root, store.url)
        assert revision == "0003"
        assert findings == []
        engine = create_engine(store.url)
        try:
            with engine.connect() as connection:
                catalog = inspect_store(connection)
                assert store_findings(catalog) == []
                assert compare_live_catalog(connection, model) == []
        finally:
            engine.dispose()


def test_previous_release_to_head_preserves_rows(tmp_path: Path) -> None:
    root = _root()
    contracts = contracts_root_for(root)
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert upgrade(root, contracts, url=store.url, revision="0001").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO corpus.documents "
                        "(document_id, generation_id, contract_version) "
                        "VALUES ('doc-1', 'gen-1', '1.0.0')"
                    )
                )
        finally:
            engine.dispose()
        before = row_counts(store.url, ("corpus.documents",))
        report = apply_revisions(root, url=store.url, run_id="prev-to-head", revision="head")
        assert report.ok, report.findings
        after = row_counts(store.url, ("corpus.documents",))
        assert before["corpus.documents"] == after["corpus.documents"] == 1


def test_downgrade_and_upgrade_round_trip(tmp_path: Path) -> None:
    root = _root()
    contracts = contracts_root_for(root)
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="round-up", revision="head").ok
        down = downgrade(root, contracts, url=store.url, revision="0001")
        assert down.ok, down.detail
        report = apply_revisions(root, url=store.url, run_id="round-up-again", revision="head")
        assert report.ok, report.findings


def test_interrupted_upgrade_rolls_back(tmp_path: Path) -> None:
    root = _root()
    contracts = contracts_root_for(root)
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert upgrade(root, contracts, url=store.url, revision="0001").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
                raise RuntimeError("interrupted")
        except RuntimeError:
            pass
        finally:
            engine.dispose()
        engine = create_engine(store.url)
        try:
            with engine.connect() as connection:
                exists = connection.execute(
                    text("SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'staging')")
                ).scalar()
                assert not exists
                assert inspect_store(connection).revision == "0001"
        finally:
            engine.dispose()
        report = apply_revisions(root, url=store.url, run_id="after-interrupt", revision="head")
        assert report.ok, report.findings


def test_constraints_reject_invalid_facts_and_vector_mixing(tmp_path: Path) -> None:
    root = _root()
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="constraints", revision="head").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO kg.objects (object_id, generation_id, contract_version) "
                        "VALUES ('obj-1', 'gen-1', '1.0.0'), ('obj-2', 'gen-1', '1.0.0')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO corpus.documents "
                        "(document_id, generation_id, contract_version) "
                        "VALUES ('doc-1', 'gen-1', '1.0.0')"
                    )
                )
            with (
                engine.begin() as connection,
                pytest.raises(IntegrityError, match="ck_facts_object_xor_literal"),
            ):
                connection.execute(
                    text(
                        "INSERT INTO kg.facts ("
                        "fact_id, subject_object_id, predicate_id, object_object_id, "
                        "literal_value, literal_type, status, document_id, extractor_id, "
                        "generation_id, contract_version) VALUES ("
                        "'bad-xor', 'obj-1', 'pred-1', 'obj-2', '1', 'integer', "
                        "'proposed', 'doc-1', 'rule-1', 'gen-1', '1.0.0')"
                    )
                )
            with (
                engine.begin() as connection,
                pytest.raises(IntegrityError, match="ck_facts_provenance"),
            ):
                connection.execute(
                    text(
                        "INSERT INTO kg.facts ("
                        "fact_id, subject_object_id, predicate_id, object_object_id, "
                        "status, generation_id, contract_version) VALUES ("
                        "'bad-prov', 'obj-1', 'pred-1', 'obj-2', 'proposed', 'gen-1', '1.0.0')"
                    )
                )
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO search.embedding_profiles "
                        "(profile_id, dimensions, model_digest, contract_version) "
                        "VALUES ('p1', 8, 'digest-a', '1.0.0')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO search.embeddings ("
                        "embedding_id, target_kind, target_id, profile_id, dimensions, "
                        "model_digest, generation_id, contract_version) VALUES ("
                        "'e1', 'chunk', 'c1', 'p1', 8, 'digest-a', 'gen-1', '1.0.0')"
                    )
                )
            with engine.begin() as connection, pytest.raises(DBAPIError, match="dimensions mix"):
                connection.execute(
                    text(
                        "INSERT INTO search.embeddings ("
                        "embedding_id, target_kind, target_id, profile_id, dimensions, "
                        "model_digest, generation_id, contract_version) VALUES ("
                        "'e2', 'chunk', 'c2', 'p1', 16, 'digest-a', 'gen-1', '1.0.0')"
                    )
                )
            with (
                engine.begin() as connection,
                pytest.raises(DBAPIError, match="duplicate embedding"),
            ):
                connection.execute(
                    text(
                        "INSERT INTO search.embeddings ("
                        "embedding_id, target_kind, target_id, profile_id, dimensions, "
                        "model_digest, generation_id, contract_version) VALUES ("
                        "'e3', 'chunk', 'c1', 'p1', 8, 'digest-a', 'gen-1', '1.0.0')"
                    )
                )
        finally:
            engine.dispose()


def test_dbt_role_cannot_mutate_canonical_or_alembic(tmp_path: Path) -> None:
    root = _root()
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="roles", revision="head").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(text(f"SET ROLE {ROLE_DBT}"))
                connection.execute(text("CREATE TABLE derived.example (id TEXT PRIMARY KEY)"))
                with pytest.raises(DBAPIError):
                    connection.execute(
                        text(
                            "INSERT INTO corpus.documents "
                            "(document_id, generation_id, contract_version) "
                            "VALUES ('doc-x', 'gen-1', '1.0.0')"
                        )
                    )
            with engine.begin() as connection:
                connection.execute(text(f"SET ROLE {ROLE_DBT}"))
                with pytest.raises(DBAPIError):
                    connection.execute(text("UPDATE alembic_version SET version_num = '0001'"))
        finally:
            engine.dispose()


def test_copy_upsert_and_quality_gate(tmp_path: Path) -> None:
    root = _root()
    model = load_schema_model_from_root(contracts_root_for(root))
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="load", revision="head").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                count = load_canonical_batch(
                    connection,
                    model,
                    "documents",
                    [_document_row()],
                    project_root=root,
                    run_id="load-docs",
                )
                assert count == 1
                python_bucket = partition_bucket("doc-1")
                sql_bucket = connection.execute(
                    text("SELECT ctl.partition_bucket('doc-1')")
                ).scalar()
                assert sql_bucket == python_bucket
                stored = connection.execute(
                    text(
                        "SELECT document_id, bucket FROM corpus.documents "
                        "WHERE document_id = 'doc-1'"
                    )
                ).one()
                assert stored.document_id == "doc-1"
                assert stored.bucket == python_bucket
            with engine.begin() as connection, pytest.raises(StagingRejectedError):
                load_canonical_batch(
                    connection,
                    model,
                    "documents",
                    [{"document_id": None, "generation_id": "g", "contract_version": "1.0.0"}],
                    project_root=root,
                    run_id="load-bad",
                )
        finally:
            engine.dispose()


def test_legacy_adoption_preserves_rows_and_refuses_drift(tmp_path: Path) -> None:
    root = _root()
    contracts = contracts_root_for(root)
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata-adopt", pins=pins) as store:
        assert upgrade(root, contracts, url=store.url, revision="0001").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO corpus.documents "
                        "(document_id, generation_id, contract_version) "
                        "VALUES ('legacy-1', 'gen-1', '1.0.0')"
                    )
                )
                connection.execute(text("ALTER TABLE corpus.documents SET SCHEMA public"))
                connection.execute(text("DROP SCHEMA corpus CASCADE"))
                connection.execute(text("DELETE FROM alembic_version"))
        finally:
            engine.dispose()
        refused = adopt_database(root, url=store.url, run_id="partial-legacy")
        assert not refused.ok
        assert "missing owned table" in " ".join(refused.findings)
    with disposable_store(root, tmp_path / "pgdata-full", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="adopt-src", revision="head").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO corpus.documents "
                        "(document_id, generation_id, contract_version) "
                        "VALUES ('keep-me', 'gen-1', '1.0.0')"
                    )
                )
                connection.execute(text("DELETE FROM alembic_version"))
        finally:
            engine.dispose()
        report = adopt_database(root, url=store.url, run_id="full-adopt")
        assert report.ok, report.findings
        assert report.stamped_revision == "0003"
        assert report.row_counts.get("corpus.documents") == 1
