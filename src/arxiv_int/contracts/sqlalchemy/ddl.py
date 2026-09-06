"""Compile deterministic review DDL from contract-derived SQLAlchemy metadata."""

from collections.abc import Iterable

from sqlalchemy import MetaData, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, SetColumnComment, SetTableComment, sort_tables

from arxiv_int.contracts.generate.normalize import normalize_text
from arxiv_int.contracts.sqlalchemy.normalize import NormalizedTable

_DIALECT = postgresql.dialect()
_HEADER = "-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)"


def create_schema_statements(schemas: Iterable[str]) -> list[str]:
    """Return CREATE SCHEMA statements for every owned schema."""
    return [f"CREATE SCHEMA IF NOT EXISTS {name};" for name in sorted(set(schemas))]


def _compile(element: CreateTable | SetTableComment | SetColumnComment) -> str:
    return str(element.compile(dialect=_DIALECT)).strip()


def table_ddl(table: Table) -> str:
    """Compile one CREATE TABLE statement with named inline constraints."""
    return f"{_compile(CreateTable(table))};"


def comment_statements(table: Table) -> list[str]:
    """Compile COMMENT ON statements so contract descriptions survive generation."""
    statements: list[str] = []
    if table.comment:
        statements.append(f"{_compile(SetTableComment(table))};")
    for column in table.columns:
        if column.comment:
            statements.append(f"{_compile(SetColumnComment(column))};")
    return statements


def contract_ddl(metadata: MetaData, normalized: NormalizedTable) -> str:
    """Return reviewable DDL for one contract table without cross-table ordering."""
    table = metadata.tables[normalized.qualified_name]
    lines = [
        f"-- Data Contract: {normalized.odcs_id}",
        f"-- Physical binding: {normalized.qualified_name}",
        _HEADER,
        *create_schema_statements([normalized.schema_name]),
        table_ddl(table),
        *comment_statements(table),
    ]
    return normalize_text("\n".join(lines))


def baseline_ddl(metadata: MetaData) -> str:
    """Return the full owned-schema DDL in dependency order for review and apply."""
    schemas = [table.schema for table in metadata.tables.values() if table.schema]
    lines = ["-- arxiv-int canonical baseline DDL", _HEADER]
    lines.extend(create_schema_statements(schemas))
    for table in sort_tables(metadata.tables.values()):
        lines.append(table_ddl(table))
        lines.extend(comment_statements(table))
    return normalize_text("\n".join(lines))
