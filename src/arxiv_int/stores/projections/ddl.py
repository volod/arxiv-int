"""Runtime copy of revision 0003 projection metadata DDL."""

from arxiv_int.stores.postgres.constants import ROLE_DBT, ROLE_PIPELINE, ROLE_READER

PROJECTION_TABLES = (
    "ctl.projections",
    "ctl.projection_active",
    "ctl.projection_evidence",
    "ctl.projection_cleanup",
)


def projection_metadata_sql() -> tuple[str, ...]:
    """Return CREATE TABLE SQL matching revision 0003."""
    return (
        "CREATE TABLE ctl.projections ("
        "projection_id TEXT PRIMARY KEY, kind TEXT NOT NULL, version_id TEXT NOT NULL, "
        "status TEXT NOT NULL, schema_version TEXT NOT NULL, engine TEXT NOT NULL, "
        "engine_object TEXT, input_fingerprint TEXT, row_count BIGINT, checksum TEXT, "
        "quality_status TEXT, last_committed_id TEXT, canonical_fact_version TEXT, "
        "run_id TEXT NOT NULL, created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(), "
        "CONSTRAINT ck_projections_kind CHECK (kind IN ('lexical', 'vector', 'graph')), "
        "CONSTRAINT ck_projections_status CHECK (status IN "
        "('staging', 'validated', 'active', 'failed', 'retired', 'dropped')), "
        "CONSTRAINT uq_projections_kind_version UNIQUE (kind, version_id))",
        "CREATE TABLE ctl.projection_active ("
        "kind TEXT PRIMARY KEY, projection_id TEXT NOT NULL "
        "REFERENCES ctl.projections (projection_id), previous_projection_id TEXT, "
        "switched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(), "
        "CONSTRAINT ck_projection_active_kind CHECK (kind IN ('lexical', 'vector', 'graph')))",
        "CREATE TABLE ctl.projection_evidence ("
        "evidence_id TEXT PRIMARY KEY, projection_id TEXT NOT NULL "
        "REFERENCES ctl.projections (projection_id), check_name TEXT NOT NULL, "
        "status TEXT NOT NULL, detail TEXT, checked_count BIGINT, failed_count BIGINT, "
        "created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now())",
        "CREATE TABLE ctl.projection_cleanup ("
        "cleanup_id TEXT PRIMARY KEY, projection_id TEXT NOT NULL "
        "REFERENCES ctl.projections (projection_id), engine_object TEXT, "
        "status TEXT NOT NULL, planned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(), "
        "CONSTRAINT ck_projection_cleanup_status CHECK "
        "(status IN ('planned', 'executed', 'skipped')))",
    )


def projection_grant_sql() -> tuple[str, ...]:
    """Return grants that keep dbt from writing projection metadata."""
    tables = ", ".join(PROJECTION_TABLES)
    return (
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tables} TO {ROLE_PIPELINE}",
        f"GRANT SELECT ON {tables} TO {ROLE_DBT}, {ROLE_READER}",
        f"GRANT USAGE, CREATE ON SCHEMA search TO {ROLE_PIPELINE}",
    )
