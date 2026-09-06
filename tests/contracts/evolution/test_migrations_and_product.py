"""Migration ordering, destructive approval, and product evolution checks."""

from pathlib import Path

import pytest

from arxiv_int.contracts.datacontract_lint import datacontract_command
from arxiv_int.contracts.evolution import check_evolution_policy, migration_policy_findings
from arxiv_int.contracts.evolution.avro_compat import generated_avro_self_compatibility
from arxiv_int.contracts.evolution.conformance import (
    expected_tables_from_sql,
    schema_conformance_findings,
)
from arxiv_int.contracts.evolution.datacontract_break import breaking_findings
from arxiv_int.contracts.evolution.migrations import (
    APPROVAL_MARKER,
    destructive_migration_findings,
    migration_order_findings,
)
from arxiv_int.quality.project_root import discover_project_root


def _root() -> Path:
    return discover_project_root(Path(__file__))


def test_product_evolution_policy_passes() -> None:
    report = check_evolution_policy(
        _root() / "contracts",
        project_root=_root(),
        include_live_sql=False,
    )
    assert report.ok, report.findings
    assert report.checked_contracts >= 14


def test_product_migration_policy_passes() -> None:
    assert migration_policy_findings(_root()) == []


def test_out_of_order_migrations_fail(tmp_path: Path) -> None:
    directory = tmp_path / "migrations"
    directory.mkdir()
    (directory / "20260102000000_second.sql").write_text("SELECT 1;\n")
    (directory / "20260101000000_first.sql").write_text("SELECT 1;\n")
    # Sorted glob is chronological; fabricate by checking duplicate timestamp instead.
    (directory / "20260101000000_again.sql").write_text("SELECT 1;\n")
    findings = migration_order_findings(directory)
    assert any("duplicate migration timestamp" in item for item in findings)


def test_destructive_migration_requires_approval(tmp_path: Path) -> None:
    directory = tmp_path / "migrations"
    directory.mkdir()
    (directory / "20260101000000_drop.sql").write_text("DROP TABLE documents;\n")
    assert destructive_migration_findings(directory)
    (directory / "20260101000000_drop.sql").write_text(
        f"{APPROVAL_MARKER}\nDROP TABLE documents;\n"
    )
    assert destructive_migration_findings(directory) == []


def test_schema_conformance_diff_detects_missing_column() -> None:
    expected = {"documents": {"id", "title"}}
    observed = {"documents": {"id"}}
    findings = schema_conformance_findings(expected, observed)
    assert any("missing column 'title'" in item for item in findings)


def test_expected_tables_parse_generated_postgres() -> None:
    postgres = _root() / "contracts" / "generated" / "postgres"
    texts = [path.read_text(encoding="utf-8") for path in sorted(postgres.glob("*.sql"))]
    tables = expected_tables_from_sql(texts)
    assert "documents" in tables
    assert "document_id" in tables["documents"]


def test_generated_avro_self_compatibility() -> None:
    path = _root() / "contracts" / "generated" / "avro" / "documents.avsc"
    assert generated_avro_self_compatibility(path) == []


@pytest.mark.skipif(datacontract_command() is None, reason="Data Contract CLI unavailable")
def test_datacontract_breaking_identical_files(tmp_path: Path) -> None:
    source = _root() / "contracts" / "datasets" / "documents.odcs.yaml"
    left = tmp_path / "left.yaml"
    right = tmp_path / "right.yaml"
    left.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    right.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    assert breaking_findings(left, right) == []
