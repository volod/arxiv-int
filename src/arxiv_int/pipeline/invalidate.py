"""Mark reuse-index roots and descendants stale, then persist the plan."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from arxiv_int.pipeline.control.lineage import LineageEdge, stale_closure
from arxiv_int.pipeline.reconcile.model import INVALIDATION_SCHEMA, InvalidationPlan
from arxiv_int.pipeline.reconcile.persist import write_invalidation
from arxiv_int.pipeline.reuse_index import ReuseEntry, save_reuse_index

_CLOCK = Callable[[], float]


def apply_invalidation(
    index: dict[str, ReuseEntry],
    lineage: Sequence[tuple[str, str]],
    superseded: Sequence[ReuseEntry],
    mark_stale: Callable[[frozenset[str], float], object],
    runs_dir: Path,
    clock: _CLOCK,
    stage: str,
    document_id: str | None,
    shard_ids: frozenset[str] | None,
) -> tuple[dict[str, ReuseEntry], tuple[str, ...]]:
    """Update the reuse index and write per-run invalidation plans."""
    roots = invalidation_roots(index, stage, document_id, shard_ids)
    edges = tuple(LineageEdge(producer, consumer) for producer, consumer in lineage)
    marked = stale_closure(roots, edges)
    updated = {
        key: replace(entry, stale=True, status="stale") if key in marked else entry
        for key, entry in index.items()
    }
    mark_stale(marked, clock())
    save_reuse_index(runs_dir, updated, tuple(lineage), tuple(superseded))
    write_invalidation_plans(runs_dir, updated, stage, document_id or "", roots, marked)
    return updated, tuple(sorted(marked))


def invalidation_roots(
    index: Mapping[str, ReuseEntry],
    stage: str,
    document_id: str | None,
    shard_ids: frozenset[str] | None,
) -> list[str]:
    """Select live reuse keys for a stage, document, or content-hash set."""
    if shard_ids is not None:
        return [
            entry.reuse_key
            for entry in index.values()
            if not entry.stale and entry.shard_id in shard_ids
        ]
    return [
        entry.reuse_key
        for entry in index.values()
        if entry.stage == stage
        and not entry.stale
        and (document_id is None or entry.shard_id == document_id)
    ]


def write_invalidation_plans(
    runs_dir: Path,
    index: Mapping[str, ReuseEntry],
    stage: str,
    document_id: str,
    roots: Sequence[str],
    marked: frozenset[str] | set[str],
) -> InvalidationPlan:
    """Persist one invalidation plan under each producing run directory."""
    bytes_total = sum(entry.bytes for entry in index.values() if entry.reuse_key in marked)
    run_ids = {entry.run_id for entry in index.values() if entry.reuse_key in marked}
    plan = InvalidationPlan(
        INVALIDATION_SCHEMA,
        stage,
        tuple(sorted(roots)),
        tuple(sorted(marked)),
        bytes_total,
        len(marked),
        document_id,
    )
    for run_id in sorted(run_ids):
        write_invalidation(runs_dir, run_id, plan)
    return plan
