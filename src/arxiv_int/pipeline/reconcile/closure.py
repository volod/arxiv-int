"""Map source deltas onto reuse-key stale closures."""

from collections.abc import Mapping, Sequence

from arxiv_int.pipeline.control.lineage import LineageEdge, stale_closure
from arxiv_int.pipeline.reconcile.model import SourceDelta
from arxiv_int.pipeline.reuse_index import ReuseEntry


def affected_hashes(delta: SourceDelta) -> frozenset[str]:
    """Content hashes whose owning shards must recompute."""
    hashes: set[str] = set()
    for event in delta.events:
        if event.kind == "path-rename":
            continue
        if event.kind == "add":
            hashes.add(event.content_hash)
            continue
        if event.kind == "content-change":
            if event.previous_hash:
                hashes.add(event.previous_hash)
            hashes.add(event.content_hash)
            continue
        if event.kind == "remove":
            hashes.add(event.content_hash)
    return frozenset(hashes)


def rename_hashes(delta: SourceDelta) -> frozenset[str]:
    """Content hashes that moved path without a byte change."""
    return frozenset(event.content_hash for event in delta.of_kind("path-rename"))


def added_hashes(delta: SourceDelta) -> frozenset[str]:
    """New content that must create shards without touching existing ones."""
    return frozenset(event.content_hash for event in delta.of_kind("add"))


def invalidate_hashes(
    delta: SourceDelta,
    index: Mapping[str, ReuseEntry],
    edges: Sequence[tuple[str, str]],
) -> frozenset[str]:
    """Mark owning shards and descendants for change/remove, never path-only rename."""
    roots = [
        entry.reuse_key
        for entry in index.values()
        if not entry.stale and entry.shard_id in _invalidation_roots(delta)
    ]
    lineage = tuple(LineageEdge(producer, consumer) for producer, consumer in edges)
    return stale_closure(roots, lineage)


def _invalidation_roots(delta: SourceDelta) -> frozenset[str]:
    roots: set[str] = set()
    for event in delta.events:
        if event.kind == "content-change" and event.previous_hash:
            roots.add(event.previous_hash)
        elif event.kind == "remove":
            roots.add(event.content_hash)
    return frozenset(roots)
