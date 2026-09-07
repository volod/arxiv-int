"""Produce one shard attempt: lease, worker, atomic publish, activation."""

import logging
from collections.abc import Callable, Mapping
from pathlib import Path
from uuid import uuid4

from arxiv_int.pipeline.control.artifacts import (
    ArtifactPublishError,
    InjectedCrash,
    Injector,
    attempt_directory,
    publish_attempt,
    validate_attempt,
)
from arxiv_int.pipeline.control.fingerprints import reuse_key
from arxiv_int.pipeline.control.model import ShardRecord, ShardWork
from arxiv_int.pipeline.control.quality import activation_decision
from arxiv_int.pipeline.control.states import ShardStatus, can_retry, classify_failure
from arxiv_int.pipeline.control.store import ControlLedger, LeaseHeldError

_LOG = logging.getLogger(__name__)
Worker = Callable[[Path], Mapping[str, bytes]]


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
    attempt: int,
    cache_hit: bool,
    now: float,
) -> ShardRecord:
    """Insert a pending shard attempt."""
    record = ShardRecord(
        uuid4().hex,
        stage_run_id,
        work.run_id,
        work.shard_id,
        attempt,
        key,
        work.identity,
        "pending",
        None,
        cache_hit,
        now,
        now,
    )
    return ledger.add_shard(record)


def produce_shard(
    ledger: ControlLedger,
    runs_dir: Path,
    work: ShardWork,
    worker: Worker,
    key: str,
    stage_run_id: str,
    *,
    clock: Callable[[], float],
    lease_ttl: float,
    max_attempts: int,
    force: bool,
    injector: Injector | None,
) -> ProduceOutcome:
    """Run the worker into a new attempt directory and accept only complete output."""
    now = clock()
    attempt = ledger.next_attempt(key)
    shard = new_shard(ledger, work, key, stage_run_id, attempt=attempt, cache_hit=False, now=now)
    try:
        lease = ledger.acquire_lease(key, shard.shard_run_id, now, lease_ttl)
    except LeaseHeldError as error:
        fail_shard(ledger, shard, "busy", str(error.lease.holder_shard_run_id), now, max_attempts)
        current = ledger.get_shard(shard.shard_run_id)
        return ProduceOutcome(
            current.status,
            current.attempt,
            key,
            current.shard_run_id,
            None,
            "reuse lease is held",
            False,
        )
    ledger.transition_shard(shard.shard_run_id, "running", now, lease_id=lease.lease_id)
    directory = attempt_directory(runs_dir, work.run_id, work.stage, work.shard_id, attempt)
    try:
        files = worker(directory)
        ledger.add_checkpoint(shard.shard_run_id, 1, reuse_key(work.identity), clock())
        published = publish_attempt(
            directory,
            reuse_key=key,
            attempt=attempt,
            files=files,
            row_counts={name: int(work.row_counts[name]) for name in work.row_counts},
            injector=injector,
        )
        validate_attempt(directory, reuse_key=key, attempt=attempt)
        decision = activation_decision(
            work.checks,
            validations=work.validations,
            transformations=work.transformations,
            generation_id=work.generation_id,
        )
        if not decision.allowed:
            raise ArtifactPublishError(";".join(decision.blocking))
        status: ShardStatus = "quarantined" if decision.quarantined else "succeeded"
        now = clock()
        ledger.add_manifest(
            shard.shard_run_id,
            attempt,
            key,
            "manifest.json",
            "accepted",
            next(iter(published.files.values())).sha256,
            sum(item.bytes for item in published.files.values()),
            now,
        )
        for upstream in work.identity.upstream_manifest_ids:
            ledger.add_lineage(upstream, key)
        updated = ledger.transition_shard(
            shard.shard_run_id,
            status,
            now,
            directory=str(directory),
            quality_warnings=decision.warnings,
        )
        ledger.release_lease(lease.lease_id, now)
        detail = "forced new attempt" if force else "published attempt"
        if decision.warnings:
            detail = f"{detail}; warnings={','.join(decision.warnings)}"
        _LOG.info("published shard %s attempt %s status %s", key, attempt, status)
        return ProduceOutcome(
            updated.status, attempt, key, updated.shard_run_id, directory, detail, True
        )
    except ArtifactPublishError as error:
        return abort_shard(
            ledger, shard, lease.lease_id, "validation", str(error), now, max_attempts
        )
    except InjectedCrash:
        abort_shard(
            ledger, shard, lease.lease_id, "interrupted", "injected crash", clock(), max_attempts
        )
        raise
    except Exception as error:
        return abort_shard(
            ledger, shard, lease.lease_id, "interrupted", str(error), clock(), max_attempts
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
    """Append classified error evidence and fail the attempt."""
    failure_class = classify_failure(code)
    ledger.add_error(shard.shard_run_id, shard.attempt, code, failure_class, detail, now)
    ledger.transition_shard(shard.shard_run_id, "failed", now)
    retry = can_retry(failure_class, shard.attempt, max_attempts)
    _LOG.info(
        "shard %s attempt %s failed class=%s retry=%s",
        shard.reuse_key,
        shard.attempt,
        failure_class,
        retry,
    )
