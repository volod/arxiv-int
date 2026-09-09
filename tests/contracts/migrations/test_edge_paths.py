"""Failure and reporting paths that keep migration status honest."""

from pathlib import Path

import pytest

from arxiv_int.contracts.migrations import commands
from arxiv_int.contracts.migrations.authoring import generate_revision, next_revision_id, slug
from arxiv_int.contracts.migrations.errors import MigrationRunnerUnavailableError
from arxiv_int.contracts.migrations.graph import manifest_findings, revision_graph
from arxiv_int.contracts.migrations.paths import revision_manifest_path, versions_dir
from arxiv_int.contracts.migrations.runner import (
    CONTRACTS_ROOT_VARIABLE,
    target_metadata,
)
from arxiv_int.contracts.migrations.state import load_state
from arxiv_int.contracts.sqlalchemy.catalog import compare_live_catalog
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.resources.paths import contracts_root
from tests.contracts.migrations._project import disposable_project


def test_revision_command_reports_a_generated_candidate(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = disposable_project(tmp_path / "project")
    caplog.set_level("INFO")
    assert commands.run_revision(root, root / "contracts", "baseline contract schema") == 0
    assert "generated revision 0001" in caplog.text
    assert "review the revision" in caplog.text


def test_slug_and_revision_ids_are_stable() -> None:
    assert slug("  Add Page Count! ") == "add_page_count"
    assert slug("***") == "revision"
    assert next_revision_id({"revisions": {}}) == "0001"
    assert next_revision_id({"revisions": {"0001": {}, "0002": {}}}) == "0003"


def test_broken_manifest_is_rejected(tmp_path: Path) -> None:
    root = disposable_project(tmp_path / "project")
    generate_revision(root, root / "contracts", message="baseline")
    revision_manifest_path(root).write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="revision manifest is not an object"):
        manifest_findings(root)


def test_revision_file_without_a_header_is_rejected(tmp_path: Path) -> None:
    root = disposable_project(tmp_path / "project")
    generate_revision(root, root / "contracts", message="baseline")
    (versions_dir(root) / "0002_broken.py").write_text("# no header\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no reviewed revision header"):
        revision_graph(root)


def test_unsupported_state_document_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "head_state.json"
    path.write_text('{"stateVersion": 99}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported migration state document"):
        load_state(path)


def test_missing_state_file_is_the_empty_state(tmp_path: Path) -> None:
    assert load_state(tmp_path / "absent.json")["tables"] == {}


def test_alembic_environment_requires_an_explicit_contracts_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CONTRACTS_ROOT_VARIABLE, raising=False)
    with pytest.raises(MigrationRunnerUnavailableError, match=CONTRACTS_ROOT_VARIABLE):
        target_metadata()
    monkeypatch.setenv(CONTRACTS_ROOT_VARIABLE, str(contracts_root()))
    assert "corpus.documents" in target_metadata().tables


def test_compare_live_catalog_reports_every_owned_table_as_missing() -> None:
    from sqlalchemy import create_engine

    model = load_schema_model_from_root(contracts_root())
    with create_engine("sqlite://").connect() as connection:
        findings = compare_live_catalog(connection, model)
    assert len(findings) == len(model.qualified_names())
    assert all("missing owned table" in item for item in findings)


def test_unknown_contract_id_is_rejected() -> None:
    model = load_schema_model_from_root(contracts_root())
    with pytest.raises(KeyError, match="Unknown contract id"):
        model.by_contract("absent")
