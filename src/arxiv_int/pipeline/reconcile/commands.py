"""Apply source deltas before an incremental DAG walk."""

from pathlib import Path

from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.reconcile.closure import invalidate_hashes
from arxiv_int.pipeline.reconcile.diff import diff_manifests, tombstones_for
from arxiv_int.pipeline.reconcile.model import (
    REBUILD_SCHEMA,
    RebuildReport,
    SiloScan,
    SourceDelta,
    SourceManifest,
    SourceOccurrence,
    Tombstone,
)
from arxiv_int.pipeline.reconcile.persist import (
    comparable_checksums,
    load_manifest,
    write_delta,
    write_manifest,
    write_rebuild,
    write_tombstones,
)
from arxiv_int.pipeline.reconcile.scan import scan_silos
from arxiv_int.pipeline.reconcile.views import (
    ActiveView,
    DerivedRow,
    retract,
    view_from_occurrences,
)
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import load_status
from arxiv_int.pipeline.run.reuse_index import load_lineage, load_reuse_index


def prepare_update(
    previous: RunContext,
    current: RunContext,
    orchestrator: Orchestrator | None = None,
) -> tuple[SourceDelta, ActiveView]:
    """Diff saved vs current manifests, tombstone comparable removals, invalidate shards."""
    previous_manifest = load_manifest(previous.runs_dir, previous.run_id) or SourceManifest(
        "empty",
        tuple(SiloScan(silo.silo_id, True, True, ()) for silo in previous.silos),
        True,
    )
    current_manifest = scan_silos(current.silos)
    write_manifest(current.runs_dir, current.run_id, current_manifest)
    delta = diff_manifests(previous_manifest, current_manifest)
    write_delta(current.runs_dir, current.run_id, delta)
    tombs = tombstones_for(delta, previous_manifest, current_manifest, current.generation_id)
    write_tombstones(current.runs_dir, current.run_id, tombs)
    index = load_reuse_index(current.runs_dir)
    edges = load_lineage(current.runs_dir)
    marked = invalidate_hashes(delta, index, edges)
    if marked and orchestrator is not None:
        shard_ids = frozenset(
            entry.shard_id for entry in index.values() if entry.reuse_key in marked
        )
        orchestrator.invalidate_shards(shard_ids)
    view = _active_view(previous_manifest, current_manifest, tombs)
    return delta, view


def record_rebuild(
    previous: RunContext, current: RunContext, *, activated: bool = False
) -> RebuildReport:
    """Compare isolated rebuild payloads without generation tokens and persist the report."""
    first = comparable_checksums(load_status(previous.runs_dir, previous.run_id).executions)
    second = comparable_checksums(load_status(current.runs_dir, current.run_id).executions)
    report = RebuildReport(
        REBUILD_SCHEMA,
        current.run_id,
        current.generation_id,
        previous.generation_id,
        second,
        first == second,
        activated,
        True,
    )
    write_rebuild(current.runs_dir, current.run_id, report)
    return report


def _active_view(
    previous: SourceManifest,
    current: SourceManifest,
    tombs: tuple[Tombstone, ...],
) -> ActiveView:
    view = retract(view_from_occurrences(_readable(previous)), tombs)
    current_hashes = {item.content_hash for item in _readable(current)}
    observable = _observable_silos(previous, current)
    kept: list[DerivedRow] = []
    extra_retracted: list[str] = []
    for row in view.rows:
        if row.content_hash in current_hashes:
            kept.append(row)
            continue
        if row.shared_with or row.review_state in {"review", "merged", "split"}:
            kept.append(row)
            continue
        if not _fully_observed(row, observable):
            kept.append(row)
            continue
        extra_retracted.append(row.row_id)
    rows = tuple(kept)
    retracted = tuple(dict.fromkeys((*view.retracted, *extra_retracted)))
    present = {row.content_hash for row in rows} | set(retracted)
    added = tuple(item for item in _readable(current) if item.content_hash not in present)
    if added:
        extra = view_from_occurrences(added)
        rows = rows + extra.rows
    return ActiveView(rows, retracted, tuple(row.row_id for row in rows))


def _readable(manifest: SourceManifest) -> tuple[SourceOccurrence, ...]:
    return tuple(item for silo in manifest.silos for item in silo.occurrences if item.readable)


def _observable_silos(previous: SourceManifest, current: SourceManifest) -> frozenset[str]:
    """Silos whose absent content is real evidence, mirroring the removal rule in the diff."""
    if not (previous.comparable and current.comparable):
        return frozenset()
    return previous.complete_silos() & current.complete_silos()


def _fully_observed(row: DerivedRow, observable: frozenset[str]) -> bool:
    """Return whether every path supporting one row was rescanned completely."""
    return all(path.split(":", 1)[0] in observable for path in row.paths)


def load_previous_manifest(runs_dir: Path, run_id: str) -> SourceManifest | None:
    """Return the sealed source manifest for a prior generation."""
    return load_manifest(runs_dir, run_id)
