"""Cross-process GPU lease contention, crash release, and stale current rows."""

from multiprocessing import get_context
from pathlib import Path

import pytest

from arxiv_int.inference.errors import LeaseConflictError
from arxiv_int.inference.lease import HostGpuLease, lease_record


def _row(run_id: str, model_id: str):
    return lease_record(
        run_id=run_id,
        model_id=model_id,
        backend="ollama",
        workload="generation",
        device_id="cuda:0",
        status="acquired",
        detail="test",
        gpu_need_gib=3.0,
        cpu_ram_gib=4.0,
    )


def _hold_until_release(state_dir: str, ready: object, release: object) -> None:
    lease = HostGpuLease(Path(state_dir))
    with lease.hold(_row("holder", "held"), wait_seconds=5.0):
        ready.set()
        release.wait(timeout=15.0)


def _acquire_and_crash(state_dir: str, ready: object) -> None:
    import os

    lease = HostGpuLease(Path(state_dir))
    lease.acquire(_row("holder", "held"), wait_seconds=5.0)
    ready.set()
    os._exit(1)


def test_flock_serializes_two_processes(tmp_path: Path) -> None:
    ctx = get_context("spawn")
    ready = ctx.Event()
    release = ctx.Event()
    holder = ctx.Process(target=_hold_until_release, args=(str(tmp_path), ready, release))
    holder.start()
    try:
        assert ready.wait(timeout=5)
        lease = HostGpuLease(tmp_path)
        with pytest.raises(LeaseConflictError, match="held"):
            lease.acquire(_row("waiter", "waiter"), wait_seconds=0.0)
        current = lease.current()
        assert current is not None
        assert current.model_id == "held"
    finally:
        release.set()
        holder.join(timeout=5)
        if holder.is_alive():
            holder.kill()
            holder.join(timeout=2)
    assert holder.exitcode == 0
    lease = HostGpuLease(tmp_path)
    with lease.hold(_row("after", "after"), wait_seconds=1.0) as held:
        assert held.model_id == "after"


def test_killed_holder_releases_flock_and_stale_current(tmp_path: Path) -> None:
    ctx = get_context("spawn")
    ready = ctx.Event()
    holder = ctx.Process(target=_acquire_and_crash, args=(str(tmp_path), ready))
    holder.start()
    assert ready.wait(timeout=5)
    holder.join(timeout=5)
    assert holder.exitcode == 1
    lease = HostGpuLease(tmp_path)
    assert lease.current() is None
    with lease.hold(_row("survivor", "survivor"), wait_seconds=1.0) as held:
        assert held.model_id == "survivor"
