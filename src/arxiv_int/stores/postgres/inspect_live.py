"""Inspect live PostgreSQL catalog objects used by the canonical store overlay."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, bindparam, text

from arxiv_int.stores.postgres.constants import (
    CANONICAL_SCHEMAS,
    CONTROL_TABLES,
    DERIVED_SCHEMA,
    HASH_MODULUS,
    HEAD_REVISION,
    LEDGER_TABLES,
    PARTITIONED_TABLES,
    PROJECTION_METADATA_TABLES,
    STAGING_SCHEMA,
    STORE_ROLES,
)


@dataclass(frozen=True, slots=True)
class PartitionSpec:
    """One HASH-partitioned parent and its remainder children."""

    qualified_name: str
    strategy: str
    child_count: int


@dataclass(frozen=True, slots=True)
class LiveStoreCatalog:
    """Redactable snapshot of schemas, partitions, checks, and roles."""

    schemas: tuple[str, ...]
    partitioned: tuple[PartitionSpec, ...]
    checks: tuple[str, ...]
    roles: tuple[str, ...]
    staging_tables: tuple[str, ...]
    revision: str | None
    extensions: tuple[str, ...]
    control_tables: tuple[str, ...] = ()


def _rows(
    connection: Connection, sql: str, params: Mapping[str, Any] | None = None
) -> Sequence[Any]:
    statement = text(sql)
    values = dict(params or {})
    expanding: list[Any] = [
        bindparam(name, expanding=True) for name, value in values.items() if isinstance(value, list)
    ]
    if expanding:
        statement = statement.bindparams(*expanding)
    return connection.execute(statement, values).fetchall()


def applied_revision(connection: Connection) -> str | None:
    """Return the Alembic version stamp, if the version table exists."""
    present = _rows(
        connection,
        "SELECT to_regclass('public.alembic_version') IS NOT NULL",
    )
    if not present or not present[0][0]:
        return None
    rows = _rows(connection, "SELECT version_num FROM alembic_version")
    if not rows:
        return None
    return str(rows[0][0])


def inspect_store(connection: Connection) -> LiveStoreCatalog:
    """Read partition, check, role, and extension objects from the live catalog."""
    schema_rows = _rows(
        connection,
        "SELECT nspname FROM pg_namespace WHERE nspname IN :names ORDER BY 1",
        {"names": [*CANONICAL_SCHEMAS, STAGING_SCHEMA, DERIVED_SCHEMA]},
    )
    partition_rows = _rows(
        connection,
        "SELECT n.nspname || '.' || c.relname AS name, "
        "pg_get_partkeydef(c.oid) AS strategy, "
        "(SELECT count(*) FROM pg_inherits i WHERE i.inhparent = c.oid) AS children "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE c.relkind = 'p' AND n.nspname IN :schemas ORDER BY 1",
        {"schemas": list(CANONICAL_SCHEMAS)},
    )
    check_rows = _rows(
        connection,
        "SELECT con.conname FROM pg_constraint con "
        "JOIN pg_class rel ON rel.oid = con.conrelid "
        "JOIN pg_namespace n ON n.oid = rel.relnamespace "
        "WHERE con.contype = 'c' AND n.nspname IN :schemas ORDER BY 1",
        {"schemas": list(CANONICAL_SCHEMAS)},
    )
    role_rows = _rows(
        connection,
        "SELECT rolname FROM pg_roles WHERE rolname IN :roles ORDER BY 1",
        {"roles": list(STORE_ROLES)},
    )
    staging_rows = _rows(
        connection,
        "SELECT tablename FROM pg_tables WHERE schemaname = :schema ORDER BY 1",
        {"schema": STAGING_SCHEMA},
    )
    extension_rows = _rows(
        connection,
        "SELECT extname || ' ' || extversion FROM pg_extension "
        "WHERE extname IN ('vector', 'pg_search', 'age') ORDER BY 1",
    )
    control_rows = _rows(
        connection,
        "SELECT tablename FROM pg_tables WHERE schemaname = 'ctl' AND tablename IN :names "
        "ORDER BY 1",
        {"names": list(CONTROL_TABLES)},
    )
    partitioned = tuple(
        PartitionSpec(str(row[0]), str(row[1] or ""), int(row[2])) for row in partition_rows
    )
    return LiveStoreCatalog(
        schemas=tuple(str(row[0]) for row in schema_rows),
        partitioned=partitioned,
        checks=tuple(str(row[0]) for row in check_rows),
        roles=tuple(str(row[0]) for row in role_rows),
        staging_tables=tuple(str(row[0]) for row in staging_rows),
        revision=applied_revision(connection),
        extensions=tuple(str(row[0]) for row in extension_rows),
        control_tables=tuple(str(row[0]) for row in control_rows),
    )


def _partition_findings(catalog: LiveStoreCatalog) -> list[str]:
    expected = {f"{schema}.{table}" for schema, table, _pk in PARTITIONED_TABLES}
    observed = {item.qualified_name for item in catalog.partitioned}
    findings: list[str] = []
    missing = sorted(expected - observed)
    if missing:
        findings.append("live catalog is missing HASH parents: " + ", ".join(missing))
    for item in catalog.partitioned:
        if item.child_count != HASH_MODULUS:
            findings.append(
                f"{item.qualified_name} has {item.child_count} partitions, expected {HASH_MODULUS}"
            )
        if "HASH" not in item.strategy.upper():
            findings.append(f"{item.qualified_name} partition strategy is {item.strategy!r}")
    return findings


def store_findings(
    catalog: LiveStoreCatalog,
    *,
    require_head: bool = True,
    require_projections: bool = True,
    require_ledger: bool | None = None,
) -> list[str]:
    """Return overlay defects after a successful head upgrade."""
    findings: list[str] = []
    expected_schemas = set(CANONICAL_SCHEMAS) | {STAGING_SCHEMA, DERIVED_SCHEMA}
    missing_schemas = sorted(expected_schemas - set(catalog.schemas))
    if missing_schemas:
        findings.append("live catalog is missing schemas: " + ", ".join(missing_schemas))
    findings.extend(_partition_findings(catalog))
    for name in ("ck_facts_object_xor_literal", "ck_facts_provenance", "ck_facts_status"):
        if name not in catalog.checks:
            findings.append(f"live catalog is missing check constraint {name}")
    missing_roles = sorted(set(STORE_ROLES) - set(catalog.roles))
    if missing_roles:
        findings.append("live catalog is missing roles: " + ", ".join(missing_roles))
    if "documents" not in catalog.staging_tables:
        findings.append("live catalog is missing staging.documents")
    if require_projections:
        missing_proj = sorted(set(PROJECTION_METADATA_TABLES) - set(catalog.control_tables))
        if missing_proj:
            findings.append(
                "live catalog is missing projection metadata: " + ", ".join(missing_proj)
            )
    if require_ledger is None:
        require_ledger = require_head
    if require_ledger:
        missing_ledger = sorted(set(LEDGER_TABLES) - set(catalog.control_tables))
        if missing_ledger:
            findings.append(
                "live catalog is missing run ledger tables: " + ", ".join(missing_ledger)
            )
    if require_head and catalog.revision != HEAD_REVISION:
        findings.append(f"live revision is {catalog.revision!r}, expected {HEAD_REVISION!r}")
    return findings
