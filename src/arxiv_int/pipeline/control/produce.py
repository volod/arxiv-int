"""Produce one shard attempt: lease, worker, atomic publish, activation."""

from collections.abc import Callable, Mapping
from pathlib import Path

from arxiv_int.pipeline.control.artifacts import (
    ArtifactPublishError,
    InjectedCrash,
    Injector,
    attempt_directory,
    publish_attempt,
    validate_attempt,
)
from arxiv_int.pipeline.control.fingerprints import reuse_key
from arxiv_int.pipeline.control.model import ShardWork
from arxiv_int.pipeline.control.quality import activation_decision
from arxiv_int.pipeline.control.settle import (
    ProduceOutcome,
    abort_shard,
    accept_shard,
    blocked_outcome,
    fail_shard,
    new_shard,
)
from arxiv_int.pipeline.control.store import ControlLedger, LeaseExpiredError, LeaseHeldError

Worker = Callable[[Path], Mapping[str, bytes]]


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
    decision = activation_decision(
        work.checks,
        validations=work.validations,
        transformations=work.transformations,
        generation_id=work.generation_id,
    )
    shard = new_shard(ledger, work, key, stage_run_id, cache_hit=False, now=now, runs_dir=runs_dir)
    if not decision.allowed:
        fail_shard(ledger, shard, "quality", ";".join(decision.blocking), now, max_attempts)
        return blocked_outcome(ledger, shard, key, ";".join(decision.blocking))
    try:
        lease = ledger.acquire_lease(key, shard.shard_run_id, now, lease_ttl)
    except LeaseHeldError as error:
        fail_shard(ledger, shard, "busy", str(error.lease.holder_shard_run_id), now, max_attempts)
        return blocked_outcome(ledger, shard, key, "reuse lease is held")
    ledger.transition_shard(shard.shard_run_id, "running", now, lease_id=lease.lease_id)
    directory = attempt_directory(runs_dir, work.run_id, work.stage, work.shard_id, shard.attempt)
    try:
        files = worker(directory)
        ledger.heartbeat_lease(lease.lease_id, clock(), lease_ttl)
        ledger.add_checkpoint(shard.shard_run_id, 1, reuse_key(work.identity), clock())
        published = publish_attempt(
            directory,
            reuse_key=key,
            attempt=shard.attempt,
            files=files,
            row_counts={name: int(work.row_counts[name]) for name in work.row_counts},
            injector=injector,
        )
        validate_attempt(directory, reuse_key=key, attempt=shard.attempt)
        ledger.heartbeat_lease(lease.lease_id, clock(), lease_ttl)
        return accept_shard(
            ledger,
            shard,
            lease.lease_id,
            work,
            key,
            directory,
            published,
            decision.quarantined,
            decision.warnings,
            clock(),
            force,
        )
    except LeaseExpiredError as error:
        return abort_shard(
            ledger, shard, lease.lease_id, "lease-expired", str(error), clock(), max_attempts
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
    except (KeyboardInterrupt, SystemExit):
        abort_shard(
            ledger,
            shard,
            lease.lease_id,
            "interrupted",
            "worker interrupted",
            clock(),
            max_attempts,
        )
        raise
    except Exception as error:
        return abort_shard(
            ledger, shard, lease.lease_id, "interrupted", str(error), clock(), max_attempts
        )
