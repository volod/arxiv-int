"""Add/change/rename/remove mutations on a disposable proof copy."""

from collections.abc import Callable
from pathlib import Path

from arxiv_int.evaluation.evaluate.errors import ProofIntegrityError
from arxiv_int.evaluation.proof.control_copy import ADD_NAME
from arxiv_int.evaluation.proof.control_model import ShardDelta
from arxiv_int.pipeline.dag.actions import persist_new_context, update_context
from arxiv_int.pipeline.dag.graph import StagePlan
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.dag.registry import StageRegistry
from arxiv_int.pipeline.reconcile.commands import prepare_update
from arxiv_int.pipeline.reconcile.model import TOMBSTONE_SCHEMA, Tombstone
from arxiv_int.pipeline.reconcile.persist import load_json, run_dir
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import RunStatus
from arxiv_int.runtime.config_model import RuntimeConfig

WalkFn = Callable[[RunContext, RuntimeConfig, StageRegistry, StagePlan], RunStatus]


def run_source_deltas(
    context: RunContext,
    config: RuntimeConfig,
    registry: StageRegistry,
    plan: StagePlan,
    walk: WalkFn,
) -> tuple[RunContext, dict[str, ShardDelta]]:
    """Apply add/change/rename/remove on the copy and record shard closures."""
    current = context
    reports: dict[str, ShardDelta] = {}
    for name, kind, mutate in (
        ("add", "add", add_file),
        ("change", "content-change", change_file),
        ("rename", "path-rename", rename_file),
        ("remove", "remove", remove_file),
    ):
        current, reports[name] = apply_delta(current, config, registry, plan, kind, mutate, walk)
    return current, reports


def apply_delta(
    previous: RunContext,
    config: RuntimeConfig,
    registry: StageRegistry,
    plan: StagePlan,
    kind: str,
    mutate: Callable[[Path], None],
    walk: WalkFn,
) -> tuple[RunContext, ShardDelta]:
    """Mutate the copy, reconcile, and walk the DAG for one delta kind."""
    mutate(previous.silos[0].root)
    updated = persist_new_context(update_context(previous))
    delta, view = prepare_update(previous, updated, Orchestrator(registry, updated.runs_dir))
    status = walk(updated, config, registry, plan)
    invoked, cached = stage_shards(status, "alpha")
    tombs = load_tombstones(updated)
    return updated, ShardDelta(
        kind,
        tuple(event.kind for event in delta.events),
        tuple(sorted(invoked)),
        tuple(sorted(cached)),
        tuple(item.content_hash for item in tombs),
        len(view.retracted),
        sum(1 for item in tombs if item.last_occurrence),
        len(view.rows),
    )


def add_file(root: Path) -> None:
    """Create one new file on the disposable copy."""
    (root / ADD_NAME).write_text("pipeline-control-add\n", encoding="ascii")


def change_file(root: Path) -> None:
    """Overwrite one existing copy file without touching ARCHIVE_DIR."""
    target = mutable_file(root, exclude={ADD_NAME})
    target.write_bytes(target.read_bytes() + b"\nchanged\n")


def rename_file(root: Path) -> None:
    """Rename one existing copy file."""
    target = mutable_file(root, exclude={ADD_NAME})
    target.rename(target.with_name(target.name + ".renamed"))


def remove_file(root: Path) -> None:
    """Delete one existing copy file."""
    mutable_file(root, exclude={ADD_NAME}).unlink()


def mutable_file(root: Path, *, exclude: set[str]) -> Path:
    """Pick a regular file on the copy that is safe to mutate."""
    files = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink() and path.name not in exclude
    ]
    if not files:
        raise ProofIntegrityError("disposable proof copy has no file to mutate")
    return files[-1]


def stage_shards(status: RunStatus, stage: str) -> tuple[set[str], set[str]]:
    """Return invoked and cached shard ids for one stage."""
    invoked = {
        item.shard_id for item in status.executions if item.stage == stage and item.worker_invoked
    }
    cached = {item.shard_id for item in status.executions if item.stage == stage and item.cache_hit}
    return invoked, cached


def load_tombstones(context: RunContext) -> tuple[Tombstone, ...]:
    """Load persisted removal tombstones for the current generation."""
    path = run_dir(context.runs_dir, context.run_id) / "delta" / "tombstones.json"
    if not path.is_file():
        return ()
    payload = load_json(path)
    rows = payload.get("tombstones", ())
    if not isinstance(rows, list):
        return ()
    loaded: list[Tombstone] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        loaded.append(
            Tombstone(
                TOMBSTONE_SCHEMA,
                str(item.get("occurrence_id", "missing")),
                str(item.get("silo_id", "default")),
                str(item.get("relative_path", "missing.txt")),
                str(item.get("content_hash", "missing")),
                str(item.get("scan_id", "scan")),
                str(item.get("generation_id", context.generation_id)),
                bool(item.get("last_occurrence", False)),
                str(item.get("reason", "remove")),
            )
        )
    return tuple(loaded)
