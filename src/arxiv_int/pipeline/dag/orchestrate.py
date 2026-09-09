"""Walk a stage plan in-process, halt on failure, and persist run status."""

from collections.abc import Callable
from pathlib import Path

from arxiv_int.pipeline.control.executor import ShardExecutor
from arxiv_int.pipeline.control.memory import InMemoryLedger
from arxiv_int.pipeline.dag.cancel import CancelToken, cancellation_scope
from arxiv_int.pipeline.dag.execute import execute_stage, execution_to_entry
from arxiv_int.pipeline.dag.graph import StagePlan
from arxiv_int.pipeline.dag.invalidate import apply_invalidation
from arxiv_int.pipeline.dag.registry import StageRegistry
from arxiv_int.pipeline.dag.upstream import resolve_upstream
from arxiv_int.pipeline.quality.bound import FixtureQuality, ProductionQuality, QualityBoundary
from arxiv_int.pipeline.reconcile.persist import write_manifest
from arxiv_int.pipeline.reconcile.scan import bind_shard, scan_silos, source_shard_ids
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.errors import (
    InterruptedPipelineError,
    PipelineError,
    UnregisteredStageError,
)
from arxiv_int.pipeline.run.locking import pipeline_lock
from arxiv_int.pipeline.run.observe import open_stage_session
from arxiv_int.pipeline.run.persist import RunStatus, StageExecution, save_status
from arxiv_int.pipeline.run.reuse_index import (
    ReuseEntry,
    load_lineage,
    load_reuse_index,
    load_superseded,
    save_reuse_index,
    supersede_previous,
)
from arxiv_int.pipeline.run.status import append_lineage, merge_status, stage_halt, walk_shards

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
        self._quality = quality
        self._cancel = cancel or CancelToken()
        self._space_guard = space_guard
        self._index: dict[str, ReuseEntry] = load_reuse_index(runs_dir)
        self._lineage: list[tuple[str, str]] = list(load_lineage(runs_dir))
        self._superseded: list[ReuseEntry] = list(load_superseded(runs_dir))

    def execute_plan(
        self,
        context: RunContext,
        plan: StagePlan,
        *,
        force: bool = False,
    ) -> RunStatus:
        """Serialize local commands, then reload the shared cache under the lock."""
        with pipeline_lock(self._runs_dir):
            self._index = load_reuse_index(self._runs_dir)
            self._lineage = list(load_lineage(self._runs_dir))
            self._superseded = list(load_superseded(self._runs_dir))
            return self._execute_plan(context, plan, force=force)

    def _execute_plan(self, context: RunContext, plan: StagePlan, *, force: bool) -> RunStatus:
        missing = tuple(name for name in plan.execute if self._registry.get(name).runner is None)
        if missing:
            raise UnregisteredStageError(missing)
        executions: list[StageExecution] = []
        run_lineage: list[tuple[str, str]] = []
        shards = source_shard_ids(context)
        shard_keys = {
            shard_id: resolve_upstream(
                bind_shard(context, shard_id), plan.assumed_upstream, self._registry, self._index
            )
            for shard_id in shards
        }
        halted, halt_reason = walk_shards(
            plan.execute,
            shards,
            lambda name, shard_id: self._commit_shard(
                context, name, shard_id, shard_keys, force, executions, run_lineage
            ),
        )
        if self._cancel.cancelled:
            halted, halt_reason = True, "interrupted"
        current = RunStatus(
            context.run_id,
            context.generation_id,
            halted,
            halt_reason,
            tuple(executions),
            tuple(run_lineage),
            plan.not_selected,
        )
        save_status(self._runs_dir, merge_status(self._runs_dir, context.run_id, current))
        if context.profile == "fixture":
            write_manifest(self._runs_dir, context.run_id, scan_silos(context.silos))
        save_reuse_index(self._runs_dir, self._index, tuple(self._lineage), tuple(self._superseded))
        return current

    def _commit_shard(
        self,
        context: RunContext,
        name: str,
        shard_id: str,
        shard_keys: dict[str, dict[str, str]],
        force: bool,
        executions: list[StageExecution],
        run_lineage: list[tuple[str, str]],
    ) -> tuple[bool, str]:
        bound = bind_shard(context, shard_id)
        execution, halt_reason = self._execute_one(bound, name, shard_keys[shard_id], force)
        if execution is None or halt_reason:
            return True, halt_reason
        executions.append(execution)
        shard_keys[shard_id][name] = execution.reuse_key
        spec = self._registry.get(name)
        append_lineage(
            spec.depends_on,
            shard_keys[shard_id],
            execution.reuse_key,
            run_lineage,
            self._lineage,
        )
        entry = execution_to_entry(bound, execution, shard_id)
        if entry is not None:
            previous = self._index.get(entry.reuse_key)
            self._superseded = list(supersede_previous(previous, entry, self._superseded))
            self._index[entry.reuse_key] = entry
        halt_reason = stage_halt(execution)
        return bool(halt_reason), halt_reason

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
            with open_stage_session(context, name) as session, cancellation_scope(self._cancel):
                session.heartbeat()
                execution = execute_stage(
                    self._registry,
                    self._executor,
                    self._quality or self._stage_quality(context, name),
                    context,
                    name,
                    upstream,
                    self._index,
                    force=force,
                )
                failed = bool(stage_halt(execution))
                session.progress(
                    processed=1,
                    remaining=0,
                    bytes_delta=execution.bytes,
                    errors_delta=int(failed),
                    force=True,
                )
                session.complete(
                    outcome=execution.outcome,
                    failed=failed,
                    next_action="inspect logs and resume"
                    if failed
                    else "continue downstream stages",
                )
        except (InterruptedPipelineError, KeyboardInterrupt):
            return None, "interrupted"
        except PipelineError as error:
            return None, str(error)
        return execution, ""

    def _stage_quality(self, context: RunContext, name: str) -> QualityBoundary:
        if context.profile == "fixture":
            return FixtureQuality()
        if name in {"preflight", "inventory"}:
            from arxiv_int.pipeline.inventory.boundary import SourceSetQuality

            return SourceSetQuality(context, name)
        if name == "extract":
            from arxiv_int.extraction.boundary import ExtractionQuality

            return ExtractionQuality(context)
        return ProductionQuality()

    def invalidate(self, stage: str, *, document_id: str | None = None) -> tuple[str, ...]:
        """Serialize invalidation with publication and cache updates."""
        with pipeline_lock(self._runs_dir):
            self._index = load_reuse_index(self._runs_dir)
            self._lineage = list(load_lineage(self._runs_dir))
            self._superseded = list(load_superseded(self._runs_dir))
            return self._invalidate(stage, document_id=document_id)

    def invalidate_shards(self, shard_ids: frozenset[str]) -> tuple[str, ...]:
        """Mark shards with the given content-hash ids and their descendants stale."""
        with pipeline_lock(self._runs_dir):
            self._index = load_reuse_index(self._runs_dir)
            self._lineage = list(load_lineage(self._runs_dir))
            self._superseded = list(load_superseded(self._runs_dir))
            return self._invalidate("", document_id=None, shard_ids=shard_ids)

    def _invalidate(
        self,
        stage: str,
        *,
        document_id: str | None,
        shard_ids: frozenset[str] | None = None,
    ) -> tuple[str, ...]:
        self._index, marked = apply_invalidation(
            self._index,
            self._lineage,
            self._superseded,
            self._ledger.mark_stale,
            self._runs_dir,
            self._clock,
            stage,
            document_id,
            shard_ids,
        )
        return marked
