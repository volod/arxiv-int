"""Invalidate, rebuild, incremental update, status, and stale-prune planning."""

from dataclasses import replace
from pathlib import Path

from arxiv_int.pipeline.dag.graph import StagePlan, select_plan
from arxiv_int.pipeline.dag.registry import StageRegistry
from arxiv_int.pipeline.dag.stages import OPTIONAL_STAGES, profile_stage_names
from arxiv_int.pipeline.prune import PrunePlan, apply_prune_plan, build_prune_plan
from arxiv_int.pipeline.run.context import RunContext, allocate_run_id, snapshot_silos
from arxiv_int.pipeline.run.persist import RunStatus, load_status, save_context
from arxiv_int.runtime.setup.requirements import PROFILE_STAGES


def remaining_plan(plan: StagePlan, status: RunStatus | None) -> StagePlan:
    """Resume by skipping stages that already succeeded on this run."""
    if status is None:
        return plan
    succeeded = tuple(
        item.stage
        for item in status.executions
        if item.status in {"succeeded", "quarantined"} and item.outcome in {"produced", "empty"}
    )
    done = set(succeeded)
    execute = tuple(name for name in plan.execute if name not in done)
    assumed = tuple(dict.fromkeys((*plan.assumed_upstream, *succeeded)))
    return StagePlan(execute, assumed, plan.not_selected)


def rebuild_context(previous: RunContext) -> RunContext:
    """Allocate a new generation without changing the frozen configuration."""
    run_id = allocate_run_id()
    return replace(previous, run_id=run_id, generation_id=run_id)


def update_context(previous: RunContext) -> RunContext:
    """Allocate a new generation whose identities see the current archive snapshot."""
    run_id = allocate_run_id()
    return replace(
        previous,
        run_id=run_id,
        generation_id=run_id,
        source_snapshot=snapshot_silos(previous.silos),
    )


def plan_for(
    registry: StageRegistry,
    context: RunContext,
    *,
    from_stage: str | None = None,
    to_stage: str | None = None,
) -> StagePlan:
    """Resolve a range against the frozen profile and registry optional flags."""
    optional = frozenset(spec.name for spec in registry.specs() if spec.optional) | OPTIONAL_STAGES
    if context.profile in PROFILE_STAGES:
        profile_stages = profile_stage_names(context.profile)
    else:
        profile_stages = tuple(name for name in registry.names() if name not in optional)
    return select_plan(
        registry.dependencies(),
        profile_stages=profile_stages,
        optional_stages=optional,
        from_stage=from_stage if from_stage is not None else context.from_stage,
        to_stage=to_stage if to_stage is not None else context.to_stage,
    )


def fixture_plan(
    registry: StageRegistry,
    *,
    from_stage: str | None = None,
    to_stage: str | None = None,
    profile_stages: tuple[str, ...] = (),
    optional_stages: frozenset[str] = frozenset(),
) -> StagePlan:
    """Resolve a plan for a fixture registry that is not a setup profile."""
    required = profile_stages or tuple(
        name for name in registry.names() if name not in optional_stages
    )
    return select_plan(
        registry.dependencies(),
        profile_stages=required,
        optional_stages=optional_stages,
        from_stage=from_stage,
        to_stage=to_stage,
    )


def status_lines(status: RunStatus) -> tuple[str, ...]:
    """Render a secret-free status summary."""
    lines = [
        f"run_id={status.run_id}",
        f"generation_id={status.generation_id}",
        f"halted={str(status.halted).lower()}",
    ]
    if status.halt_reason:
        lines.append(f"halt_reason={status.halt_reason}")
    for item in status.executions:
        lines.append(
            f"stage={item.stage} shard={item.shard_id} status={item.status} "
            f"cache_hit={str(item.cache_hit).lower()} attempt={item.attempt}"
        )
    if status.not_selected:
        lines.append("not_selected=" + ",".join(status.not_selected))
    return tuple(lines)


def load_run_status(runs_dir: Path, run_id: str) -> RunStatus:
    """Load status.json for one run."""
    return load_status(runs_dir, run_id)


def persist_new_context(context: RunContext) -> RunContext:
    """Write a newly allocated run context."""
    save_context(context)
    return context


__all__ = [
    "PrunePlan",
    "apply_prune_plan",
    "build_prune_plan",
    "fixture_plan",
    "load_run_status",
    "persist_new_context",
    "plan_for",
    "rebuild_context",
    "remaining_plan",
    "status_lines",
    "update_context",
]
