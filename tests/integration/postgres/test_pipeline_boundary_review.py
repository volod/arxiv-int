"""Declared disposable-store evidence for lease and file/ledger publication seams."""

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import create_engine

from arxiv_int.pipeline.control.artifacts import InjectedCrash, validate_attempt
from arxiv_int.pipeline.control.executor import ShardExecutor
from arxiv_int.pipeline.control.postgres import PostgresControlLedger
from arxiv_int.pipeline.control.settle import new_shard
from arxiv_int.pipeline.control.store import LeaseExpiredError, LeaseHeldError
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.apply import apply_revisions
from arxiv_int.stores.postgres.disposable import disposable_store
from tests.pipeline.control.test_executor import _work

pytestmark = [
    pytest.mark.heavy,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_SCHEMA_MIGRATIONS") != "1",
        reason="requires declared disposable schema run",
    ),
]


@pytest.fixture
def ledger(tmp_path):
    root = discover_project_root(Path(__file__))
    with disposable_store(root, tmp_path / "pgdata") as store:
        assert apply_revisions(root, url=store.url, run_id="boundary-review", revision="head").ok
        engine = create_engine(store.url)
        try:
            yield PostgresControlLedger(engine)
        finally:
            engine.dispose()


def test_concurrent_first_lease_and_expired_holder(ledger) -> None:
    work = _work()
    ledger.ensure_run(work.run_id, work.generation_id, work.config_fingerprint, 1)
    stage = ledger.ensure_stage(work.run_id, work.stage, work.stage_version, 1)
    holders = [
        new_shard(ledger, work, "shared-key", stage.stage_run_id, cache_hit=False, now=1)
        for _ in range(2)
    ]
    barrier = Barrier(2)

    def acquire(holder):
        barrier.wait(timeout=5)
        try:
            return ledger.acquire_lease("shared-key", holder.shard_run_id, 1, 5)
        except LeaseHeldError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(pool.map(acquire, holders))
    accepted = [lease for lease in leases if lease is not None]
    assert len(accepted) == 1
    old = accepted[0]
    replacement = ledger.acquire_lease("shared-key", holders[0].shard_run_id, 10, 5)
    assert replacement.lease_id != old.lease_id
    with pytest.raises(LeaseExpiredError):
        ledger.heartbeat_lease(old.lease_id, 11, 5)
    ledger.release_lease(replacement.lease_id, 12)


def test_file_crash_retry_force_and_sql_cache_agree(ledger, tmp_path) -> None:
    executor = ShardExecutor(ledger, tmp_path / "runs", clock=lambda: 1)
    work = _work()
    first = executor.execute(work, lambda _: {"output.json": b"complete"})
    assert first.status == "succeeded"
    before = (first.directory / "output.json").read_bytes()

    def crash(point):
        if point == "after-payload-rename":
            raise InjectedCrash(point)

    with pytest.raises(InjectedCrash):
        executor.execute(work, lambda _: {"output.json": b"partial"}, force=True, injector=crash)
    assert ledger.reusable_shard(first.reuse_key).directory == str(first.directory)
    assert (first.directory / "output.json").read_bytes() == before
    forced = executor.execute(work, lambda _: {"output.json": b"replacement"}, force=True)
    assert forced.status == "succeeded"
    assert forced.directory != first.directory
    cached = executor.execute(
        replace(work, run_id="run-2", generation_id="gen-2"),
        lambda _: pytest.fail("cache invoked worker"),
    )
    assert cached.cache_hit and cached.directory == forced.directory
    validate_attempt(cached.directory, reuse_key=cached.reuse_key, attempt=cached.attempt)
    assert ledger.get_shard(cached.shard_run_id).cache_hit
