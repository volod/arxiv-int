"""Cache hit, force retry, stale-lease recovery, and invalidation through the executor."""

from pathlib import Path

import pytest

from arxiv_int.pipeline.control.artifacts import InjectedCrash
from arxiv_int.pipeline.control.executor import ShardExecutor
from arxiv_int.pipeline.control.fingerprints import ReuseIdentity, reuse_key
from arxiv_int.pipeline.control.memory import InMemoryLedger
from arxiv_int.pipeline.control.model import ShardWork
from arxiv_int.pipeline.control.store import LeaseHeldError
from tests.pipeline.control.identities import identity, owned_fingerprints, passing_checks


def _work(ident: ReuseIdentity | None = None, **owned: str) -> ShardWork:
    resolved = ident or identity(**owned)
    return ShardWork(
        run_id="run-1",
        generation_id="gen-1",
        stage=resolved.stage,
        stage_version=resolved.stage_version,
        shard_id=resolved.shard_id,
        config_fingerprint="cfg-1",
        identity=resolved,
        checks=passing_checks(),
        row_counts={"output.json": 1},
    )


def _executor(tmp_path: Path, ledger: InMemoryLedger | None = None) -> ShardExecutor:
    ticks = iter(float(index) for index in range(1, 1000))
    return ShardExecutor(ledger or InMemoryLedger(), tmp_path / "runs", clock=lambda: next(ticks))


def test_unchanged_rerun_validates_and_skips_the_worker(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    work = _work()
    calls = {"n": 0}

    def worker(_directory: Path) -> dict[str, bytes]:
        calls["n"] += 1
        return {"output.json": b"ok"}

    first = executor.execute(work, worker)
    second = executor.execute(work, worker)
    assert first.worker_invoked and first.status == "succeeded"
    assert second.cache_hit and not second.worker_invoked
    assert second.attempt == first.attempt
    assert calls["n"] == 1
    assert second.directory == first.directory


def test_force_retry_writes_a_new_attempt_without_overwriting(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    work = _work()
    first = executor.execute(work, lambda _d: {"output.json": b"one"})
    forced = executor.execute(work, lambda _d: {"output.json": b"two"}, force=True)
    assert first.directory is not None and forced.directory is not None
    assert first.directory != forced.directory
    assert forced.attempt == first.attempt + 1
    assert not forced.cache_hit
    assert (first.directory / "output.json").read_bytes() == b"one"
    assert (forced.directory / "output.json").read_bytes() == b"two"


def test_crash_does_not_create_a_reusable_manifest(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    work = _work()

    def crash(point: str) -> None:
        if point == "after-payload-rename":
            raise InjectedCrash(point)

    with pytest.raises(InjectedCrash):
        executor.execute(work, lambda _d: {"output.json": b"partial"}, injector=crash)
    reused = executor.execute(work, lambda _d: {"output.json": b"complete"})
    assert reused.worker_invoked
    assert reused.status == "succeeded"
    assert reused.directory is not None
    assert (reused.directory / "output.json").read_bytes() == b"complete"


def test_owned_fingerprint_change_marks_the_closure_stale(tmp_path: Path) -> None:
    ledger = InMemoryLedger()
    executor = _executor(tmp_path, ledger)
    producer = executor.execute(_work(), lambda _d: {"output.json": b"p"})
    child = ReuseIdentity(
        stage="embed",
        stage_version="1",
        shard_id="child",
        parameters={"bucket": "0"},
        input_hashes=("hash-b",),
        upstream_manifest_ids=(producer.reuse_key,),
        owned=owned_fingerprints(code_fingerprint="embed-code-v1"),
    )
    executor.execute(_work(child), lambda _d: {"output.json": b"c"})
    unrelated = identity(shard_id="other", code_fingerprint="code_fingerprint-other")
    executor.execute(_work(unrelated), lambda _d: {"output.json": b"o"})
    marked = executor.invalidate_owned("code_fingerprint", "code_fingerprint-v1")
    assert producer.reuse_key in marked
    assert reuse_key(child) in marked
    assert reuse_key(unrelated) not in marked
    statuses = {item.reuse_key: item.status for item in ledger.shards() if not item.cache_hit}
    assert statuses[producer.reuse_key] == "stale"
    assert statuses[reuse_key(child)] == "stale"
    assert statuses[reuse_key(unrelated)] == "succeeded"


def test_expired_lease_is_recovered(tmp_path: Path) -> None:
    ledger = InMemoryLedger()
    executor = ShardExecutor(ledger, tmp_path / "runs", clock=lambda: 100.0, lease_ttl_seconds=10.0)
    work = _work()
    first = executor.execute(work, lambda _d: {"output.json": b"ok"})
    holder = next(iter(ledger._leases.values()))
    ledger._leases[holder.lease_id] = holder.__class__(
        holder.lease_id,
        holder.reuse_key,
        "dead-worker",
        "acquired",
        1.0,
        1.0,
        50.0,
    )
    with pytest.raises(LeaseHeldError):
        ledger.acquire_lease(first.reuse_key, "other", now=40.0, ttl_seconds=10.0)
    recovered = ledger.acquire_lease(first.reuse_key, "other", now=60.0, ttl_seconds=10.0)
    assert recovered.holder_shard_run_id == "other"
    assert recovered.status == "acquired"
