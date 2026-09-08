"""Execute one shard with cache validation, leases, and atomic publication."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.pipeline.control.artifacts import (
    ArtifactPublishError,
    Injector,
    validate_attempt,
)
from arxiv_int.pipeline.control.fingerprints import reuse_key
from arxiv_int.pipeline.control.lineage import keys_matching_owned_change, stale_closure
from arxiv_int.pipeline.control.memory import InMemoryLedger
from arxiv_int.pipeline.control.model import ShardWork
from arxiv_int.pipeline.control.produce import Worker, produce_shard
from arxiv_int.pipeline.control.quality import activation_decision
from arxiv_int.pipeline.control.settle import new_shard
from arxiv_int.pipeline.control.states import DEFAULT_MAX_TRANSIENT_ATTEMPTS
from arxiv_int.pipeline.control.store import ControlLedger

_LOG = logging.getLogger(__name__)
DEFAULT_LEASE_TTL_SECONDS = 300.0


@dataclass(frozen=True, slots=True)
class ShardDecision:
    """Outcome of scheduling or reusing one shard."""

    status: str
    cache_hit: bool
    attempt: int
    reuse_key: str
    shard_run_id: str
    directory: Path | None
    detail: str
    worker_invoked: bool


class ShardExecutor:
    """Generic control mechanics; the worker remains stage-owned."""

    def __init__(
        self,
        ledger: ControlLedger,
        runs_dir: Path,
        *,
        clock: Callable[[], float],
        lease_ttl_seconds: float = DEFAULT_LEASE_TTL_SECONDS,
        max_transient_attempts: int = DEFAULT_MAX_TRANSIENT_ATTEMPTS,
    ) -> None:
        self._ledger = ledger
        self._runs_dir = runs_dir
        self._clock = clock
        self._lease_ttl = lease_ttl_seconds
        self._max_attempts = max_transient_attempts

    def execute(
        self,
        work: ShardWork,
        worker: Worker,
        *,
        force: bool = False,
        injector: Injector | None = None,
    ) -> ShardDecision:
        """Reuse a valid manifest or run the worker into a new attempt directory."""
        key = reuse_key(work.identity)
        now = self._clock()
        self._ledger.ensure_run(work.run_id, work.generation_id, work.config_fingerprint, now)
        stage = self._ledger.ensure_stage(work.run_id, work.stage, work.stage_version, now)
        self._ledger.transition_run(work.run_id, "running", now)
        self._ledger.transition_stage(stage.stage_run_id, "running", now)
        eligible = activation_decision(
            work.checks,
            validations=work.validations,
            transformations=work.transformations,
            generation_id=work.generation_id,
        ).allowed
        if not force and eligible:
            reused = self._try_reuse(work, key)
            if reused is not None:
                return reused
        produced = produce_shard(
            self._ledger,
            self._runs_dir,
            work,
            worker,
            key,
            stage.stage_run_id,
            clock=self._clock,
            lease_ttl=self._lease_ttl,
            max_attempts=self._max_attempts,
            force=force,
            injector=injector,
        )
        return ShardDecision(
            produced.status,
            False,
            produced.attempt,
            produced.reuse_key,
            produced.shard_run_id,
            produced.directory,
            produced.detail,
            produced.worker_invoked,
        )

    def invalidate_owned(self, field: str, previous: str) -> tuple[str, ...]:
        """Mark shards that used ``previous`` plus their consumer closure stale."""
        identities = {item.reuse_key: item.identity for item in self._ledger.shards()}
        roots = keys_matching_owned_change(identities, field, previous)
        closure = stale_closure(roots, self._ledger.lineage())
        marked = self._ledger.mark_stale(closure, self._clock())
        _LOG.info("invalidated %s reuse keys for owned field %s", len(marked), field)
        return marked

    def _try_reuse(self, work: ShardWork, key: str) -> ShardDecision | None:
        existing = self._ledger.reusable_shard(key)
        if existing is None or existing.directory is None:
            return None
        directory = Path(existing.directory)
        try:
            validate_attempt(directory, reuse_key=key, attempt=existing.attempt)
        except ArtifactPublishError as error:
            _LOG.info("reuse key %s failed cache validation: %s", key, error)
            return None
        now = self._clock()
        stage = self._ledger.ensure_stage(work.run_id, work.stage, work.stage_version, now)
        shard = new_shard(
            self._ledger,
            work,
            key,
            stage.stage_run_id,
            cache_hit=True,
            now=now,
        )
        self._ledger.transition_shard(shard.shard_run_id, "running", now)
        published = self._ledger.transition_shard(
            shard.shard_run_id,
            existing.status,
            now,
            cache_hit=True,
            directory=existing.directory,
            quality_warnings=existing.quality_warnings,
        )
        _LOG.info("cache hit for reuse key %s attempt %s", key, existing.attempt)
        return ShardDecision(
            published.status,
            True,
            existing.attempt,
            key,
            published.shard_run_id,
            directory,
            "cache hit after manifest validation",
            False,
        )


def in_memory_executor(runs_dir: Path, clock: Callable[[], float]) -> ShardExecutor:
    """Return a fixture executor bound to an in-memory ledger."""
    return ShardExecutor(InMemoryLedger(), runs_dir, clock=clock)
