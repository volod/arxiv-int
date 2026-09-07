"""Walk a stage plan in-process, halt on failure, and persist run status."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from arxiv_int.pipeline.cancel import CancelToken
from arxiv_int.pipeline.context import RunContext
from arxiv_int.pipeline.control.executor import ShardExecutor
from arxiv_int.pipeline.control.lineage import LineageEdge, stale_closure
from arxiv_int.pipeline.control.memory import InMemoryLedger
from arxiv_int.pipeline.errors import (
    InterruptedPipelineError,
    PipelineError,
    StaleUpstreamError,
    UnregisteredStageError,
)
from arxiv_int.pipeline.execute import execute_stage, execution_to_entry, try_reuse
from arxiv_int.pipeline.graph import StagePlan
from arxiv_int.pipeline.observe import open_stage_session
from arxiv_int.pipeline.persist import RunStatus, StageExecution, load_status, run_dir, save_status
from arxiv_int.pipeline.quality_bound import FixtureQuality, QualityBoundary
from arxiv_int.pipeline.registry import StageRegistry
from arxiv_int.pipeline.reuse_index import (
    ReuseEntry,
    load_lineage,
    load_reuse_index,
    save_reuse_index,
)

_CLOCK = Callable[[], float]
_GUARD = Callable[[str], None]


class Orchestrator:
    """Sequential DAG runner over the shard executor; not a second scheduler."""

    def __init__(
        self,
        registry: StageRegistry,
        runs_dir: Path,
        *,
        executor: ShardExecutor | None = None,
        quality: QualityBoundary | None = None,
        clock: _CLOCK | None = None,
        cancel: CancelToken | None = None,
        space_guard: _GUARD | None = None,
    ) -> None:
        ticks = iter(float(index) for index in range(1, 10_000))
        self._registry = registry
        self._runs_dir = runs_dir
        self._clock = clock or (lambda: next(ticks))
        self._ledger = InMemoryLedger()
        self._executor = executor or ShardExecutor(self._ledger, runs_dir, clock=self._clock)
        self._quality = quality or FixtureQuality()
        self._cancel = cancel or CancelToken()
        self._space_guard = space_guard
        self._index: dict[str, ReuseEntry] = load_reuse_index(runs_dir)
        self._lineage: list[tuple[str, str]] = list(load_lineage(runs_dir))

    def execute_plan(
        self,
        context: RunContext,
        plan: StagePlan,
        *,
        force: bool = False,
    ) -> RunStatus:
        """Execute ``plan.execute`` in order; stop on failure or cancellation."""
        missing = tuple(name for name in plan.execute if self._registry.get(name).runner is None)
        if missing:
            raise UnregisteredStageError(missing)
        self._require_upstream(plan.assumed_upstream)
        executions: list[StageExecution] = []
        run_lineage: list[tuple[str, str]] = []
        keys = self._upstream_keys(plan.assumed_upstream)
        halted = False
        halt_reason = ""
        for name in plan.execute:
            execution, halt_reason = self._execute_one(context, name, keys, force)
            if execution is None or halt_reason:
                halted = True
                break
            executions.append(execution)
            keys[name] = execution.reuse_key
            spec = self._registry.get(name)
            self._record_lineage(spec.depends_on, keys, execution.reuse_key, run_lineage)
            entry = execution_to_entry(
                context, execution, context.parameters.get("document_id", "default")
            )
            if entry is not None:
                self._index[entry.reuse_key] = entry
            halt_reason = _stage_halt(execution)
            if halt_reason:
                halted = True
                break
        current = RunStatus(
            context.run_id,
            context.generation_id,
            halted,
            halt_reason,
            tuple(executions),
            tuple(run_lineage),
            plan.not_selected,
        )
        save_status(self._runs_dir, _merge_status(self._runs_dir, context.run_id, current))
        save_reuse_index(self._runs_dir, self._index, tuple(self._lineage))
        return current

    def _execute_one(
        self,
        context: RunContext,
        name: str,
        keys: dict[str, str],
        force: bool,
    ) -> tuple[StageExecution | None, str]:
        try:
            self._cancel.raise_if_cancelled()
            if self._space_guard is not None:
                self._space_guard(name)
            spec = self._registry.get(name)
            upstream = tuple(keys[item] for item in spec.depends_on if item in keys)
            with open_stage_session(context, name) as session:
                session.heartbeat()
                execution = execute_stage(
                    self._registry,
                    self._executor,
                    self._quality,
                    context,
                    name,
                    upstream,
                    self._index,
                    force=force,
                )
                session.progress(processed=1, remaining=0, bytes_delta=execution.bytes, force=True)
        except (InterruptedPipelineError, KeyboardInterrupt):
            return None, "interrupted"
        except PipelineError as error:
            return None, str(error)
        return execution, ""

    def invalidate(self, stage: str, *, document_id: str | None = None) -> tuple[str, ...]:
        """Mark the named stage's reuse keys and their consumer closure stale."""
        roots = [
            entry.reuse_key
            for entry in self._index.values()
            if entry.stage == stage
            and not entry.stale
            and (document_id is None or entry.shard_id == document_id)
        ]
        edges = tuple(LineageEdge(producer, consumer) for producer, consumer in self._lineage)
        marked = stale_closure(roots, edges)
        self._index = {
            key: replace(entry, stale=True, status="stale") if key in marked else entry
            for key, entry in self._index.items()
        }
        self._ledger.mark_stale(marked, self._clock())
        save_reuse_index(self._runs_dir, self._index, tuple(self._lineage))
        return tuple(sorted(marked))

    def _record_lineage(
        self,
        depends_on: tuple[str, ...],
        keys: dict[str, str],
        consumer: str,
        run_lineage: list[tuple[str, str]],
    ) -> None:
        for producer in depends_on:
            if producer not in keys:
                continue
            edge = (keys[producer], consumer)
            run_lineage.append(edge)
            if edge not in self._lineage:
                self._lineage.append(edge)

    def _require_upstream(self, names: tuple[str, ...]) -> None:
        for name in names:
            matches = [
                entry
                for entry in self._index.values()
                if entry.stage == name
                and not entry.stale
                and entry.status in {"succeeded", "quarantined"}
            ]
            if not matches or try_reuse(matches[-1], force=False) is None:
                raise StaleUpstreamError(f"stale or missing upstream stage {name}")

    def _upstream_keys(self, names: tuple[str, ...]) -> dict[str, str]:
        keys: dict[str, str] = {}
        for name in names:
            for entry in self._index.values():
                if entry.stage == name and not entry.stale:
                    keys[name] = entry.reuse_key
        return keys


def _stage_halt(execution: StageExecution) -> str:
    if execution.status not in {"succeeded", "quarantined"}:
        return execution.detail
    if execution.outcome == "partial":
        return execution.detail or "partial stage output"
    return ""


def _merge_status(runs_dir: Path, run_id: str, current: RunStatus) -> RunStatus:
    """Keep prior stage rows when an atomic or resume walk covers a subset."""
    path = run_dir(runs_dir, run_id) / "status.json"
    if not path.is_file():
        return current
    prior = load_status(runs_dir, run_id)
    by_stage = {item.stage: item for item in prior.executions}
    order = [item.stage for item in prior.executions]
    for item in current.executions:
        by_stage[item.stage] = item
        if item.stage not in order:
            order.append(item.stage)
    lineage = tuple(dict.fromkeys((*prior.lineage, *current.lineage)))
    skipped = tuple(dict.fromkeys((*prior.not_selected, *current.not_selected)))
    return RunStatus(
        current.run_id,
        current.generation_id,
        current.halted,
        current.halt_reason,
        tuple(by_stage[name] for name in order),
        lineage,
        skipped,
    )
