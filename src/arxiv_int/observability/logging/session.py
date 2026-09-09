"""Per-stage observability session: queued logs, throttled progress, final manifest."""

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from types import TracebackType

from arxiv_int.inference.scheduler.lease_records import utc_now
from arxiv_int.inference.scheduler.telemetry import TelemetryEvent, TelemetrySink, telemetry_path
from arxiv_int.observability.logging import QueuedLogSession
from arxiv_int.observability.logging.format import format_progress
from arxiv_int.observability.logging.handlers import stage_log_handlers
from arxiv_int.observability.metrics import labels_for_snapshot
from arxiv_int.observability.metrics.constants import (
    DEFAULT_LOG_FORMAT,
    DEFAULT_PROGRESS_INTERVAL_SEC,
    DEFAULT_QUEUE_MAXSIZE,
    WorkerState,
)
from arxiv_int.observability.metrics.events import ProgressSnapshot
from arxiv_int.observability.metrics.progress import ProgressTracker
from arxiv_int.observability.metrics.pump import HeartbeatPump
from arxiv_int.observability.metrics.resources import ResourceProbe, ResourceSampler
from arxiv_int.observability.sinks import (
    FanoutProgressStore,
    FileProgressStore,
    MemoryProgressStore,
    ProgressStore,
)
from arxiv_int.observability.sinks.manifest import build_stage_manifest, write_stage_manifest

_CLOCK = Callable[[], float]


class StageSession:
    """Serialize logs and emit throttled progress for one stage attempt."""

    def __init__(
        self,
        run_dir: Path,
        run_id: str,
        stage: str,
        *,
        shard: str = "default",
        logger: logging.Logger | None = None,
        store: ProgressStore | None = None,
        sampler: ResourceProbe | None = None,
        clock: _CLOCK | None = None,
        stamp: Callable[[], str] | None = None,
        interval_sec: float = DEFAULT_PROGRESS_INTERVAL_SEC,
        log_format: str = DEFAULT_LOG_FORMAT,
        extra_secrets: tuple[str, ...] = (),
        queue_maxsize: int = DEFAULT_QUEUE_MAXSIZE,
        telemetry: TelemetrySink | None = None,
        background_heartbeats: bool = False,
    ) -> None:
        self._clock = clock or time.monotonic
        self._stamp = stamp or utc_now
        self._run_dir = run_dir
        self._run_id = run_id
        self._stage = stage
        self._logger = logger or logging.getLogger(f"arxiv_int.pipeline.{stage}")
        self._memory = MemoryProgressStore()
        file_store = FileProgressStore(run_dir)
        stores: list[ProgressStore] = [self._memory, file_store]
        if store is not None:
            stores.append(store)
        self._store = FanoutProgressStore(tuple(stores))
        self._sampler = sampler or ResourceSampler(disk_root=run_dir)
        self._tracker = ProgressTracker(
            run_id,
            stage,
            shard,
            clock=self._clock,
            stamp=self._stamp,
            interval_sec=interval_sec,
        )
        self._telemetry = telemetry or TelemetrySink(telemetry_path(run_dir.parent, run_id))
        logs = run_dir / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        handlers = stage_log_handlers(logs, run_id, stage, log_format)
        self._session = QueuedLogSession(
            self._logger,
            handlers if handlers else (logging.NullHandler(),),
            maxsize=queue_maxsize,
            extra_secrets=extra_secrets,
        )
        self._completed = False
        self._started = False
        self._lock = threading.RLock()
        self._pump: HeartbeatPump | None = None
        if background_heartbeats:
            self._pump = HeartbeatPump(self._background_tick, interval_sec)

    @property
    def snapshots(self) -> tuple[ProgressSnapshot, ...]:
        """Return in-memory snapshots recorded in this session."""
        return tuple(self._memory.rows)

    @property
    def dropped(self) -> int:
        return self._session.dropped

    def start(self) -> None:
        if self._started:
            return
        self._session.start()
        self._started = True
        self.emit(event="stage-start", force=True)
        if self._pump is not None:
            self._pump.start()

    def stop(self) -> None:
        if not self._started:
            return
        if self._pump is not None:
            self._pump.stop()
        self._session.stop()
        self._started = False

    def heartbeat(self, *, force: bool = False) -> None:
        """Mark the worker alive without counting items."""
        with self._lock:
            self._tracker.update(heartbeat=True)
            self.emit(event="heartbeat", force=force)

    def _background_tick(self) -> None:
        with self._lock:
            if not self._started:
                return
            self._tracker.update(heartbeat=True)
            self.emit(event="heartbeat", force=True)

    def progress(
        self,
        *,
        processed: int | None = None,
        remaining: int | None = None,
        bytes_delta: int = 0,
        errors_delta: int = 0,
        detail: str = "",
        force: bool = False,
    ) -> ProgressSnapshot | None:
        """Update counts and maybe emit a throttled snapshot."""
        with self._lock:
            self._tracker.update(
                processed=processed,
                remaining=remaining,
                bytes_delta=bytes_delta,
                errors_delta=errors_delta,
                detail=detail,
            )
            return self.emit(force=force)

    def emit(
        self,
        *,
        event: str = "progress",
        force: bool = False,
        worker_state: WorkerState | None = None,
    ) -> ProgressSnapshot | None:
        """Emit when throttles fire, or always when ``force`` is set."""
        with self._lock:
            return self._emit_locked(event=event, force=force, worker_state=worker_state)

    def _emit_locked(
        self,
        *,
        event: str,
        force: bool,
        worker_state: WorkerState | None,
    ) -> ProgressSnapshot | None:
        if not force and not self._tracker.should_emit(force=force):
            return None
        snapshot = self._tracker.snapshot(
            self._sampler.sample(),
            dropped_log_records=self._session.dropped,
            event=event,
            force_state=worker_state,
        )
        labels_for_snapshot(
            snapshot.stage, snapshot.event, snapshot.worker_state, snapshot.resources.device
        )
        self._store.record(snapshot)
        self._logger.info("%s", format_progress(snapshot))
        self._record_telemetry(snapshot)
        return snapshot

    def complete(self, *, outcome: str, next_action: str, failed: bool = False) -> Path:
        """Force a terminal snapshot and write the stage observability manifest."""
        with self._lock:
            state: WorkerState = "failed" if failed else "completed"
            snapshot = self._emit_locked(event="stage-complete", force=True, worker_state=state)
        assert snapshot is not None
        self._completed = True
        payload = build_stage_manifest(snapshot, outcome=outcome, next_action=next_action)
        return write_stage_manifest(self._run_dir, payload)

    def _record_telemetry(self, snapshot: ProgressSnapshot) -> None:
        resources = snapshot.resources
        self._telemetry.record(
            TelemetryEvent(
                event="pipeline.resource",
                run_id=snapshot.run_id,
                model_id="",
                backend="pipeline",
                device=resources.device,
                status=snapshot.worker_state,
                detail=snapshot.stage,
                free_gpu_gib=resources.gpu_free_gib,
                used_gpu_gib=resources.gpu_used_gib,
                total_gpu_gib=resources.gpu_total_gib,
                ram_available_gib=resources.ram_available_gib,
                power_watts=resources.gpu_power_watts,
                gpu_util_pct=resources.gpu_util_pct,
            )
        )

    def __enter__(self) -> "StageSession":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        failed = exc_type is not None
        if self._started and not self._completed:
            next_action = "inspect logs and resume" if failed else "continue downstream stages"
            self.complete(
                outcome="failed" if failed else "produced",
                next_action=next_action,
                failed=failed,
            )
        self.stop()
