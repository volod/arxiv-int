"""Validate live store definitions directly against the initial migration's metadata."""

import importlib.util
from pathlib import Path
from types import ModuleType

from sqlalchemy import Connection, MetaData, text

from arxiv_int.contracts.sqlalchemy.catalog import compare_metadata
from arxiv_int.stores.postgres.constants import HEAD_REVISION, ROLE_DBT, ROLE_READER, STORE_ROLES

INITIAL_REVISION_FILE = "0001_initial_store.py"


def initial_definition(project_root: Path) -> ModuleType:
    """Load the selected checkout's frozen initial definition without executing its upgrade."""
    path = project_root / "src/arxiv_int/migrations/versions" / INITIAL_REVISION_FILE
    spec = importlib.util.spec_from_file_location("arxiv_int_initial_store", path)
    if spec is None or spec.loader is None:
        raise ValueError("initial store definition is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def catalog_boundary_findings(
    project_root: Path, connection: Connection, revision: str
) -> list[str]:
    """Reject missing, partial or drifted initial stores; no snapshot files are required."""
    if revision != HEAD_REVISION:
        return [f"unsupported store revision {revision}; expected {HEAD_REVISION}"]
    definition = initial_definition(project_root)
    metadata = definition.schema_metadata()
    assert isinstance(metadata, MetaData)
    findings = compare_metadata(connection, metadata)
    findings.extend(_role_findings(connection, metadata))
    findings.extend(_function_findings(connection, definition.STORE_SQL))
    return findings


def _role_findings(connection: Connection, metadata: MetaData) -> list[str]:
    findings: list[str] = []
    for role in STORE_ROLES:
        attributes = connection.execute(
            text(
                "SELECT rolsuper, rolcanlogin, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls "
                "FROM pg_roles WHERE rolname = :role"
            ),
            {"role": role},
        ).first()
        if attributes is None or any(attributes):
            findings.append(f"store role {role} is absent or has unsafe attributes")
    for role in (ROLE_DBT, ROLE_READER):
        if not connection.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}
        ).scalar():
            continue
        findings.extend(_write_privilege_findings(connection, metadata, role))
    return findings


def _write_privilege_findings(connection: Connection, metadata: MetaData, role: str) -> list[str]:
    findings: list[str] = []
    for name in (*metadata.tables, "public.alembic_version"):
        if name.startswith("staging."):
            continue
        writable = connection.execute(
            text(
                "SELECT CASE WHEN to_regclass(:name) IS NULL THEN false ELSE "
                "has_table_privilege(:role, to_regclass(:name), 'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') END"
            ),
            {"role": role, "name": name},
        ).scalar()
        if writable:
            findings.append(f"store role {role} can mutate protected table {name}")
    return findings


def _function_findings(connection: Connection, statements: tuple[str, ...]) -> list[str]:
    findings: list[str] = []
    for statement in statements:
        if not statement.startswith("CREATE OR REPLACE FUNCTION"):
            continue
        identity = statement.split("FUNCTION ", 1)[1].split("(", 1)[0]
        schema, name = identity.split(".")
        body = statement.split("$$", 2)[1].strip()
        observed = (
            connection.execute(
                text(
                    "SELECT prosrc FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                    "WHERE n.nspname = :schema AND p.proname = :name"
                ),
                {"schema": schema, "name": name},
            )
            .scalars()
            .all()
        )
        if [str(value).strip() for value in observed] != [body]:
            findings.append(f"store function {identity} differs from the initial definition")
    trigger = connection.execute(
        text(
            "SELECT t.tgenabled, p.proname, n.nspname FROM pg_trigger t "
            "JOIN pg_proc p ON p.oid = t.tgfoid JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE t.tgrelid = to_regclass('search.embeddings') AND t.tgname = 'trg_embeddings_profile'"
        )
    ).first()
    if trigger is None or tuple(trigger) != ("O", "enforce_embedding_profile", "search"):
        findings.append("embedding profile trigger is missing, disabled or retargeted")
    return findings
