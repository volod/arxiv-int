"""Adoption stamps 0001 when the live overlay has projection tables but no ledger."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from arxiv_int.contracts.migrations.runner import DATABASE_URL_VARIABLE, STATUS_OK, RunnerOutcome
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.adopt import adopt_database
from arxiv_int.stores.postgres.constants import (
    CANONICAL_SCHEMAS,
    HASH_MODULUS,
    INITIAL_REVISION,
    PARTITIONED_TABLES,
    PROJECTION_METADATA_TABLES,
    STORE_ROLES,
)
from arxiv_int.stores.postgres.inspect_live import LiveStoreCatalog, PartitionSpec


def test_adopt_stamps_initial_when_ledger_tables_are_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(DATABASE_URL_VARIABLE, "postgresql://x")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value.execute.return_value.scalar.return_value = (
        False
    )
    catalog = LiveStoreCatalog(
        schemas=(*CANONICAL_SCHEMAS, "staging", "derived"),
        partitioned=tuple(
            PartitionSpec(f"{schema}.{table}", f"HASH ({pk})", HASH_MODULUS)
            for schema, table, pk in PARTITIONED_TABLES
        ),
        checks=("ck_facts_object_xor_literal", "ck_facts_provenance", "ck_facts_status"),
        roles=STORE_ROLES,
        staging_tables=("documents",),
        revision=None,
        extensions=("vector",),
        control_tables=PROJECTION_METADATA_TABLES,
    )
    monkeypatch.setattr("arxiv_int.stores.postgres.adopt.create_engine", lambda *_a, **_k: engine)
    monkeypatch.setattr("arxiv_int.stores.postgres.adopt.relocate_public_tables", lambda *_a: [])
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.compare_live_catalog", lambda *_a, **_k: []
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.require_safe_adoption", lambda *_a, **_k: None
    )
    monkeypatch.setattr("arxiv_int.stores.postgres.adopt.inspect_store", lambda *_a, **_k: catalog)
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.stamp",
        lambda *_a, **_k: RunnerOutcome(STATUS_OK, "stamped"),
    )
    monkeypatch.setattr("arxiv_int.stores.postgres.adopt.catalog_boundary_findings", lambda *_a: [])
    report = adopt_database(discover_project_root(Path(__file__)), url="postgresql://x", run_id="s")
    assert report.ok
    assert report.stamped_revision == INITIAL_REVISION
