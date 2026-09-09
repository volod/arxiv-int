"""SQLAlchemy metadata for ctl.stage_progress. Frozen DDL lives in revision 0001."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

PROGRESS_METADATA = MetaData(schema="ctl")
_NOW = text("now()")
PROGRESS_TABLES: tuple[str, ...] = ("stage_progress",)
WORKER_STATE_SQL = "worker_state IN ('running','slow','stalled','completed','failed')"


def _ts(name: str) -> Column[datetime]:
    return Column(name, DateTime(timezone=True), nullable=False, server_default=_NOW)


STAGE_PROGRESS = Table(
    "stage_progress",
    PROGRESS_METADATA,
    Column("progress_id", Text, primary_key=True),
    Column("stage_run_id", Text, nullable=True),
    Column("run_id", Text, nullable=False),
    Column("stage_name", Text, nullable=False),
    Column("shard_token", Text, nullable=False),
    Column("processed_items", BigInteger, nullable=False),
    Column("remaining_items", BigInteger, nullable=False),
    Column("byte_count", BigInteger, nullable=False),
    Column("error_count", Integer, nullable=False),
    Column("throughput_per_s", DOUBLE_PRECISION(), nullable=False),
    Column("eta_seconds", DOUBLE_PRECISION()),
    Column("elapsed_seconds", DOUBLE_PRECISION(), nullable=False),
    Column("worker_state", Text, nullable=False),
    Column("cpu_pct", DOUBLE_PRECISION(), nullable=False),
    Column("ram_available_gib", DOUBLE_PRECISION(), nullable=False),
    Column("disk_free_gib", DOUBLE_PRECISION(), nullable=False),
    Column("gpu_util_pct", DOUBLE_PRECISION(), nullable=False),
    Column("gpu_free_gib", DOUBLE_PRECISION(), nullable=False),
    Column("pg_size_bytes", BigInteger, nullable=False),
    Column("wal_bytes", BigInteger, nullable=False),
    Column("dropped_log_records", Integer, nullable=False),
    _ts("recorded_at"),
    CheckConstraint(WORKER_STATE_SQL, name="ck_stage_progress_worker_state"),
    schema="ctl",
)

Index("ix_stage_progress_run_id", STAGE_PROGRESS.c.run_id)
Index("ix_stage_progress_stage_run", STAGE_PROGRESS.c.stage_run_id)
Index("ix_stage_progress_recorded_at", STAGE_PROGRESS.c.recorded_at)
