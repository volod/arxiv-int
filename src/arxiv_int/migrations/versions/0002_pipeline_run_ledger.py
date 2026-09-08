"""pipeline run ledger tables

Frozen control-plane overlay: this revision never imports today's runtime modules
to decide what it creates.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: None = None
depends_on: None = None

CONTRACT_FINGERPRINTS: dict[str, str] = {}
REVIEW_NOTES: tuple[str, ...] = (
    "Adds ctl run/stage/shard ledger, reuse leases, checkpoints, errors, manifests, lineage, and resource_lease.",
)
IRREVERSIBLE_REASON: str = ""
_NOW = sa.text("now()")
_RUN_STATUS = (
    "status IN ('pending','running','succeeded','failed','quarantined',"
    "'superseded','stale','pruned')"
)
LEDGER_TABLES: tuple[str, ...] = (
    "run",
    "stage_run",
    "shard_run",
    "reuse_lease",
    "checkpoint",
    "shard_error",
    "artifact_manifest",
    "artifact_lineage",
    "resource_lease",
)


def _ts(name: str) -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=_NOW)


def schema_metadata() -> sa.MetaData:
    """Return frozen ledger table definitions used for creation and inspection."""
    metadata = sa.MetaData()
    sa.Table(
        "run",
        metadata,
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("generation_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("config_fingerprint", sa.Text(), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.CheckConstraint(_RUN_STATUS, name="ck_run_status"),
        schema="ctl",
    )
    sa.Table(
        "stage_run",
        metadata,
        sa.Column("stage_run_id", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("ctl.run.run_id"), nullable=False),
        sa.Column("stage_name", sa.Text(), nullable=False),
        sa.Column("stage_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.UniqueConstraint("run_id", "stage_name", name="uq_stage_run_run_stage"),
        sa.CheckConstraint(_RUN_STATUS, name="ck_stage_run_status"),
        schema="ctl",
    )
    sa.Table(
        "shard_run",
        metadata,
        sa.Column("shard_run_id", sa.Text(), primary_key=True),
        sa.Column("stage_run_id", sa.Text(), sa.ForeignKey("ctl.stage_run.stage_run_id"), nullable=False),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("ctl.run.run_id"), nullable=False),
        sa.Column("shard_id", sa.Text(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("reuse_key", sa.Text(), nullable=False),
        sa.Column("identity_json", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("lease_id", sa.Text()),
        sa.Column("cache_hit", sa.Text(), nullable=False),
        sa.Column("directory", sa.Text()),
        sa.Column("quality_warnings", sa.Text(), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.UniqueConstraint("reuse_key", "attempt", name="uq_shard_run_reuse_attempt"),
        sa.CheckConstraint(_RUN_STATUS, name="ck_shard_run_status"),
        sa.CheckConstraint("attempt >= 1", name="ck_shard_run_attempt"),
        sa.CheckConstraint("cache_hit IN ('true','false')", name="ck_shard_run_cache_hit"),
        schema="ctl",
    )
    sa.Table(
        "reuse_lease",
        metadata,
        sa.Column("lease_id", sa.Text(), primary_key=True),
        sa.Column("reuse_key", sa.Text(), nullable=False),
        sa.Column("holder_shard_run_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('acquired','released','expired','failed')", name="ck_reuse_lease_status"
        ),
        schema="ctl",
    )
    sa.Table(
        "checkpoint",
        metadata,
        sa.Column("checkpoint_id", sa.Text(), primary_key=True),
        sa.Column("shard_run_id", sa.Text(), sa.ForeignKey("ctl.shard_run.shard_run_id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payload_digest", sa.Text(), nullable=False),
        _ts("created_at"),
        sa.UniqueConstraint("shard_run_id", "sequence", name="uq_checkpoint_shard_sequence"),
        schema="ctl",
    )
    sa.Table(
        "shard_error",
        metadata,
        sa.Column("error_id", sa.Text(), primary_key=True),
        sa.Column("shard_run_id", sa.Text(), sa.ForeignKey("ctl.shard_run.shard_run_id"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("failure_class", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        _ts("created_at"),
        sa.CheckConstraint(
            "failure_class IN ('transient','permanent')", name="ck_shard_error_class"
        ),
        schema="ctl",
    )
    sa.Table(
        "artifact_manifest",
        metadata,
        sa.Column("manifest_id", sa.Text(), primary_key=True),
        sa.Column("shard_run_id", sa.Text(), sa.ForeignKey("ctl.shard_run.shard_run_id"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("reuse_key", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("byte_count", sa.BigInteger(), nullable=False),
        _ts("created_at"),
        sa.CheckConstraint(
            "status IN ('staging','accepted','rejected')", name="ck_artifact_manifest_status"
        ),
        schema="ctl",
    )
    sa.Table(
        "artifact_lineage",
        metadata,
        sa.Column("edge_id", sa.Text(), primary_key=True),
        sa.Column("producer_reuse_key", sa.Text(), nullable=False),
        sa.Column("consumer_reuse_key", sa.Text(), nullable=False),
        _ts("created_at"),
        sa.UniqueConstraint(
            "producer_reuse_key", "consumer_reuse_key", name="uq_artifact_lineage_edge"
        ),
        schema="ctl",
    )
    sa.Table(
        "resource_lease",
        metadata,
        sa.Column("lease_id", sa.Text(), primary_key=True),
        *(
            sa.Column(name, sa.Text(), nullable=False)
            for name in (
                "resource_kind",
                "device_id",
                "holder_run_id",
                "model_id",
                "backend",
                "workload",
                "status",
                "acquired_at",
                "released_at",
                "heartbeat_at",
                "detail",
            )
        ),
        sa.Column("holder_pid", sa.BigInteger(), nullable=False),
        sa.Column("gpu_need_gib", DOUBLE_PRECISION(), nullable=False),
        sa.Column("cpu_ram_gib", DOUBLE_PRECISION(), nullable=False),
        sa.CheckConstraint(
            "status IN ('acquired','released','cancelled','rejected')",
            name="ck_resource_lease_status",
        ),
        schema="ctl",
    )
    return metadata


def upgrade() -> None:
    """Create run-ledger tables, indexes, and pipeline grants."""
    metadata = schema_metadata()
    for definition in metadata.sorted_tables:
        op.execute(sa.schema.CreateTable(definition))
        for index in sorted(definition.indexes, key=lambda item: str(item.name)):
            op.execute(sa.schema.CreateIndex(index))
    op.execute("CREATE INDEX ix_shard_run_reuse_key ON ctl.shard_run (reuse_key)")
    op.execute("CREATE INDEX ix_stage_run_run_id ON ctl.stage_run (run_id)")
    op.execute("CREATE INDEX ix_reuse_lease_reuse_key ON ctl.reuse_lease (reuse_key)")
    op.execute(
        "CREATE UNIQUE INDEX uq_reuse_lease_active_key ON ctl.reuse_lease (reuse_key) "
        "WHERE status = 'acquired'"
    )
    op.execute("CREATE INDEX ix_artifact_lineage_producer ON ctl.artifact_lineage (producer_reuse_key)")
    op.execute("CREATE INDEX ix_resource_lease_holder_run ON ctl.resource_lease (holder_run_id)")
    names = ", ".join(f"ctl.{name}" for name in LEDGER_TABLES)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {names} TO arxiv_int_pipeline")
    op.execute(f"GRANT SELECT ON {names} TO arxiv_int_dbt, arxiv_int_reader")


def downgrade() -> None:
    """Drop ledger tables without touching canonical contract data."""
    for name in reversed(LEDGER_TABLES):
        op.execute(f"DROP TABLE IF EXISTS ctl.{name} CASCADE")
