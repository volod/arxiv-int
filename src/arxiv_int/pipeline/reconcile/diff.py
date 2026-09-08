"""Diff complete comparable source manifests into add/change/rename/remove."""

from arxiv_int.pipeline.reconcile.model import (
    DELTA_SCHEMA,
    TOMBSTONE_SCHEMA,
    DeltaEvent,
    SourceDelta,
    SourceManifest,
    SourceOccurrence,
    Tombstone,
)


def diff_manifests(previous: SourceManifest, current: SourceManifest) -> SourceDelta:
    """Emit removals only when both scans are complete for the same silo."""
    before = previous.occurrence_map()
    after = current.occurrence_map()
    complete = previous.complete_silos() & current.complete_silos()
    comparable = previous.comparable and current.comparable
    remaining = _content_counts(current)
    added_keys = [key for key in after if key not in before]
    removed_keys = [
        key for key in before if key not in after and _silo_of(key) in complete and comparable
    ]
    changed: list[DeltaEvent] = []
    for key in sorted(set(before) & set(after)):
        old, new = before[key], after[key]
        if old.content_hash != new.content_hash:
            changed.append(_event("content-change", new, old))
    renamed, leftover_added, leftover_removed = _pair_renames(
        [before[key] for key in removed_keys],
        [after[key] for key in added_keys],
    )
    events = (
        tuple(_event("add", item) for item in leftover_added)
        + tuple(changed)
        + tuple(renamed)
        + tuple(
            _event("remove", item, remains=remaining.get(item.content_hash, 0) > 0)
            for item in leftover_removed
        )
    )
    withheld = tuple(
        sorted(
            key
            for key in before
            if key not in after and (_silo_of(key) not in complete or not comparable)
        )
    )
    return SourceDelta(
        DELTA_SCHEMA,
        previous.scan_id,
        current.scan_id,
        comparable,
        events,
        withheld,
    )


def tombstones_for(
    delta: SourceDelta,
    previous: SourceManifest,
    current: SourceManifest,
    generation_id: str,
) -> tuple[Tombstone, ...]:
    """Create tombstones for comparable removals; last-occurrence flags shared evidence."""
    records: list[Tombstone] = []
    previous_map = previous.occurrence_map()
    for event in delta.of_kind("remove"):
        old = previous_map.get(f"{event.silo_id}:{event.relative_path}")
        if old is None:
            continue
        records.append(
            Tombstone(
                TOMBSTONE_SCHEMA,
                old.occurrence_id,
                old.silo_id,
                old.relative_path,
                old.content_hash,
                current.scan_id,
                generation_id,
                not event.content_remains,
            )
        )
    return tuple(records)


def _pair_renames(
    removed: list[SourceOccurrence],
    added: list[SourceOccurrence],
) -> tuple[tuple[DeltaEvent, ...], tuple[SourceOccurrence, ...], tuple[SourceOccurrence, ...]]:
    """Pair a removal with an addition of the same content inside the same silo only.

    A file that appears in another silo is a distinct occurrence, and the silo-scoped
    path-event ledger cannot express a rename that crosses silos.
    """
    by_key: dict[tuple[str, str], list[SourceOccurrence]] = {}
    for item in sorted(removed, key=lambda occ: occ.path_key):
        by_key.setdefault((item.silo_id, item.content_hash), []).append(item)
    renamed: list[DeltaEvent] = []
    leftover_added: list[SourceOccurrence] = []
    claimed: set[str] = set()
    for item in sorted(added, key=lambda occ: occ.path_key):
        candidates = by_key.get((item.silo_id, item.content_hash), [])
        if not candidates:
            leftover_added.append(item)
            continue
        old = candidates.pop(0)
        claimed.add(old.path_key)
        renamed.append(_event("path-rename", item, old))
    leftover_removed = tuple(item for item in removed if item.path_key not in claimed)
    return tuple(renamed), tuple(leftover_added), leftover_removed


def _event(
    kind: str,
    item: SourceOccurrence,
    previous: SourceOccurrence | None = None,
    *,
    remains: bool = False,
) -> DeltaEvent:
    return DeltaEvent(
        kind,
        item.silo_id,
        item.relative_path,
        item.content_hash,
        previous.relative_path if previous is not None else "",
        previous.content_hash if previous is not None else "",
        previous.silo_id if previous is not None else "",
        remains,
    )


def _silo_of(path_key: str) -> str:
    return path_key.split(":", 1)[0]


def _content_counts(manifest: SourceManifest) -> dict[str, int]:
    counts: dict[str, int] = {}
    for silo in manifest.silos:
        for item in silo.occurrences:
            if item.readable:
                counts[item.content_hash] = counts.get(item.content_hash, 0) + 1
    return counts
