"""Capture owned live definitions as run evidence; never as a committed schema baseline."""

from typing import Any

from sqlalchemy import Connection, text

from arxiv_int.stores.postgres.constants import (
    CANONICAL_SCHEMAS,
    OWNED_TABLES,
    PROJECTION_METADATA_TABLES,
    STORE_ROLES,
)


def _query(connection: Connection, sql: str, **params: Any) -> list[list[Any]]:
    return [list(row) for row in connection.execute(text(sql), params)]


def _owned_names() -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                *(f"{schema}.{table}" for schema, table in OWNED_TABLES),
                *(f"staging.{table}" for _, table in OWNED_TABLES),
                *(f"ctl.{table}" for table in PROJECTION_METADATA_TABLES),
                "search.embedding_profiles",
            }
        )
    )


def _table_definition(connection: Connection, name: str) -> dict[str, Any]:
    return {
        "columns": _query(
            connection,
            "SELECT a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull, "
            "pg_get_expr(d.adbin, d.adrelid), a.attidentity, a.attgenerated "
            "FROM pg_attribute a LEFT JOIN pg_attrdef d "
            "ON d.adrelid = a.attrelid AND d.adnum = a.attnum "
            "WHERE a.attrelid = to_regclass(:name) AND a.attnum > 0 AND NOT a.attisdropped "
            "ORDER BY a.attname",
            name=name,
        ),
        "constraints": _query(
            connection,
            "SELECT conname, contype, pg_get_constraintdef(oid), convalidated "
            "FROM pg_constraint WHERE conrelid = to_regclass(:name) ORDER BY conname",
            name=name,
        ),
        "indexes": _query(
            connection,
            "SELECT c.relname, pg_get_indexdef(i.indexrelid), i.indisvalid, i.indisready "
            "FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
            "WHERE i.indrelid = to_regclass(:name) ORDER BY c.relname",
            name=name,
        ),
        "relation": _query(
            connection,
            "SELECT relkind, relpersistence, pg_get_partkeydef(oid), relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE oid = to_regclass(:name)",
            name=name,
        ),
        "partitions": _query(
            connection,
            "SELECT n.nspname, c.relname, pg_get_expr(c.relpartbound, c.oid) "
            "FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE i.inhparent = to_regclass(:name) ORDER BY n.nspname, c.relname",
            name=name,
        ),
        "triggers": _query(
            connection,
            "SELECT tgname, pg_get_triggerdef(oid), tgenabled FROM pg_trigger "
            "WHERE tgrelid = to_regclass(:name) AND NOT tgisinternal ORDER BY tgname",
            name=name,
        ),
        "privileges": _query(
            connection,
            "SELECT rolname, p, has_table_privilege(rolname, to_regclass(:name), p) "
            "FROM pg_roles CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE',"
            "'TRUNCATE','REFERENCES','TRIGGER']) p WHERE rolname = ANY(:roles) ORDER BY rolname,p",
            name=name,
            roles=list(STORE_ROLES),
        ),
    }


def capture_catalog(connection: Connection) -> dict[str, Any]:
    """Read stable definitions; exclude rows, dbt relations and disposable projections."""
    prior = connection.execute(text("SHOW search_path")).scalar_one()
    connection.execute(text("SELECT set_config('search_path', 'pg_catalog', true)"))
    try:
        tables = {}
        for name in _owned_names():
            if connection.execute(text("SELECT to_regclass(:name)"), {"name": name}).scalar():
                tables[name] = _table_definition(connection, name)
        return {
            "tables": tables,
            "roles": _query(
                connection,
                "SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb, rolcanlogin, "
                "rolreplication, rolbypassrls FROM pg_roles WHERE rolname = ANY(:roles) ORDER BY 1",
                roles=list(STORE_ROLES),
            ),
            "schemas": _query(
                connection,
                "SELECT nspname FROM pg_namespace WHERE nspname = ANY(:schemas) ORDER BY 1",
                schemas=[*CANONICAL_SCHEMAS, "staging", "derived"],
            ),
            "schema_privileges": _query(
                connection,
                "SELECT rolname, nspname, has_schema_privilege(rolname, n.oid, 'USAGE'), "
                "has_schema_privilege(rolname, n.oid, 'CREATE') FROM pg_roles CROSS JOIN pg_namespace n "
                "WHERE rolname = ANY(:roles) AND nspname = ANY(:schemas) ORDER BY 1,2",
                roles=list(STORE_ROLES),
                schemas=[*CANONICAL_SCHEMAS, "staging", "derived"],
            ),
            "functions": _query(
                connection,
                "SELECT n.nspname, p.proname, pg_get_functiondef(p.oid) FROM pg_proc p "
                "JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE (n.nspname, p.proname) IN "
                "(('ctl','partition_bucket'),('search','enforce_embedding_profile')) ORDER BY 1,2",
            ),
        }
    finally:
        connection.execute(text("SELECT set_config('search_path', :prior, true)"), {"prior": prior})
