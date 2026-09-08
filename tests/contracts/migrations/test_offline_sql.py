"""Deterministic offline PostgreSQL DDL emitted from the frozen revision history."""

from pathlib import Path

import pytest

from arxiv_int.contracts.migrations import commands
from arxiv_int.contracts.migrations.paths import data_root, migration_artifact_dir
from arxiv_int.contracts.migrations.runner import offline_sql
from arxiv_int.resources.paths import contracts_root
from tests.contracts.migrations._project import product_root


def _sql() -> str:
    return offline_sql(product_root(), contracts_root())


def test_offline_upgrade_sql_is_deterministic_and_schema_qualified() -> None:
    first = _sql()
    assert first == _sql()
    assert "CREATE SCHEMA IF NOT EXISTS corpus" in first
    assert "CREATE TABLE corpus.documents (" in first
    assert "CONSTRAINT pk_documents PRIMARY KEY (document_id)" in first
    assert "REFERENCES corpus.documents (document_id)" in first
    assert "INSERT INTO alembic_version (version_num) VALUES ('0001')" in first
    assert "PARTITION BY HASH" in first
    assert "ck_facts_object_xor_literal" in first
    assert "CREATE SCHEMA IF NOT EXISTS derived" in first


def test_offline_sql_matches_the_generated_baseline_tables() -> None:
    baseline = (contracts_root() / "generated" / "postgres" / "baseline.sql").read_text(
        encoding="utf-8"
    )
    emitted = _sql()
    for line in baseline.splitlines():
        if line.startswith("CREATE TABLE "):
            assert line in emitted


def test_offline_sql_command_writes_under_the_data_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "artifacts"))
    assert data_root(product_root()) == tmp_path / "artifacts"
    assert commands.run_offline_sql(product_root(), contracts_root(), "head") == 0
    written = sorted((tmp_path / "artifacts" / "migrations").rglob("upgrade.sql"))
    assert len(written) == 1
    assert "CREATE TABLE corpus.documents (" in written[0].read_text(encoding="utf-8")


def test_relative_data_dir_resolves_under_the_project_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", ".data")
    assert migration_artifact_dir(product_root(), "run").parent.parent == (product_root() / ".data")
