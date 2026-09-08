"""Retain compact manifests, lineage, checksums, and tombstones after prune."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arxiv_int.pipeline.persist import load_json, write_json

PRUNED_DIR = "pruned"


def compact_lineage(
    edges: Sequence[tuple[str, str]],
    pruned_keys: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    """Drop edges whose producer and consumer were both pruned."""
    removed = set(pruned_keys)
    kept: list[tuple[str, str]] = []
    for producer, consumer in edges:
        if producer in removed and consumer in removed:
            continue
        kept.append((producer, consumer))
    return tuple(dict.fromkeys(kept))


def retain_attempt(directory: Path, destination: Path, reuse_key: str) -> Path | None:
    """Copy checksums from an attempt manifest before deleting the tree."""
    manifest = directory / "manifest.json"
    if not manifest.is_file():
        return None
    payload: dict[str, Any] = load_json(manifest)
    retained = {
        "checksums": payload.get("files", {}),
        "directory": str(directory),
        "reuse_key": reuse_key,
        "tombstones": True,
    }
    path = destination / PRUNED_DIR / f"{reuse_key}.json"
    write_json(path, retained)
    return path


def retain_many(
    runs_dir: Path,
    entries: Sequence[Any],
) -> tuple[Path, ...]:
    """Write compact retained records for each eligible attempt."""
    written: list[Path] = []
    for entry in entries:
        directory = Path(entry.directory)
        path = retain_attempt(directory, runs_dir, entry.reuse_key)
        if path is not None:
            written.append(path)
    return tuple(written)


def compact_index_payload(
    entries: Mapping[str, Any],
    lineage: Sequence[tuple[str, str]],
    pruned_keys: Sequence[str],
) -> dict[str, Any]:
    """Return a reuse-index payload with pruned keys removed from live entries."""
    remaining = {key: entries[key] for key in entries if key not in set(pruned_keys)}
    return {
        "entries": remaining,
        "lineage": [list(edge) for edge in compact_lineage(lineage, pruned_keys)],
    }
