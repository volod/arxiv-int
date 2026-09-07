"""Encode and decode ctl ledger rows for bound SQLAlchemy transactions."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import Connection, func, insert, select, text
from sqlalchemy.engine import RowMapping

from arxiv_int.inference.lease_records import ResourceLeaseRecord
from arxiv_int.pipeline.control.fingerprints import ReuseIdentity
from arxiv_int.pipeline.control.model import LeaseRecord, RunRecord, ShardRecord, StageRecord
from arxiv_int.pipeline.control.states import as_lease_status, as_shard_status
from arxiv_int.pipeline.control.tables import RESOURCE_LEASES, SHARD_RUNS


def insert_resource_lease(connection: Connection, record: ResourceLeaseRecord) -> None:
    """Insert one GPU resource-lease row in the caller's transaction."""
    connection.execute(insert(RESOURCE_LEASES).values(**record.to_dict()))


def assigned_shard(connection: Connection, record: ShardRecord) -> ShardRecord:
    """Lock the reuse key and assign the next attempt number in this transaction."""
    digest = hashlib.sha256(record.reuse_key.encode("ascii")).digest()
    lock_key = int.from_bytes(digest[:8], "big") % (2**63)
    connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    highest = connection.execute(
        select(func.max(SHARD_RUNS.c.attempt)).where(SHARD_RUNS.c.reuse_key == record.reuse_key)
    ).scalar()
    return replace(record, attempt=int(highest or 0) + 1)


def as_datetime(now: float) -> datetime:
    """Convert a POSIX timestamp to UTC."""
    return datetime.fromtimestamp(now, UTC)


def as_timestamp(value: object) -> float:
    """Convert a datetime or numeric database value to POSIX seconds."""
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


def run_from_row(row: RowMapping) -> RunRecord:
    """Rebuild a run record from a mapping row."""
    data = dict(row)
    return RunRecord(
        str(data["run_id"]),
        str(data["generation_id"]),
        str(data["status"]),
        str(data["config_fingerprint"]),
        as_timestamp(data["created_at"]),
        as_timestamp(data["updated_at"]),
    )


def stage_from_row(row: RowMapping) -> StageRecord:
    """Rebuild a stage record from a mapping row."""
    data = dict(row)
    return StageRecord(
        str(data["stage_run_id"]),
        str(data["run_id"]),
        str(data["stage_name"]),
        str(data["stage_version"]),
        str(data["status"]),
        as_timestamp(data["created_at"]),
        as_timestamp(data["updated_at"]),
    )


def shard_from_row(row: RowMapping) -> ShardRecord:
    """Rebuild a shard attempt from a mapping row."""
    data = dict(row)
    payload_raw = json.loads(str(data["identity_json"]))
    if not isinstance(payload_raw, dict):
        raise ValueError("identity_json must be an object")
    identity = ReuseIdentity(
        stage=str(payload_raw["stage"]),
        stage_version=str(payload_raw["stageVersion"]),
        shard_id=str(payload_raw["shardId"]),
        parameters=_string_map(payload_raw["parameters"]),
        input_hashes=tuple(str(item) for item in _sequence(payload_raw["inputHashes"])),
        upstream_manifest_ids=tuple(
            str(item) for item in _sequence(payload_raw["upstreamManifestIds"])
        ),
        owned=_string_map(payload_raw["owned"]),
    )
    warnings = str(data.get("quality_warnings") or "")
    directory = data.get("directory")
    lease_id = data.get("lease_id")
    return ShardRecord(
        str(data["shard_run_id"]),
        str(data["stage_run_id"]),
        str(data["run_id"]),
        str(data["shard_id"]),
        _as_int(data["attempt"]),
        str(data["reuse_key"]),
        identity,
        as_shard_status(str(data["status"])),
        None if lease_id is None else str(lease_id),
        str(data["cache_hit"]) == "true",
        as_timestamp(data["created_at"]),
        as_timestamp(data["updated_at"]),
        None if directory is None else str(directory),
        tuple(item for item in warnings.split(",") if item),
    )


def shard_values(record: ShardRecord) -> dict[str, object]:
    """Return insert/update values for one shard_run row."""
    identity = record.identity
    payload = {
        "inputHashes": list(identity.input_hashes),
        "owned": dict(identity.owned),
        "parameters": dict(identity.parameters),
        "shardId": identity.shard_id,
        "stage": identity.stage,
        "stageVersion": identity.stage_version,
        "upstreamManifestIds": list(identity.upstream_manifest_ids),
    }
    return {
        "attempt": record.attempt,
        "cache_hit": "true" if record.cache_hit else "false",
        "created_at": as_datetime(record.created_at),
        "directory": record.directory,
        "identity_json": json.dumps(payload, sort_keys=True),
        "lease_id": record.lease_id,
        "quality_warnings": ",".join(record.quality_warnings),
        "reuse_key": record.reuse_key,
        "run_id": record.run_id,
        "shard_id": record.shard_id,
        "shard_run_id": record.shard_run_id,
        "stage_run_id": record.stage_run_id,
        "status": record.status,
        "updated_at": as_datetime(record.updated_at),
    }


def lease_from_row(row: RowMapping) -> LeaseRecord:
    """Rebuild a reuse-lease record from a mapping row."""
    data = dict(row)
    return LeaseRecord(
        str(data["lease_id"]),
        str(data["reuse_key"]),
        str(data["holder_shard_run_id"]),
        as_lease_status(str(data["status"])),
        as_timestamp(data["acquired_at"]),
        as_timestamp(data["heartbeat_at"]),
        as_timestamp(data["expires_at"]),
    )


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"expected int, got {type(value)!r}")
    return value


def _string_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise TypeError("expected object")
    return {str(key): str(item) for key, item in value.items()}


def _sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise TypeError("expected sequence")
    return tuple(value)
