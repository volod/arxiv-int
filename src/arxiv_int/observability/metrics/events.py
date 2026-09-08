"""Typed observability events. Operational metadata only; no corpus text."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from arxiv_int.observability.metrics.constants import SCHEMA_ID, WORKER_STATE_BY_NAME, WorkerState


@dataclass(frozen=True, slots=True)
class ResourceSample:
    """Bounded host and store pressure for one progress tick."""

    cpu_pct: float = 0.0
    ram_available_gib: float = 0.0
    ram_total_gib: float = 0.0
    disk_free_gib: float = 0.0
    disk_total_gib: float = 0.0
    gpu_util_pct: float = 0.0
    gpu_free_gib: float = 0.0
    gpu_used_gib: float = 0.0
    gpu_total_gib: float = 0.0
    gpu_power_watts: float = 0.0
    pg_size_bytes: int = 0
    wal_bytes: int = 0
    device: str = "cpu"

    def as_dict(self) -> dict[str, object]:
        """Return JSON-serializable resource fields."""
        return {
            "cpu_pct": self.cpu_pct,
            "device": self.device,
            "disk_free_gib": self.disk_free_gib,
            "disk_total_gib": self.disk_total_gib,
            "gpu_free_gib": self.gpu_free_gib,
            "gpu_power_watts": self.gpu_power_watts,
            "gpu_total_gib": self.gpu_total_gib,
            "gpu_used_gib": self.gpu_used_gib,
            "gpu_util_pct": self.gpu_util_pct,
            "pg_size_bytes": self.pg_size_bytes,
            "ram_available_gib": self.ram_available_gib,
            "ram_total_gib": self.ram_total_gib,
            "wal_bytes": self.wal_bytes,
        }


@dataclass(frozen=True, slots=True)
class ProgressSnapshot:
    """One throttled progress row for logs, status, and ctl.stage_progress."""

    ts: str
    run_id: str
    stage: str
    shard_token: str
    processed: int
    remaining: int
    bytes: int
    errors: int
    throughput_per_s: float
    eta_seconds: float | None
    elapsed_seconds: float
    worker_state: WorkerState
    resources: ResourceSample
    dropped_log_records: int = 0
    event: str = "progress"
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        """Return the JSONL object for schema ``arxiv-int.observability.v1``."""
        payload: dict[str, object] = {
            "bytes": self.bytes,
            "detail": self.detail,
            "dropped_log_records": self.dropped_log_records,
            "elapsed_seconds": self.elapsed_seconds,
            "errors": self.errors,
            "eta_seconds": self.eta_seconds,
            "event": self.event,
            "processed": self.processed,
            "remaining": self.remaining,
            "run_id": self.run_id,
            "schema": SCHEMA_ID,
            "shard": self.shard_token,
            "stage": self.stage,
            "throughput_per_s": self.throughput_per_s,
            "ts": self.ts,
            "worker_state": self.worker_state,
        }
        payload.update(self.resources.as_dict())
        return payload


def snapshot_from_mapping(payload: Mapping[str, Any]) -> ProgressSnapshot:
    """Rebuild a snapshot from a JSON object; missing resource fields stay zero."""
    resources = ResourceSample(
        cpu_pct=float(payload.get("cpu_pct", 0.0)),
        ram_available_gib=float(payload.get("ram_available_gib", 0.0)),
        ram_total_gib=float(payload.get("ram_total_gib", 0.0)),
        disk_free_gib=float(payload.get("disk_free_gib", 0.0)),
        disk_total_gib=float(payload.get("disk_total_gib", 0.0)),
        gpu_util_pct=float(payload.get("gpu_util_pct", 0.0)),
        gpu_free_gib=float(payload.get("gpu_free_gib", 0.0)),
        gpu_used_gib=float(payload.get("gpu_used_gib", 0.0)),
        gpu_total_gib=float(payload.get("gpu_total_gib", 0.0)),
        gpu_power_watts=float(payload.get("gpu_power_watts", 0.0)),
        pg_size_bytes=int(payload.get("pg_size_bytes", 0)),
        wal_bytes=int(payload.get("wal_bytes", 0)),
        device=str(payload.get("device", "cpu")),
    )
    eta = payload.get("eta_seconds")
    state = WORKER_STATE_BY_NAME.get(str(payload.get("worker_state", "running")), "running")
    return ProgressSnapshot(
        ts=str(payload["ts"]),
        run_id=str(payload["run_id"]),
        stage=str(payload["stage"]),
        shard_token=str(payload.get("shard", "")),
        processed=int(payload.get("processed", 0)),
        remaining=int(payload.get("remaining", 0)),
        bytes=int(payload.get("bytes", 0)),
        errors=int(payload.get("errors", 0)),
        throughput_per_s=float(payload.get("throughput_per_s", 0.0)),
        eta_seconds=None if eta is None else float(eta),
        elapsed_seconds=float(payload.get("elapsed_seconds", 0.0)),
        worker_state=state,
        resources=resources,
        dropped_log_records=int(payload.get("dropped_log_records", 0)),
        event=str(payload.get("event", "progress")),
        detail=str(payload.get("detail", "")),
    )
