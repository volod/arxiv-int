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
    for statement in (
        "CREATE SCHEMA IF NOT EXISTS corpus",
        "CREATE SCHEMA IF NOT EXISTS derived",
        "CREATE TABLE corpus.documents (",
        "CONSTRAINT pk_documents PRIMARY KEY (document_id)",
        "REFERENCES corpus.documents (document_id)",
        "CREATE TABLE ctl.run (",
        "CREATE TABLE ctl.stage_progress (",
        "CREATE TABLE ctl.source_tombstone (",
        "PARTITION BY HASH",
        "ck_facts_object_xor_literal",
    ):
        assert statement in first
    assert "ALTER TABLE corpus.document_path_event ADD CONSTRAINT" not in first


def test_one_initial_revision_creates_every_owned_corpus_table() -> None:
    """One stamp, no follow-up revision: every contract table lands in the initial DDL."""
    first = _sql()
    assert "INSERT INTO alembic_version (version_num) VALUES ('0001')" in first
    assert "INSERT INTO alembic_version (version_num) VALUES ('0002')" not in first
    for table in (
        "document_path_event",
        "documents",
        "duplicate_groups",
        "normalized_documents",
        "source_occurrences",
        "chunks",
        "spans",
    ):
        assert f"CREATE TABLE corpus.{table} (" in first
        assert f"CREATE UNLOGGED TABLE staging.{table} (" in first
        assert f"CREATE TABLE corpus.{table}_p00 PARTITION OF corpus.{table}" in first


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
