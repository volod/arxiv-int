"""Cross-run reuse index and lineage persistence."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from arxiv_int.pipeline.run.persist import load_json, write_json

REUSE_INDEX_NAME = "reuse-index.json"


@dataclass(frozen=True, slots=True)
class ReuseEntry:
    """Cross-run cache pointer for one reuse key."""

    reuse_key: str
    stage: str
    shard_id: str
    attempt: int
    directory: str
    status: str
    bytes: int
    run_id: str
    generation_id: str
    stale: bool


def load_reuse_index(runs_dir: Path) -> dict[str, ReuseEntry]:
    """Load the cross-run reuse index, or an empty map."""
    path = runs_dir / REUSE_INDEX_NAME
    if not path.is_file():
        return {}
    payload = load_json(path)
    entries = {}
    for item in payload.get("entries", ()):
        entry = _reuse_from_payload(item)
        entries[entry.reuse_key] = entry
    return entries


def load_superseded(runs_dir: Path) -> tuple[ReuseEntry, ...]:
    """Load prior attempt directories replaced by a later generation."""
    path = runs_dir / REUSE_INDEX_NAME
    if not path.is_file():
        return ()
    payload = load_json(path)
    return tuple(_reuse_from_payload(item) for item in payload.get("superseded", ()))


def save_reuse_index(
    runs_dir: Path,
    entries: Mapping[str, ReuseEntry],
    lineage: tuple[tuple[str, str], ...] = (),
    superseded: Sequence[ReuseEntry] = (),
) -> Path:
    """Replace the cross-run reuse index, lineage edges, and superseded attempts."""
    path = runs_dir / REUSE_INDEX_NAME
    write_json(
        path,
        {
            "entries": [_reuse_payload(entries[key]) for key in sorted(entries)],
            "lineage": [list(edge) for edge in lineage],
            "superseded": [_reuse_payload(item) for item in superseded],
        },
    )
    return path


def load_lineage(runs_dir: Path) -> tuple[tuple[str, str], ...]:
    """Load producer-consumer reuse-key edges from the reuse index."""
    path = runs_dir / REUSE_INDEX_NAME
    if not path.is_file():
        return ()
    payload = load_json(path)
    return tuple((str(left), str(right)) for left, right in payload.get("lineage", ()))


def supersede_previous(
    previous: ReuseEntry | None,
    replacement: ReuseEntry,
    superseded: Sequence[ReuseEntry],
) -> tuple[ReuseEntry, ...]:
    """Keep the prior directory when a new attempt replaces a live reuse key."""
    if previous is None or previous.directory == replacement.directory:
        return tuple(superseded)
    if any(item.directory == previous.directory for item in superseded):
        return tuple(superseded)
    retained = replace(previous, stale=True, status="superseded")
    return tuple((*superseded, retained))


def _reuse_from_payload(item: Mapping[str, Any]) -> ReuseEntry:
    return ReuseEntry(
        str(item["reuse_key"]),
        str(item["stage"]),
        str(item["shard_id"]),
        int(item["attempt"]),
        str(item["directory"]),
        str(item["status"]),
        int(item["bytes"]),
        str(item["run_id"]),
        str(item["generation_id"]),
        bool(item["stale"]),
    )


def _reuse_payload(entry: ReuseEntry) -> dict[str, Any]:
    return {
        "reuse_key": entry.reuse_key,
        "stage": entry.stage,
        "shard_id": entry.shard_id,
        "attempt": entry.attempt,
        "directory": entry.directory,
        "status": entry.status,
        "bytes": entry.bytes,
        "run_id": entry.run_id,
        "generation_id": entry.generation_id,
        "stale": entry.stale,
    }
