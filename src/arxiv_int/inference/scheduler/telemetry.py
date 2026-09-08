"""Narrow resource telemetry sink consumed by later pipeline logging."""

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from arxiv_int.inference.scheduler.lease_records import utc_now

_WRITE_LOCK = Lock()


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    """One load/throughput/VRAM/power or lease event. No prompts or secrets."""

    event: str
    run_id: str
    model_id: str
    backend: str
    device: str
    status: str
    detail: str
    gpu_need_gib: float = 0.0
    free_gpu_gib: float = 0.0
    used_gpu_gib: float = 0.0
    total_gpu_gib: float = 0.0
    ram_available_gib: float = 0.0
    database_reserve_gib: float = 0.0
    power_watts: float = 0.0
    gpu_util_pct: float = 0.0
    throughput_tokens_per_s: float = 0.0
    load_seconds: float = 0.0
    lease_id: str = ""
    recorded_at: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = {
            "event": self.event,
            "run_id": self.run_id,
            "model_id": self.model_id,
            "backend": self.backend,
            "device": self.device,
            "status": self.status,
            "detail": self.detail,
            "gpu_need_gib": self.gpu_need_gib,
            "free_gpu_gib": self.free_gpu_gib,
            "used_gpu_gib": self.used_gpu_gib,
            "total_gpu_gib": self.total_gpu_gib,
            "ram_available_gib": self.ram_available_gib,
            "database_reserve_gib": self.database_reserve_gib,
            "power_watts": self.power_watts,
            "gpu_util_pct": self.gpu_util_pct,
            "throughput_tokens_per_s": self.throughput_tokens_per_s,
            "load_seconds": self.load_seconds,
            "lease_id": self.lease_id,
            "recorded_at": self.recorded_at or utc_now(),
        }
        return payload


class TelemetrySink:
    """Append-only JSONL under $RUNS_DIR/<run-id>/telemetry/."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def record(self, event: TelemetryEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event.to_dict(), sort_keys=True) + "\n"
        with _WRITE_LOCK, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def record_snapshot(self, event: TelemetryEvent) -> None:
        """Write the latest snapshot beside the JSONL for operator inspection."""
        self.record(event)
        snapshot = self.path.with_name("resources.json")
        snapshot.write_text(json.dumps(event.to_dict(), indent=2, sort_keys=True) + "\n")


def telemetry_path(runs_dir: Path, run_id: str) -> Path:
    """Return the resource-events JSONL path for one run."""
    return runs_dir / run_id / "telemetry" / "resource-events.jsonl"
