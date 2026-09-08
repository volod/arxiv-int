"""Optional PostgreSQL writer for ctl.stage_progress and stage_run heartbeats."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine, insert, text

from arxiv_int.observability.events import ProgressSnapshot
from arxiv_int.observability.tables import STAGE_PROGRESS


def _as_datetime(snapshot: ProgressSnapshot) -> datetime:
    parsed = datetime.fromisoformat(snapshot.ts.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


class PostgresProgressStore:
    """Insert progress rows and touch ctl.stage_run.updated_at when linked."""

    def __init__(self, engine: Engine, *, stage_run_id: str | None = None) -> None:
        self._engine = engine
        self._stage_run_id = stage_run_id

    def record(self, snapshot: ProgressSnapshot) -> None:
        stamp = _as_datetime(snapshot)
        resources = snapshot.resources
        values = {
            "progress_id": f"prg-{uuid4().hex}",
            "stage_run_id": self._stage_run_id,
            "run_id": snapshot.run_id,
            "stage_name": snapshot.stage,
            "shard_token": snapshot.shard_token,
            "processed_items": snapshot.processed,
            "remaining_items": snapshot.remaining,
            "byte_count": snapshot.bytes,
            "error_count": snapshot.errors,
            "throughput_per_s": snapshot.throughput_per_s,
            "eta_seconds": snapshot.eta_seconds,
            "elapsed_seconds": snapshot.elapsed_seconds,
            "worker_state": snapshot.worker_state,
            "cpu_pct": resources.cpu_pct,
            "ram_available_gib": resources.ram_available_gib,
            "disk_free_gib": resources.disk_free_gib,
            "gpu_util_pct": resources.gpu_util_pct,
            "gpu_free_gib": resources.gpu_free_gib,
            "pg_size_bytes": resources.pg_size_bytes,
            "wal_bytes": resources.wal_bytes,
            "dropped_log_records": snapshot.dropped_log_records,
            "recorded_at": stamp,
        }
        with self._engine.begin() as connection:
            connection.execute(insert(STAGE_PROGRESS).values(**values))
            if self._stage_run_id:
                connection.execute(
                    text(
                        "UPDATE ctl.stage_run SET updated_at = :stamp "
                        "WHERE stage_run_id = :stage_run_id"
                    ),
                    {"stamp": stamp, "stage_run_id": self._stage_run_id},
                )
