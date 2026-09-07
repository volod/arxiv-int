"""SQL parse and disposable-database checks for the generated baseline DDL."""

from pathlib import Path

import pytest

pytest.importorskip("sqlglot")

from arxiv_int.contracts.generate.pipeline import BASELINE_DDL_RELATIVE
from arxiv_int.contracts.generate.sql_validate import (
    apply_baseline_on_disposable_postgres,
    parse_sql_statements,
)
from arxiv_int.quality.project_root import discover_project_root


def _generated_root() -> Path:
    return discover_project_root(Path(__file__)) / "contracts" / "generated"


def _contract_sql() -> list[str]:
    root = _generated_root() / "postgres"
    return [
        path.read_text(encoding="utf-8")
        for path in sorted(root.glob("*.sql"))
        if path.name != "baseline.sql"
    ]


def _baseline_sql() -> str:
    return (_generated_root() / BASELINE_DDL_RELATIVE).read_text(encoding="utf-8")


def test_generated_postgres_ddl_parses_with_sqlglot() -> None:
    texts = _contract_sql()
    assert len(texts) >= 14
    assert parse_sql_statements([*texts, _baseline_sql()]) == []


def test_generated_ddl_is_schema_qualified() -> None:
    baseline = _baseline_sql()
    assert "CREATE SCHEMA IF NOT EXISTS corpus;" in baseline
    assert "CREATE TABLE corpus.documents (" in baseline
    assert "CREATE TABLE kg.transactions (" in baseline
    assert "CONSTRAINT pk_documents PRIMARY KEY (document_id)" in baseline


@pytest.mark.heavy
def test_baseline_ddl_applies_on_disposable_database() -> None:
    findings = apply_baseline_on_disposable_postgres(_baseline_sql())
    if findings and findings[0].startswith("docker unavailable"):
        pytest.skip(findings[0])
    assert findings == []
