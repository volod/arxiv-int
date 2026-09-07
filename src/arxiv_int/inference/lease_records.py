"""ctl.resource_lease row shape persisted as JSONL until the run ledger applies SQL."""

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

RESOURCE_KIND_GPU = "gpu"
LeaseStatus = Literal["acquired", "released", "cancelled", "rejected"]


@dataclass(frozen=True, slots=True)
class ResourceLeaseRecord:
    """One GPU resource-lease row."""

    lease_id: str
    resource_kind: str
    device_id: str
    holder_pid: int
    holder_run_id: str
    model_id: str
    backend: str
    workload: str
    status: LeaseStatus
    acquired_at: str
    released_at: str
    heartbeat_at: str
    detail: str
    gpu_need_gib: float
    cpu_ram_gib: float

    def to_dict(self) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "resource_kind": self.resource_kind,
            "device_id": self.device_id,
            "holder_pid": self.holder_pid,
            "holder_run_id": self.holder_run_id,
            "model_id": self.model_id,
            "backend": self.backend,
            "workload": self.workload,
            "status": self.status,
            "acquired_at": self.acquired_at,
            "released_at": self.released_at,
            "heartbeat_at": self.heartbeat_at,
            "detail": self.detail,
            "gpu_need_gib": self.gpu_need_gib,
            "cpu_ram_gib": self.cpu_ram_gib,
        }


def new_lease_id() -> str:
    return uuid4().hex


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def lease_record(
    *,
    run_id: str,
    model_id: str,
    backend: str,
    workload: str,
    device_id: str,
    status: LeaseStatus,
    detail: str,
    gpu_need_gib: float,
    cpu_ram_gib: float,
    lease_id: str | None = None,
    acquired_at: str = "",
    released_at: str = "",
) -> ResourceLeaseRecord:
    stamp = utc_now()
    acquired = acquired_at or (stamp if status == "acquired" else "")
    released = released_at or (stamp if status in {"released", "cancelled"} else "")
    return ResourceLeaseRecord(
        lease_id=lease_id or new_lease_id(),
        resource_kind=RESOURCE_KIND_GPU,
        device_id=device_id,
        holder_pid=os.getpid(),
        holder_run_id=run_id,
        model_id=model_id,
        backend=backend,
        workload=workload,
        status=status,
        acquired_at=acquired,
        released_at=released,
        heartbeat_at=stamp,
        detail=detail,
        gpu_need_gib=gpu_need_gib,
        cpu_ram_gib=cpu_ram_gib,
    )


def record_from_dict(payload: dict[str, object]) -> ResourceLeaseRecord:
    """Rebuild an acquired-lease row from gpu.lease.json."""
    return ResourceLeaseRecord(
        lease_id=str(payload.get("lease_id") or ""),
        resource_kind=str(payload.get("resource_kind") or RESOURCE_KIND_GPU),
        device_id=str(payload.get("device_id") or ""),
        holder_pid=_as_int(payload.get("holder_pid")),
        holder_run_id=str(payload.get("holder_run_id") or ""),
        model_id=str(payload.get("model_id") or ""),
        backend=str(payload.get("backend") or ""),
        workload=str(payload.get("workload") or ""),
        status="acquired",
        acquired_at=str(payload.get("acquired_at") or ""),
        released_at=str(payload.get("released_at") or ""),
        heartbeat_at=str(payload.get("heartbeat_at") or ""),
        detail=str(payload.get("detail") or ""),
        gpu_need_gib=_as_float(payload.get("gpu_need_gib")),
        cpu_ram_gib=_as_float(payload.get("cpu_ram_gib")),
    )


def _as_int(value: object) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    return 0


def _as_float(value: object) -> float:
    if isinstance(value, bool) or value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return 0.0
