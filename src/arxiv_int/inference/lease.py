"""Host-wide exclusive GPU lease and ctl.resource_lease JSONL ledger."""

import fcntl
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Lock
from time import monotonic, sleep

from arxiv_int.inference.errors import LeaseCancelledError, LeaseConflictError
from arxiv_int.inference.lease_records import (
    LeaseStatus,
    ResourceLeaseRecord,
    lease_record,
    record_from_dict,
)

LEASE_POLL_SECONDS = 0.05

__all__ = [
    "HostGpuLease",
    "LeaseStatus",
    "ResourceLeaseRecord",
    "lease_record",
]


class HostGpuLease:
    """One exclusive GPU lease for the host: process flock plus in-process lock."""

    def __init__(self, state_dir: Path) -> None:
        self._dir = state_dir
        self._lock_path = state_dir / "gpu.lock"
        self._current_path = state_dir / "gpu.lease.json"
        self._ledger_path = state_dir / "ctl.resource_lease.jsonl"
        self._thread_lock = Lock()
        self._lock_file: int | None = None

    @contextmanager
    def hold(
        self,
        record: ResourceLeaseRecord,
        *,
        cancel: Event | None = None,
        wait_seconds: float = 30.0,
    ) -> Iterator[ResourceLeaseRecord]:
        acquired = self.acquire(record, cancel=cancel, wait_seconds=wait_seconds)
        try:
            yield acquired
        except BaseException:
            status: LeaseStatus = (
                "cancelled" if cancel is not None and cancel.is_set() else "released"
            )
            self.release(acquired, status=status)
            raise
        else:
            self.release(acquired, status="released")

    def acquire(
        self,
        record: ResourceLeaseRecord,
        *,
        cancel: Event | None = None,
        wait_seconds: float = 30.0,
    ) -> ResourceLeaseRecord:
        deadline = monotonic() + max(wait_seconds, 0.0)
        self._wait_thread(cancel, deadline)
        try:
            self._wait_flock(cancel, deadline)
            acquired = lease_record(
                run_id=record.holder_run_id,
                model_id=record.model_id,
                backend=record.backend,
                workload=record.workload,
                device_id=record.device_id,
                status="acquired",
                detail=record.detail,
                gpu_need_gib=record.gpu_need_gib,
                cpu_ram_gib=record.cpu_ram_gib,
                lease_id=record.lease_id,
            )
            self._persist(acquired)
            return acquired
        except BaseException:
            self._unlock()
            raise

    def release(self, record: ResourceLeaseRecord, *, status: LeaseStatus = "released") -> None:
        finished = lease_record(
            run_id=record.holder_run_id,
            model_id=record.model_id,
            backend=record.backend,
            workload=record.workload,
            device_id=record.device_id,
            status=status,
            detail=record.detail,
            gpu_need_gib=record.gpu_need_gib,
            cpu_ram_gib=record.cpu_ram_gib,
            lease_id=record.lease_id,
            acquired_at=record.acquired_at,
        )
        try:
            self._persist(finished)
        finally:
            self._unlock()

    def append_rejected(self, record: ResourceLeaseRecord) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        _append_jsonl(self._ledger_path, record)

    def current(self) -> ResourceLeaseRecord | None:
        if not self._current_path.is_file():
            return None
        payload = json.loads(self._current_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("status") != "acquired":
            return None
        return record_from_dict(payload)

    def _wait_thread(self, cancel: Event | None, deadline: float) -> None:
        while True:
            _raise_if_cancelled(cancel)
            if self._thread_lock.acquire(blocking=False):
                return
            _raise_if_expired(deadline)
            sleep(LEASE_POLL_SECONDS)

    def _wait_flock(self, cancel: Event | None, deadline: float) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        handle = os.open(self._lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        self._lock_file = handle
        while True:
            _raise_if_cancelled(cancel)
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                _raise_if_expired(deadline)
                sleep(LEASE_POLL_SECONDS)

    def _persist(self, record: ResourceLeaseRecord) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(record.to_dict(), sort_keys=True)
        self._current_path.write_text(payload + "\n", encoding="utf-8")
        _append_jsonl(self._ledger_path, record)

    def _unlock(self) -> None:
        handle = self._lock_file
        self._lock_file = None
        if handle is not None:
            try:
                fcntl.flock(handle, fcntl.LOCK_UN)
            finally:
                os.close(handle)
        if self._thread_lock.locked():
            self._thread_lock.release()


def _append_jsonl(path: Path, record: ResourceLeaseRecord) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")


def _raise_if_cancelled(cancel: Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise LeaseCancelledError("GPU lease wait cancelled")


def _raise_if_expired(deadline: float) -> None:
    if monotonic() >= deadline:
        raise LeaseConflictError("GPU lease is held by another workload")
