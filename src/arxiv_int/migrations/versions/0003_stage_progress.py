"""pipeline stage progress overlay

Frozen control-plane overlay: this revision never imports today's runtime modules
to decide what it creates.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: None = None
depends_on: None = None

CONTRACT_FINGERPRINTS: dict[str, str] = {}
REVIEW_NOTES: tuple[str, ...] = (
    "Adds ctl.stage_progress snapshots for throttled pipeline telemetry and Grafana SQL.",
)
IRREVERSIBLE_REASON: str = ""
_NOW = sa.text("now()")
PROGRESS_TABLES: tuple[str, ...] = ("stage_progress",)


def _ts(name: str) -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=_NOW)


def schema_metadata() -> sa.MetaData:
    """Return frozen progress-table definitions used for creation and inspection."""
    metadata = sa.MetaData()
    sa.Table(
        "stage_progress",
        metadata,
        sa.Column("progress_id", sa.Text(), primary_key=True),
        sa.Column("stage_run_id", sa.Text(), nullable=True),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("stage_name", sa.Text(), nullable=False),
        sa.Column("shard_token", sa.Text(), nullable=False),
        sa.Column("processed_items", sa.BigInteger(), nullable=False),
        sa.Column("remaining_items", sa.BigInteger(), nullable=False),
        sa.Column("byte_count", sa.BigInteger(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("throughput_per_s", DOUBLE_PRECISION(), nullable=False),
        sa.Column("eta_seconds", DOUBLE_PRECISION()),
        sa.Column("elapsed_seconds", DOUBLE_PRECISION(), nullable=False),
        sa.Column("worker_state", sa.Text(), nullable=False),
        sa.Column("cpu_pct", DOUBLE_PRECISION(), nullable=False),
        sa.Column("ram_available_gib", DOUBLE_PRECISION(), nullable=False),
        sa.Column("disk_free_gib", DOUBLE_PRECISION(), nullable=False),
        sa.Column("gpu_util_pct", DOUBLE_PRECISION(), nullable=False),
        sa.Column("gpu_free_gib", DOUBLE_PRECISION(), nullable=False),
        sa.Column("pg_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("wal_bytes", sa.BigInteger(), nullable=False),
        sa.Column("dropped_log_records", sa.Integer(), nullable=False),
        _ts("recorded_at"),
        sa.CheckConstraint(
            "worker_state IN ('running','slow','stalled','completed','failed')",
            name="ck_stage_progress_worker_state",
        ),
        schema="ctl",
    )
    return metadata


def upgrade() -> None:
    """Create stage_progress and grant pipeline write plus reader select."""
    metadata = schema_metadata()
    for definition in metadata.sorted_tables:
        op.execute(sa.schema.CreateTable(definition))
        for index in sorted(definition.indexes, key=lambda item: str(item.name)):
            op.execute(sa.schema.CreateIndex(index))
    op.execute("CREATE INDEX ix_stage_progress_run_id ON ctl.stage_progress (run_id)")
    op.execute("CREATE INDEX ix_stage_progress_stage_run ON ctl.stage_progress (stage_run_id)")
    op.execute(
        "CREATE INDEX ix_stage_progress_recorded_at ON ctl.stage_progress (recorded_at)"
    )
    op.execute(
        "ALTER TABLE ctl.stage_progress ADD CONSTRAINT fk_stage_progress_stage_run "
        "FOREIGN KEY (stage_run_id) REFERENCES ctl.stage_run (stage_run_id)"
    )
    names = ", ".join(f"ctl.{name}" for name in PROGRESS_TABLES)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {names} TO arxiv_int_pipeline")
    op.execute(f"GRANT SELECT ON {names} TO arxiv_int_dbt, arxiv_int_reader")


def downgrade() -> None:
    """Drop progress snapshots without touching the 0002 run ledger."""
    for name in reversed(PROGRESS_TABLES):
        op.execute(f"DROP TABLE IF EXISTS ctl.{name} CASCADE")
