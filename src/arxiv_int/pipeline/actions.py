"""Invalidate, rebuild, incremental update, status, and stale-prune planning."""

from dataclasses import dataclass, replace
from pathlib import Path
from uuid import uuid4

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.pipeline.context import RunContext, allocate_run_id, snapshot_silos
from arxiv_int.pipeline.graph import StagePlan, select_plan
from arxiv_int.pipeline.persist import (
    PRUNE_DIR,
    RunStatus,
    load_json,
    load_status,
    save_context,
    write_json,
)
from arxiv_int.pipeline.registry import StageRegistry
from arxiv_int.pipeline.reuse_index import ReuseEntry, load_reuse_index
from arxiv_int.pipeline.stages import OPTIONAL_STAGES, profile_stage_names
from arxiv_int.runtime.setup.requirements import PROFILE_STAGES


@dataclass(frozen=True, slots=True)
class PrunePlan:
    """Dry-run list of stale derived attempts; apply requires this fingerprint."""

    plan_id: str
    fingerprint: str
    entries: tuple[ReuseEntry, ...]
    bytes: int
    blocked: tuple[str, ...]


def remaining_plan(plan: StagePlan, status: RunStatus | None) -> StagePlan:
    """Resume by skipping stages that already succeeded on this run."""
    if status is None:
        return plan
    succeeded = tuple(
        item.stage for item in status.executions if item.status in {"succeeded", "quarantined"}
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
            f"stage={item.stage} status={item.status} cache_hit={str(item.cache_hit).lower()} "
            f"attempt={item.attempt}"
        )
    if status.not_selected:
        lines.append("not_selected=" + ",".join(status.not_selected))
    return tuple(lines)


def _prune_sets(
    runs_dir: Path,
) -> tuple[tuple[ReuseEntry, ...], tuple[ReuseEntry, ...], tuple[str, ...]]:
    index = load_reuse_index(runs_dir)
    stale = tuple(entry for entry in index.values() if entry.stale)
    live_dirs = {entry.directory for entry in index.values() if not entry.stale}
    blocked = tuple(entry.directory for entry in stale if entry.directory not in live_dirs)
    eligible = tuple(entry for entry in stale if entry.directory not in set(blocked))
    return stale, eligible, blocked


def _prune_fingerprint(entries: tuple[ReuseEntry, ...]) -> str:
    payload = {
        "bytes": sum(entry.bytes for entry in entries),
        "directories": sorted(entry.directory for entry in entries),
    }
    return sha256_text(normalize_json(payload))


def build_prune_plan(runs_dir: Path) -> PrunePlan:
    """List stale derived attempts; apply deletes only non-blocked entries."""
    stale, eligible, blocked = _prune_sets(runs_dir)
    plan_id = f"prune-{uuid4().hex}"
    fingerprint = _prune_fingerprint(eligible)
    plan = PrunePlan(plan_id, fingerprint, stale, sum(entry.bytes for entry in stale), blocked)
    write_json(
        runs_dir / PRUNE_DIR / f"{plan_id}.json",
        {
            "blocked": list(blocked),
            "bytes": plan.bytes,
            "directories": [entry.directory for entry in eligible],
            "fingerprint": fingerprint,
            "plan_id": plan_id,
        },
    )
    return plan


def apply_prune_plan(runs_dir: Path, plan_id: str) -> int:
    """Delete directories listed in a previously written dry-run plan."""
    path = runs_dir / PRUNE_DIR / f"{plan_id}.json"
    payload = load_json(path)
    _stale, eligible, blocked = _prune_sets(runs_dir)
    if _prune_fingerprint(eligible) != str(payload.get("fingerprint")):
        raise ValueError("prune plan is stale; rerun the dry-run")
    removed = 0
    for directory in payload["directories"]:
        target = Path(str(directory)).resolve()
        if target.as_posix() in blocked:
            raise ValueError(f"refusing to delete sole recovery copy: {target}")
        root = runs_dir.resolve()
        if root not in target.parents:
            raise ValueError(f"refusing to delete path outside RUNS_DIR: {target}")
        if target.is_dir():
            _remove_tree(target)
            removed += 1
    return removed


def load_run_status(runs_dir: Path, run_id: str) -> RunStatus:
    """Load status.json for one run."""
    return load_status(runs_dir, run_id)


def persist_new_context(context: RunContext) -> RunContext:
    """Write a newly allocated run context."""
    save_context(context)
    return context


def _remove_tree(directory: Path) -> None:
    for child in directory.iterdir():
        if child.is_dir():
            _remove_tree(child)
        else:
            child.unlink()
    directory.rmdir()
