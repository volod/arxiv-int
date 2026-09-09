"""In-memory active derived views that retract last-occurrence outputs only."""

from dataclasses import dataclass, replace

from arxiv_int.pipeline.reconcile.model import SourceOccurrence, Tombstone


@dataclass(frozen=True, slots=True)
class DerivedRow:
    """One active derived record keyed by content identity plus supporting paths."""

    content_hash: str
    row_id: str
    paths: frozenset[str]
    kind: str = "document"
    review_state: str = "active"
    shared_with: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ActiveView:
    """Canonical/derived rows that remain after tombstones and replacements."""

    rows: tuple[DerivedRow, ...]
    retracted: tuple[str, ...]
    retained: tuple[str, ...]


def view_from_occurrences(occurrences: tuple[SourceOccurrence, ...]) -> ActiveView:
    """Group readable occurrences by content hash."""
    grouped: dict[str, list[str]] = {}
    for item in occurrences:
        if not item.readable:
            continue
        grouped.setdefault(item.content_hash, []).append(item.path_key)
    rows = tuple(
        DerivedRow(content_hash, content_hash, frozenset(paths))
        for content_hash, paths in sorted(grouped.items())
    )
    return ActiveView(rows, (), tuple(row.row_id for row in rows))


def retract(
    view: ActiveView,
    tombstones: tuple[Tombstone, ...],
    replacements: tuple[DerivedRow, ...] = (),
) -> ActiveView:
    """Drop rows whose last supporting occurrence is gone; keep shared evidence."""
    by_id = {row.row_id: row for row in view.rows}
    for row in replacements:
        by_id[row.row_id] = row
    retracted: list[str] = []
    missing: set[str] = set()
    for tomb in tombstones:
        _apply_tombstone(by_id, tomb, retracted, missing)
    rows = tuple(by_id[key] for key in sorted(by_id))
    return ActiveView(rows, tuple(dict.fromkeys(retracted)), tuple(row.row_id for row in rows))


def _apply_tombstone(
    by_id: dict[str, DerivedRow],
    tomb: Tombstone,
    retracted: list[str],
    missing: set[str],
) -> None:
    matching = [row for row in by_id.values() if row.content_hash == tomb.content_hash]
    if not matching:
        _retract_absent(tomb, retracted, missing)
        return
    path = f"{tomb.silo_id}:{tomb.relative_path}"
    for current in matching:
        _retract_or_keep(by_id, current, path, tomb, retracted)


def _retract_absent(tomb: Tombstone, retracted: list[str], missing: set[str]) -> None:
    if tomb.last_occurrence and tomb.content_hash not in missing:
        retracted.append(tomb.content_hash)
        missing.add(tomb.content_hash)


def _retract_or_keep(
    by_id: dict[str, DerivedRow],
    current: DerivedRow,
    path: str,
    tomb: Tombstone,
    retracted: list[str],
) -> None:
    remaining = frozenset(item for item in current.paths if item != path)
    if remaining:
        by_id[current.row_id] = replace(current, paths=remaining)
        return
    if current.shared_with or current.review_state in {"review", "merged", "split"}:
        return
    if tomb.last_occurrence:
        retracted.append(current.row_id)
        by_id.pop(current.row_id, None)


def merge_rows(left: DerivedRow, right: DerivedRow, merged_id: str) -> DerivedRow:
    """Keep both evidence sets under one review overlay identity."""
    return DerivedRow(
        left.content_hash,
        merged_id,
        left.paths | right.paths,
        left.kind,
        "merged",
        left.shared_with | right.shared_with | {left.row_id, right.row_id},
    )


def split_row(row: DerivedRow, new_id: str) -> tuple[DerivedRow, DerivedRow]:
    """Split a review overlay without dropping source evidence."""
    first = replace(row, review_state="split", shared_with=row.shared_with | {new_id})
    second = DerivedRow(
        row.content_hash,
        new_id,
        row.paths,
        row.kind,
        "split",
        row.shared_with | {row.row_id},
    )
    return first, second
