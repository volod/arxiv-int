"""Accept, abort, or fail one shard attempt without illegal status transitions."""

import logging
from pathlib import Path
from uuid import uuid4

from arxiv_int.pipeline.control.artifacts import ArtifactManifest
from arxiv_int.pipeline.control.model import ShardRecord, ShardWork
from arxiv_int.pipeline.control.states import (
    IllegalTransitionError,
    ShardStatus,
    can_retry,
    classify_failure,
)
from arxiv_int.pipeline.control.store import ControlLedger

_LOG = logging.getLogger(__name__)
_TERMINAL = frozenset({"stale", "pruned", "superseded", "failed"})


class ProduceOutcome:
    """Narrow result returned to the executor."""

    def __init__(
        self,
        status: str,
        attempt: int,
        reuse_key_value: str,
        shard_run_id: str,
        directory: Path | None,
        detail: str,
        worker_invoked: bool,
    ) -> None:
        self.status = status
        self.attempt = attempt
        self.reuse_key = reuse_key_value
        self.shard_run_id = shard_run_id
        self.directory = directory
        self.detail = detail
        self.worker_invoked = worker_invoked


def new_shard(
    ledger: ControlLedger,
    work: ShardWork,
    key: str,
    stage_run_id: str,
    *,
    cache_hit: bool,
    now: float,
) -> ShardRecord:
    """Insert a pending shard attempt, assigning the next attempt number."""
    record = ShardRecord(
        uuid4().hex,
        stage_run_id,
        work.run_id,
        work.shard_id,
        1,
        key,
        work.identity,
        "pending",
        None,
        cache_hit,
        now,
        now,
    )
    return ledger.add_shard(record)


def blocked_outcome(
    ledger: ControlLedger, shard: ShardRecord, key: str, detail: str
) -> ProduceOutcome:
    """Return a failed or busy decision that did not invoke the worker."""
    current = ledger.get_shard(shard.shard_run_id)
    return ProduceOutcome(
        current.status, current.attempt, key, current.shard_run_id, None, detail, False
    )


def accept_shard(
    ledger: ControlLedger,
    shard: ShardRecord,
    lease_id: str,
    work: ShardWork,
    key: str,
    directory: Path,
    published: ArtifactManifest,
    quarantined: bool,
    warnings: tuple[str, ...],
    now: float,
    force: bool,
) -> ProduceOutcome:
    """Record lineage and accept the attempt unless invalidation won the race."""
    current = ledger.get_shard(shard.shard_run_id)
    if current.status in {"stale", "pruned", "superseded"}:
        ledger.release_lease(lease_id, now)
        return ProduceOutcome(
            current.status, shard.attempt, key, shard.shard_run_id, directory, "invalidated", True
        )
    status: ShardStatus = "quarantined" if quarantined else "succeeded"
    ledger.add_manifest(
        shard.shard_run_id,
        shard.attempt,
        key,
        "manifest.json",
        "accepted",
        next(iter(published.files.values())).sha256,
        sum(item.bytes for item in published.files.values()),
        now,
    )
    for upstream in work.identity.upstream_manifest_ids:
        ledger.add_lineage(upstream, key)
    try:
        updated = ledger.transition_shard(
            shard.shard_run_id,
            status,
            now,
            directory=str(directory),
            quality_warnings=warnings,
        )
    except IllegalTransitionError:
        current = ledger.get_shard(shard.shard_run_id)
        ledger.release_lease(lease_id, now)
        return ProduceOutcome(
            current.status, shard.attempt, key, shard.shard_run_id, directory, "invalidated", True
        )
    ledger.release_lease(lease_id, now)
    detail = "forced new attempt" if force else "published attempt"
    if warnings:
        detail = f"{detail}; warnings={','.join(warnings)}"
    _LOG.info("published shard %s attempt %s status %s", key, shard.attempt, status)
    return ProduceOutcome(
        updated.status, shard.attempt, key, updated.shard_run_id, directory, detail, True
    )


def abort_shard(
    ledger: ControlLedger,
    shard: ShardRecord,
    lease_id: str,
    code: str,
    detail: str,
    now: float,
    max_attempts: int,
) -> ProduceOutcome:
    """Release the lease, record the error, and mark the attempt failed."""
    try:
        ledger.release_lease(lease_id, now, status="failed")
    except Exception:
        _LOG.info("lease %s already released during abort", lease_id)
    fail_shard(ledger, shard, code, detail, now, max_attempts)
    current = ledger.get_shard(shard.shard_run_id)
    directory = None if current.directory is None else Path(current.directory)
    return ProduceOutcome(
        current.status,
        current.attempt,
        current.reuse_key,
        current.shard_run_id,
        directory,
        detail,
        True,
    )


def fail_shard(
    ledger: ControlLedger,
    shard: ShardRecord,
    code: str,
    detail: str,
    now: float,
    max_attempts: int,
) -> None:
    """Append classified error evidence and fail the attempt when still mutable."""
    failure_class = classify_failure(code)
    ledger.add_error(shard.shard_run_id, shard.attempt, code, failure_class, detail, now)
    current = ledger.get_shard(shard.shard_run_id)
    if current.status not in _TERMINAL:
        ledger.transition_shard(shard.shard_run_id, "failed", now)
    retry = can_retry(failure_class, shard.attempt, max_attempts)
    _LOG.info(
        "shard %s attempt %s failed class=%s retry=%s",
        shard.reuse_key,
        shard.attempt,
        failure_class,
        retry,
    )
