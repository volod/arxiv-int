"""SQLAlchemy metadata for ctl projection registry tables."""

from sqlalchemy import BigInteger, Column, DateTime, MetaData, Table, Text

_METADATA = MetaData(schema="ctl")
PROJECTIONS = Table(
    "projections",
    _METADATA,
    Column("projection_id", Text, primary_key=True),
    Column("kind", Text, nullable=False),
    Column("version_id", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("schema_version", Text, nullable=False),
    Column("engine", Text, nullable=False),
    Column("engine_object", Text),
    Column("input_fingerprint", Text),
    Column("row_count", BigInteger),
    Column("checksum", Text),
    Column("quality_status", Text),
    Column("last_committed_id", Text),
    Column("canonical_fact_version", Text),
    Column("run_id", Text, nullable=False),
    Column("created_at", DateTime(timezone=True)),
    schema="ctl",
)
ACTIVE = Table(
    "projection_active",
    _METADATA,
    Column("kind", Text, primary_key=True),
    Column("projection_id", Text, nullable=False),
    Column("previous_projection_id", Text),
    Column("switched_at", DateTime(timezone=True)),
    schema="ctl",
)
EVIDENCE = Table(
    "projection_evidence",
    _METADATA,
    Column("evidence_id", Text, primary_key=True),
    Column("projection_id", Text, nullable=False),
    Column("check_name", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("detail", Text),
    Column("checked_count", BigInteger),
    Column("failed_count", BigInteger),
    Column("created_at", DateTime(timezone=True)),
    schema="ctl",
)
CLEANUP = Table(
    "projection_cleanup",
    _METADATA,
    Column("cleanup_id", Text, primary_key=True),
    Column("projection_id", Text, nullable=False),
    Column("engine_object", Text),
    Column("status", Text, nullable=False),
    Column("planned_at", DateTime(timezone=True)),
    schema="ctl",
)
