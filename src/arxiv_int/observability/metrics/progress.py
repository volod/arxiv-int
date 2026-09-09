"""Time- and count-throttled progress, ETA, and stalled-versus-slow classification."""

from collections.abc import Callable

from arxiv_int.observability.logging.redact import redact_text, shard_token
from arxiv_int.observability.metrics.constants import (
    DEFAULT_PROGRESS_COUNT_INTERVAL,
    DEFAULT_PROGRESS_INTERVAL_SEC,
    DEFAULT_SLOW_ETA_SEC,
    DEFAULT_STALL_TIMEOUT_SEC,
    WorkerState,
)
from arxiv_int.observability.metrics.events import ProgressSnapshot, ResourceSample

_CLOCK = Callable[[], float]
_STAMP = Callable[[], str]


class ProgressTracker:
    """Accumulate counts and decide when a snapshot should be emitted."""

    def __init__(
        self,
        run_id: str,
        stage: str,
        shard: str,
        *,
        clock: _CLOCK,
        stamp: _STAMP,
        interval_sec: float = DEFAULT_PROGRESS_INTERVAL_SEC,
        count_interval: int = DEFAULT_PROGRESS_COUNT_INTERVAL,
        stall_timeout_sec: float = DEFAULT_STALL_TIMEOUT_SEC,
        slow_eta_sec: float = DEFAULT_SLOW_ETA_SEC,
    ) -> None:
        self._run_id = run_id
        self._stage = stage
        self._shard = shard_token(shard)
        self._clock = clock
        self._stamp = stamp
        self._interval_sec = interval_sec
        self._count_interval = max(1, count_interval)
        self._stall_timeout_sec = stall_timeout_sec
        self._slow_eta_sec = slow_eta_sec
        started = clock()
        self._started_at = started
        self._last_emit_at = started
        self._last_heartbeat_at = started
        self._last_progress_at = started
        self._last_emitted_processed = 0
        self.processed = 0
        self.remaining = 0
        self.bytes = 0
        self.errors = 0
        self.detail = ""

    def update(
        self,
        *,
        processed: int | None = None,
        remaining: int | None = None,
        bytes_delta: int = 0,
        errors_delta: int = 0,
        detail: str = "",
        heartbeat: bool = False,
    ) -> None:
        """Record work or a heartbeat without emitting."""
        now = self._clock()
        if heartbeat:
            self._last_heartbeat_at = now
        previous = self.processed
        if processed is not None:
            self.processed = processed
        if remaining is not None:
            self.remaining = remaining
        self.bytes += bytes_delta
        self.errors += errors_delta
        if detail:
            self.detail = redact_text(detail)
        if self.processed != previous or bytes_delta or errors_delta:
            self._last_progress_at = now
            self._last_heartbeat_at = now

    def should_emit(self, *, force: bool = False) -> bool:
        """Return whether time, count, or an explicit force requires a snapshot."""
        if force:
            return True
        now = self._clock()
        if now - self._last_emit_at >= self._interval_sec:
            return True
        return (self.processed - self._last_emitted_processed) >= self._count_interval

    def classify(self, now: float | None = None) -> WorkerState:
        """Distinguish a dead worker from a live shard with a large ETA."""
        current = self._clock() if now is None else now
        if current - self._last_heartbeat_at > self._stall_timeout_sec:
            return "stalled"
        eta = self.eta_seconds(current)
        if eta is not None and eta > self._slow_eta_sec:
            return "slow"
        return "running"

    def eta_seconds(self, now: float | None = None) -> float | None:
        """Return remaining/rate seconds, or None when throughput is zero."""
        rate = self.throughput_per_s(now)
        if rate <= 0.0 or self.remaining <= 0:
            return None
        return self.remaining / rate

    def throughput_per_s(self, now: float | None = None) -> float:
        """Return processed items per elapsed second."""
        current = self._clock() if now is None else now
        elapsed = max(0.0, current - self._started_at)
        if elapsed <= 0.0:
            return 0.0
        return self.processed / elapsed

    def snapshot(
        self,
        resources: ResourceSample,
        *,
        worker_state: WorkerState | None = None,
        dropped_log_records: int = 0,
        event: str = "progress",
        force_state: WorkerState | None = None,
    ) -> ProgressSnapshot:
        """Build one JSONL row and mark the throttle clock."""
        now = self._clock()
        state = force_state or worker_state or self.classify(now)
        snapshot = ProgressSnapshot(
            ts=self._stamp(),
            run_id=self._run_id,
            stage=self._stage,
            shard_token=self._shard,
            processed=self.processed,
            remaining=self.remaining,
            bytes=self.bytes,
            errors=self.errors,
            throughput_per_s=self.throughput_per_s(now),
            eta_seconds=self.eta_seconds(now),
            elapsed_seconds=max(0.0, now - self._started_at),
            worker_state=state,
            resources=resources,
            dropped_log_records=dropped_log_records,
            event=event,
            detail=self.detail,
        )
        self._last_emit_at = now
        self._last_emitted_processed = self.processed
        return snapshot
