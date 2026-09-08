"""SQLAlchemy metadata for ctl run-ledger tables. Frozen DDL lives in revision 0001."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

LEDGER_METADATA = MetaData(schema="ctl")
_NOW = text("now()")
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
RUN_STATUS_SQL = (
    "status IN ('pending','running','succeeded','failed','quarantined',"
    "'superseded','stale','pruned')"
)
LEASE_STATUS_SQL = "status IN ('acquired','released','expired','failed')"
RESOURCE_LEASE_STATUS_SQL = "status IN ('acquired','released','cancelled','rejected')"
MANIFEST_STATUS_SQL = "status IN ('staging','accepted','rejected')"
FAILURE_CLASS_SQL = "failure_class IN ('transient','permanent')"


def _ts(name: str) -> Column[datetime]:
    return Column(name, DateTime(timezone=True), nullable=False, server_default=_NOW)


RUNS = Table(
    "run",
    LEDGER_METADATA,
    Column("run_id", Text, primary_key=True),
    Column("generation_id", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("config_fingerprint", Text, nullable=False),
    _ts("created_at"),
    _ts("updated_at"),
    CheckConstraint(RUN_STATUS_SQL, name="ck_run_status"),
    schema="ctl",
)
STAGE_RUNS = Table(
    "stage_run",
    LEDGER_METADATA,
    Column("stage_run_id", Text, primary_key=True),
    Column("run_id", Text, ForeignKey("ctl.run.run_id"), nullable=False),
    Column("stage_name", Text, nullable=False),
    Column("stage_version", Text, nullable=False),
    Column("status", Text, nullable=False),
    _ts("created_at"),
    _ts("updated_at"),
    UniqueConstraint("run_id", "stage_name", name="uq_stage_run_run_stage"),
    CheckConstraint(RUN_STATUS_SQL, name="ck_stage_run_status"),
    schema="ctl",
)
SHARD_RUNS = Table(
    "shard_run",
    LEDGER_METADATA,
    Column("shard_run_id", Text, primary_key=True),
    Column("stage_run_id", Text, ForeignKey("ctl.stage_run.stage_run_id"), nullable=False),
    Column("run_id", Text, ForeignKey("ctl.run.run_id"), nullable=False),
    Column("shard_id", Text, nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("reuse_key", Text, nullable=False),
    Column("identity_json", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("lease_id", Text),
    Column("cache_hit", Text, nullable=False),
    Column("directory", Text),
    Column("quality_warnings", Text, nullable=False),
    _ts("created_at"),
    _ts("updated_at"),
    UniqueConstraint("reuse_key", "attempt", name="uq_shard_run_reuse_attempt"),
    CheckConstraint(RUN_STATUS_SQL, name="ck_shard_run_status"),
    CheckConstraint("attempt >= 1", name="ck_shard_run_attempt"),
    CheckConstraint("cache_hit IN ('true','false')", name="ck_shard_run_cache_hit"),
    schema="ctl",
)
REUSE_LEASES = Table(
    "reuse_lease",
    LEDGER_METADATA,
    Column("lease_id", Text, primary_key=True),
    Column("reuse_key", Text, nullable=False),
    Column("holder_shard_run_id", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("acquired_at", DateTime(timezone=True), nullable=False),
    Column("heartbeat_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(LEASE_STATUS_SQL, name="ck_reuse_lease_status"),
    schema="ctl",
)
CHECKPOINTS = Table(
    "checkpoint",
    LEDGER_METADATA,
    Column("checkpoint_id", Text, primary_key=True),
    Column("shard_run_id", Text, ForeignKey("ctl.shard_run.shard_run_id"), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("payload_digest", Text, nullable=False),
    _ts("created_at"),
    UniqueConstraint("shard_run_id", "sequence", name="uq_checkpoint_shard_sequence"),
    schema="ctl",
)
SHARD_ERRORS = Table(
    "shard_error",
    LEDGER_METADATA,
    Column("error_id", Text, primary_key=True),
    Column("shard_run_id", Text, ForeignKey("ctl.shard_run.shard_run_id"), nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("code", Text, nullable=False),
    Column("failure_class", Text, nullable=False),
    Column("detail", Text, nullable=False),
    _ts("created_at"),
    CheckConstraint(FAILURE_CLASS_SQL, name="ck_shard_error_class"),
    schema="ctl",
)
ARTIFACT_MANIFESTS = Table(
    "artifact_manifest",
    LEDGER_METADATA,
    Column("manifest_id", Text, primary_key=True),
    Column("shard_run_id", Text, ForeignKey("ctl.shard_run.shard_run_id"), nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("reuse_key", Text, nullable=False),
    Column("relative_path", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("sha256", Text, nullable=False),
    Column("byte_count", BigInteger, nullable=False),
    _ts("created_at"),
    CheckConstraint(MANIFEST_STATUS_SQL, name="ck_artifact_manifest_status"),
    schema="ctl",
)
ARTIFACT_LINEAGE = Table(
    "artifact_lineage",
    LEDGER_METADATA,
    Column("edge_id", Text, primary_key=True),
    Column("producer_reuse_key", Text, nullable=False),
    Column("consumer_reuse_key", Text, nullable=False),
    _ts("created_at"),
    UniqueConstraint("producer_reuse_key", "consumer_reuse_key", name="uq_artifact_lineage_edge"),
    schema="ctl",
)
RESOURCE_LEASES = Table(
    "resource_lease",
    LEDGER_METADATA,
    Column("lease_id", Text, primary_key=True),
    Column("resource_kind", Text, nullable=False),
    Column("device_id", Text, nullable=False),
    Column("holder_pid", BigInteger, nullable=False),
    Column("holder_run_id", Text, nullable=False),
    Column("model_id", Text, nullable=False),
    Column("backend", Text, nullable=False),
    Column("workload", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("acquired_at", Text, nullable=False),
    Column("released_at", Text, nullable=False),
    Column("heartbeat_at", Text, nullable=False),
    Column("detail", Text, nullable=False),
    Column("gpu_need_gib", DOUBLE_PRECISION(), nullable=False),
    Column("cpu_ram_gib", DOUBLE_PRECISION(), nullable=False),
    CheckConstraint(RESOURCE_LEASE_STATUS_SQL, name="ck_resource_lease_status"),
    schema="ctl",
)

Index("ix_shard_run_reuse_key", SHARD_RUNS.c.reuse_key)
Index("ix_stage_run_run_id", STAGE_RUNS.c.run_id)
Index("ix_reuse_lease_reuse_key", REUSE_LEASES.c.reuse_key)
Index(
    "uq_reuse_lease_active_key",
    REUSE_LEASES.c.reuse_key,
    unique=True,
    postgresql_where=text("status = 'acquired'"),
)
Index("ix_artifact_lineage_producer", ARTIFACT_LINEAGE.c.producer_reuse_key)
Index("ix_resource_lease_holder_run", RESOURCE_LEASES.c.holder_run_id)
