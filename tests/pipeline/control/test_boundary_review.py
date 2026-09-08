"""Lease expiration and cancellation at the worker/publication seam."""

from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.pipeline.control.executor import ShardExecutor
from arxiv_int.pipeline.control.memory import InMemoryLedger
from tests.pipeline.control.test_executor import _work


def test_expired_worker_cannot_renew_and_publish(tmp_path: Path) -> None:
    ledger = InMemoryLedger()
    now = [1.0]
    executor = ShardExecutor(ledger, tmp_path, clock=lambda: now[0], lease_ttl_seconds=5)

    def worker(_directory):
        now[0] = 10.0
        return {"output.json": b"late"}

    result = executor.execute(_work(), worker)
    assert result.status == "failed"
    assert ledger.reusable_shard(result.reuse_key) is None
    assert not list(tmp_path.rglob("manifest.json"))


def test_keyboard_interrupt_releases_lease_and_records_failure(tmp_path: Path) -> None:
    ledger = InMemoryLedger()
    executor = ShardExecutor(ledger, tmp_path, clock=lambda: 1.0)

    def worker(_directory):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        executor.execute(_work(), worker)
    assert all(lease.status != "acquired" for lease in ledger._leases.values())
    assert ledger.shards()[0].status == "failed"
    resumed = executor.execute(_work(), lambda _directory: {"output.json": b"resumed"})
    assert resumed.status == "succeeded"


def test_cache_cannot_bypass_missing_global_checks(tmp_path: Path) -> None:
    ledger = InMemoryLedger()
    executor = ShardExecutor(ledger, tmp_path, clock=lambda: 1.0)
    work = _work()
    assert executor.execute(work, lambda _: {"output.json": b"ok"}).status == "succeeded"
    result = executor.execute(replace(work, checks=()), lambda _: {"output.json": b"bad"})
    assert result.status == "failed"
    assert not result.cache_hit
    assert not result.worker_invoked
