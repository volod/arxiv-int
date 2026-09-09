"""SQLAlchemy metadata for reconcile control tables. Frozen DDL lives in 0001."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    text,
)

RECONCILE_METADATA = MetaData(schema="ctl")
_NOW = text("now()")
RECONCILE_TABLES: tuple[str, ...] = (
    "source_tombstone",
    "prune_event",
    "artifact_pin",
)
TOMBSTONE_REASON_SQL = "reason IN ('remove','supersede','retract')"
PRUNE_STATUS_SQL = "status IN ('planned','applied','refused')"
PIN_KIND_SQL = "kind IN ('pin','review','rollback','backup','ledger')"


def _ts(name: str) -> Column[datetime]:
    return Column(name, DateTime(timezone=True), nullable=False, server_default=_NOW)


SOURCE_TOMBSTONE = Table(
    "source_tombstone",
    RECONCILE_METADATA,
    Column("tombstone_id", Text, primary_key=True),
    Column("occurrence_id", Text, nullable=False),
    Column("silo_id", Text, nullable=False),
    Column("relative_path", Text, nullable=False),
    Column("content_hash", Text, nullable=False),
    Column("scan_id", Text, nullable=False),
    Column("generation_id", Text, nullable=False),
    Column("last_occurrence", Boolean, nullable=False),
    Column("reason", Text, nullable=False),
    _ts("created_at"),
    UniqueConstraint("occurrence_id", "scan_id", name="uq_source_tombstone_occurrence_scan"),
    CheckConstraint(TOMBSTONE_REASON_SQL, name="ck_source_tombstone_reason"),
    schema="ctl",
)
PRUNE_EVENT = Table(
    "prune_event",
    RECONCILE_METADATA,
    Column("event_id", Text, primary_key=True),
    Column("plan_id", Text, nullable=False),
    Column("fingerprint", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("bytes_removed", BigInteger, nullable=False),
    Column("detail", Text, nullable=False),
    _ts("created_at"),
    CheckConstraint(PRUNE_STATUS_SQL, name="ck_prune_event_status"),
    schema="ctl",
)
ARTIFACT_PIN = Table(
    "artifact_pin",
    RECONCILE_METADATA,
    Column("pin_id", Text, primary_key=True),
    Column("directory", Text, nullable=False),
    Column("reuse_key", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("generation_id", Text, nullable=False),
    _ts("created_at"),
    CheckConstraint(PIN_KIND_SQL, name="ck_artifact_pin_kind"),
    schema="ctl",
)

Index("ix_source_tombstone_content_hash", SOURCE_TOMBSTONE.c.content_hash)
Index("ix_source_tombstone_generation", SOURCE_TOMBSTONE.c.generation_id)
Index("ix_prune_event_plan_id", PRUNE_EVENT.c.plan_id)
Index("ix_artifact_pin_directory", ARTIFACT_PIN.c.directory)
