"""projection metadata, pointer, evidence, and cleanup tables

Generated for the rebuildable search and graph projection overlay. Definitions
below are frozen: this revision never imports today's contracts to decide what
it creates.

Revision ID: 0003
Revises: 0002
Contract fingerprints: unchanged from 0001; this revision adds ctl projection objects.
"""

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: None = None
depends_on: None = None

CONTRACT_FINGERPRINTS: dict[str, str] = {}
REVIEW_NOTES: tuple[str, ...] = (
    "projection metadata lives in ctl and is never a canonical document or fact",
    "active pointers switch only after quality results are publishable",
    "index DDL and AGE graphs stay outside dbt-owned derived relations",
)
IRREVERSIBLE_REASON: str = ""


def upgrade() -> None:
    """Create versioned projection metadata, active pointers, and evidence tables."""
    op.execute(
        "CREATE TABLE ctl.projections ("
        "projection_id TEXT PRIMARY KEY, "
        "kind TEXT NOT NULL, "
        "version_id TEXT NOT NULL, "
        "status TEXT NOT NULL, "
        "schema_version TEXT NOT NULL, "
        "engine TEXT NOT NULL, "
        "engine_object TEXT, "
        "input_fingerprint TEXT, "
        "row_count BIGINT, "
        "checksum TEXT, "
        "quality_status TEXT, "
        "last_committed_id TEXT, "
        "canonical_fact_version TEXT, "
        "run_id TEXT NOT NULL, "
        "created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(), "
        "CONSTRAINT ck_projections_kind CHECK (kind IN ('lexical', 'vector', 'graph')), "
        "CONSTRAINT ck_projections_status CHECK (status IN "
        "('staging', 'validated', 'active', 'failed', 'retired', 'dropped')), "
        "CONSTRAINT uq_projections_kind_version UNIQUE (kind, version_id)"
        ")"
    )
    op.execute(
        "CREATE TABLE ctl.projection_active ("
        "kind TEXT PRIMARY KEY, "
        "projection_id TEXT NOT NULL REFERENCES ctl.projections (projection_id), "
        "previous_projection_id TEXT, "
        "switched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(), "
        "CONSTRAINT ck_projection_active_kind CHECK (kind IN ('lexical', 'vector', 'graph'))"
        ")"
    )
    op.execute(
        "CREATE TABLE ctl.projection_evidence ("
        "evidence_id TEXT PRIMARY KEY, "
        "projection_id TEXT NOT NULL REFERENCES ctl.projections (projection_id), "
        "check_name TEXT NOT NULL, "
        "status TEXT NOT NULL, "
        "detail TEXT, "
        "checked_count BIGINT, "
        "failed_count BIGINT, "
        "created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()"
        ")"
    )
    op.execute(
        "CREATE TABLE ctl.projection_cleanup ("
        "cleanup_id TEXT PRIMARY KEY, "
        "projection_id TEXT NOT NULL REFERENCES ctl.projections (projection_id), "
        "engine_object TEXT, "
        "status TEXT NOT NULL, "
        "planned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(), "
        "CONSTRAINT ck_projection_cleanup_status CHECK "
        "(status IN ('planned', 'executed', 'skipped'))"
        ")"
    )
    op.execute("CREATE INDEX ix_projections_kind_status ON ctl.projections (kind, status)")
    op.execute(
        "CREATE INDEX ix_projection_evidence_projection_id "
        "ON ctl.projection_evidence (projection_id)"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ctl.projections, ctl.projection_active, "
        "ctl.projection_evidence, ctl.projection_cleanup TO arxiv_int_pipeline"
    )
    op.execute(
        "GRANT SELECT ON ctl.projections, ctl.projection_active, ctl.projection_evidence, "
        "ctl.projection_cleanup TO arxiv_int_dbt, arxiv_int_reader"
    )
    op.execute("GRANT USAGE, CREATE ON SCHEMA search TO arxiv_int_pipeline")


def downgrade() -> None:
    """Drop projection metadata without touching canonical corpus or knowledge rows."""
    op.execute("DROP TABLE IF EXISTS ctl.projection_cleanup")
    op.execute("DROP TABLE IF EXISTS ctl.projection_evidence")
    op.execute("DROP TABLE IF EXISTS ctl.projection_active")
    op.execute("DROP TABLE IF EXISTS ctl.projections")
    op.execute("REVOKE CREATE ON SCHEMA search FROM arxiv_int_pipeline")
