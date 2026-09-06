"""SQL parse and disposable-database checks for generated baselines."""

from pathlib import Path

import pytest

pytest.importorskip("sqlglot")

from arxiv_int.contracts.generate.sql_validate import (
    apply_sql_on_disposable_postgres,
    parse_sql_statements,
)
from arxiv_int.quality.project_root import discover_project_root


def _baseline_sql() -> list[str]:
    root = discover_project_root(Path(__file__)) / "contracts" / "generated" / "postgres"
    return [path.read_text(encoding="utf-8") for path in sorted(root.glob("*.sql"))]


def test_baseline_postgres_sql_parses_with_sqlglot() -> None:
    texts = _baseline_sql()
    assert len(texts) >= 14
    assert parse_sql_statements(texts) == []


def test_baseline_postgres_sql_applies_on_disposable_database() -> None:
    findings = apply_sql_on_disposable_postgres(_baseline_sql())
    if findings and findings[0].startswith("docker unavailable"):
        pytest.skip(findings[0])
    assert findings == []
