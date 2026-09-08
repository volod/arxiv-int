"""pipeline source tombstone, prune-event, and artifact-pin overlay

Frozen control-plane overlay: this revision never imports today's runtime modules
to decide what it creates.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: None = None
depends_on: None = None

CONTRACT_FINGERPRINTS: dict[str, str] = {}
REVIEW_NOTES: tuple[str, ...] = (
    "Adds ctl.source_tombstone, ctl.prune_event, and ctl.artifact_pin for incremental "
    "reconciliation and two-phase stale prune.",
)
IRREVERSIBLE_REASON: str = ""
_NOW = sa.text("now()")
RECONCILE_TABLES: tuple[str, ...] = (
    "source_tombstone",
    "prune_event",
    "artifact_pin",
)


def _ts(name: str) -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=_NOW)


def schema_metadata() -> sa.MetaData:
    """Return frozen reconcile-table definitions used for creation and inspection."""
    metadata = sa.MetaData()
    sa.Table(
        "source_tombstone",
        metadata,
        sa.Column("tombstone_id", sa.Text(), primary_key=True),
        sa.Column("occurrence_id", sa.Text(), nullable=False),
        sa.Column("silo_id", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("scan_id", sa.Text(), nullable=False),
        sa.Column("generation_id", sa.Text(), nullable=False),
        sa.Column("last_occurrence", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        _ts("created_at"),
        sa.UniqueConstraint(
            "occurrence_id", "scan_id", name="uq_source_tombstone_occurrence_scan"
        ),
        sa.CheckConstraint(
            "reason IN ('remove','supersede','retract')",
            name="ck_source_tombstone_reason",
        ),
        schema="ctl",
    )
    sa.Table(
        "prune_event",
        metadata,
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("bytes_removed", sa.BigInteger(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        _ts("created_at"),
        sa.CheckConstraint(
            "status IN ('planned','applied','refused')",
            name="ck_prune_event_status",
        ),
        schema="ctl",
    )
    sa.Table(
        "artifact_pin",
        metadata,
        sa.Column("pin_id", sa.Text(), primary_key=True),
        sa.Column("directory", sa.Text(), nullable=False),
        sa.Column("reuse_key", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("generation_id", sa.Text(), nullable=False),
        _ts("created_at"),
        sa.CheckConstraint(
            "kind IN ('pin','review','rollback','backup','ledger')",
            name="ck_artifact_pin_kind",
        ),
        schema="ctl",
    )
    return metadata


def upgrade() -> None:
    """Create reconcile tables and grant pipeline write plus reader select."""
    metadata = schema_metadata()
    for definition in metadata.sorted_tables:
        op.execute(sa.schema.CreateTable(definition))
        for index in sorted(definition.indexes, key=lambda item: str(item.name)):
            op.execute(sa.schema.CreateIndex(index))
    op.execute(
        "CREATE INDEX ix_source_tombstone_content_hash ON ctl.source_tombstone (content_hash)"
    )
    op.execute(
        "CREATE INDEX ix_source_tombstone_generation ON ctl.source_tombstone (generation_id)"
    )
    op.execute("CREATE INDEX ix_prune_event_plan_id ON ctl.prune_event (plan_id)")
    op.execute("CREATE INDEX ix_artifact_pin_directory ON ctl.artifact_pin (directory)")
    names = ", ".join(f"ctl.{name}" for name in RECONCILE_TABLES)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {names} TO arxiv_int_pipeline")
    op.execute(f"GRANT SELECT ON {names} TO arxiv_int_dbt, arxiv_int_reader")


def downgrade() -> None:
    """Drop reconcile tables without touching the 0003 progress overlay."""
    for name in reversed(RECONCILE_TABLES):
        op.execute(f"DROP TABLE IF EXISTS ctl.{name} CASCADE")
