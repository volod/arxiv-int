"""Merge resumed stage rows and halt reasons for one DAG walk."""

from collections.abc import Callable
from pathlib import Path

from arxiv_int.pipeline.run.persist import RunStatus, StageExecution, load_status, run_dir


def stage_halt(execution: StageExecution) -> str:
    """Return a halt reason when a shard cannot continue the DAG."""
    if execution.status not in {"succeeded", "quarantined"}:
        return execution.detail
    if execution.outcome == "partial":
        return execution.detail or "partial stage output"
    return ""


def append_lineage(
    depends_on: tuple[str, ...],
    keys: dict[str, str],
    consumer: str,
    run_lineage: list[tuple[str, str]],
    stored: list[tuple[str, str]],
) -> None:
    """Record producer-consumer reuse-key edges for one shard."""
    for producer in depends_on:
        if producer not in keys:
            continue
        edge = (keys[producer], consumer)
        run_lineage.append(edge)
        if edge not in stored:
            stored.append(edge)


def walk_shards(
    names: tuple[str, ...],
    shards: tuple[str, ...],
    commit: Callable[[str, str], tuple[bool, str]],
) -> tuple[bool, str]:
    """Run commit(name, shard_id) until a shard requests a halt."""
    for name in names:
        for shard_id in shards:
            halted, reason = commit(name, shard_id)
            if halted:
                return True, reason
    return False, ""


def merge_status(runs_dir: Path, run_id: str, current: RunStatus) -> RunStatus:
    """Keep prior stage rows when an atomic or resume walk covers a subset."""
    path = run_dir(runs_dir, run_id) / "status.json"
    if not path.is_file():
        return current
    prior = load_status(runs_dir, run_id)
    by_item = {(item.stage, item.shard_id): item for item in prior.executions}
    order = [(item.stage, item.shard_id) for item in prior.executions]
    for item in current.executions:
        key = (item.stage, item.shard_id)
        by_item[key] = item
        if key not in order:
            order.append(key)
    lineage = tuple(dict.fromkeys((*prior.lineage, *current.lineage)))
    skipped = tuple(dict.fromkeys((*prior.not_selected, *current.not_selected)))
    return RunStatus(
        current.run_id,
        current.generation_id,
        current.halted,
        current.halt_reason,
        tuple(by_item[key] for key in order),
        lineage,
        skipped,
    )
