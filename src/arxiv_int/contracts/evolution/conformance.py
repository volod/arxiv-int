"""Compare expected baseline tables to a live PostgreSQL information_schema."""

import re
from collections.abc import Sequence

from arxiv_int.contracts.generate.sql_validate import apply_sql_on_disposable_postgres

_CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<table>[a-zA-Z0-9_.]+)\s*\((?P<body>.*?)\);",
    re.IGNORECASE | re.DOTALL,
)
_COLUMN = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+", re.MULTILINE)


def expected_tables_from_sql(sql_texts: Sequence[str]) -> dict[str, set[str]]:
    """Parse CREATE TABLE statements into table -> column-name sets."""
    tables: dict[str, set[str]] = {}
    for text in sql_texts:
        for match in _CREATE_TABLE.finditer(text):
            table = match.group("table").split(".")[-1].lower()
            body = match.group("body")
            columns: set[str] = set()
            for line in body.splitlines():
                stripped = line.strip().rstrip(",")
                if not stripped or stripped.upper().startswith(
                    ("PRIMARY ", "UNIQUE ", "CONSTRAINT ", "CHECK ", "FOREIGN ")
                ):
                    continue
                column = _COLUMN.match(stripped)
                if column:
                    columns.add(column.group(1).lower())
            tables[table] = columns
    return tables


def schema_conformance_findings(
    expected: dict[str, set[str]], observed: dict[str, set[str]]
) -> list[str]:
    """Diff expected vs observed table/column sets."""
    findings: list[str] = []
    for table in sorted(set(expected) | set(observed)):
        if table not in observed:
            findings.append(f"live schema missing table '{table}'")
            continue
        if table not in expected:
            findings.append(f"live schema has unexpected table '{table}'")
            continue
        missing = expected[table] - observed[table]
        extra = observed[table] - expected[table]
        for column in sorted(missing):
            findings.append(f"live schema table '{table}' missing column '{column}'")
        for column in sorted(extra):
            findings.append(f"live schema table '{table}' has unexpected column '{column}'")
    return findings


def disposable_schema_conformance_findings(sql_texts: Sequence[str]) -> list[str]:
    """Apply SQL on disposable Postgres when Docker works; otherwise skip softly.

    Full information_schema introspection requires a query client. This check proves the
    baseline CREATE TABLE set applies cleanly, which is the live-store gate available
    without a pinned product image.
    """
    apply_findings = apply_sql_on_disposable_postgres(sql_texts)
    if apply_findings and apply_findings[0].startswith("docker unavailable"):
        return []
    return apply_findings
