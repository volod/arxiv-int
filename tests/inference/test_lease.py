"""Host-wide GPU lease contention, cancellation, and ledger persistence."""

from pathlib import Path
from threading import Event, Thread
from time import sleep

import pytest

from arxiv_int.inference.errors import LeaseCancelledError, LeaseConflictError
from arxiv_int.inference.lease import HostGpuLease, ResourceLeaseRecord, lease_record


def _row(run_id: str = "run", model_id: str = "fixture") -> ResourceLeaseRecord:
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


def test_second_acquirer_waits_then_succeeds(tmp_path: Path) -> None:
    lease = HostGpuLease(tmp_path)
    released = Event()
    holding = Event()
    order: list[str] = []

    def holder() -> None:
        with lease.hold(_row("a"), wait_seconds=1.0):
            holding.set()
            released.wait(timeout=2.0)
            order.append("first")

    thread = Thread(target=holder)
    thread.start()
    assert holding.wait(timeout=2.0)
    waiter_done = Event()

    def waiter() -> None:
        with lease.hold(_row("b"), wait_seconds=2.0):
            order.append("second")
        waiter_done.set()

    waiting = Thread(target=waiter)
    waiting.start()
    sleep(0.1)
    released.set()
    thread.join(timeout=2.0)
    waiting.join(timeout=2.0)
    assert order == ["first", "second"]
    ledger = (tmp_path / "ctl.resource_lease.jsonl").read_text(encoding="utf-8")
    assert ledger.count('"status": "acquired"') == 2
    assert ledger.count('"status": "released"') == 2


def test_cancel_during_wait_releases_without_holding(tmp_path: Path) -> None:
    lease = HostGpuLease(tmp_path)
    holding = Event()
    cancel = Event()

    def holder() -> None:
        with lease.hold(_row("holder"), wait_seconds=1.0):
            holding.set()
            sleep(0.4)

    thread = Thread(target=holder)
    thread.start()
    assert holding.wait(timeout=2.0)
    cancel.set()
    with pytest.raises(LeaseCancelledError):
        lease.acquire(_row("waiter"), cancel=cancel, wait_seconds=2.0)
    thread.join(timeout=2.0)
    with lease.hold(_row(model_id="after"), wait_seconds=1.0):
        current = lease.current()
        assert current is not None
        assert current.model_id == "after"


def test_zero_wait_conflict_is_explicit(tmp_path: Path) -> None:
    lease = HostGpuLease(tmp_path)
    holding = Event()
    finished = Event()

    def holder() -> None:
        with lease.hold(_row(), wait_seconds=1.0):
            holding.set()
            finished.wait(timeout=2.0)

    thread = Thread(target=holder)
    thread.start()
    assert holding.wait(timeout=2.0)
    with pytest.raises(LeaseConflictError, match="held"):
        lease.acquire(_row("other"), wait_seconds=0.0)
    finished.set()
    thread.join(timeout=2.0)
