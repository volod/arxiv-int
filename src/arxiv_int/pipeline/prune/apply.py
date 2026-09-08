"""Apply a previously written prune plan after rechecking protections."""

from collections.abc import Sequence
from pathlib import Path

from arxiv_int.pipeline.persist import load_json
from arxiv_int.pipeline.prune.compact import compact_lineage, retain_many
from arxiv_int.pipeline.prune.model import PRUNE_SCHEMA, PruneEvent
from arxiv_int.pipeline.prune.plan import PRUNE_DIR, fingerprint_for
from arxiv_int.pipeline.prune.protect import blocked_directories, protections
from arxiv_int.pipeline.reuse_index import (
    ReuseEntry,
    load_lineage,
    load_reuse_index,
    load_superseded,
    save_reuse_index,
)


class PruneRefusedError(ValueError):
    """Raised when apply would delete protected or out-of-root data."""


def apply_prune_plan(runs_dir: Path, plan_id: str) -> int:
    """Delete eligible directories listed in a previously written dry-run plan."""
    path = runs_dir / PRUNE_DIR / f"{plan_id}.json"
    payload = load_json(path)
    index, superseded, eligible, blocked_dirs = _recheck(runs_dir)
    if fingerprint_for(eligible) != str(payload.get("fingerprint")):
        raise PruneRefusedError("prune plan is stale; rerun the dry-run")
    retain_many(runs_dir, eligible)
    listed = tuple(str(item) for item in payload["directories"])
    removed = _delete_listed(runs_dir, listed, blocked_dirs)
    _save_after_delete(runs_dir, index, superseded, listed)
    _write_event(runs_dir, plan_id, str(payload.get("fingerprint", "")), removed)
    return removed


def _recheck(
    runs_dir: Path,
) -> tuple[dict[str, ReuseEntry], tuple[ReuseEntry, ...], tuple[ReuseEntry, ...], frozenset[str]]:
    index = load_reuse_index(runs_dir)
    superseded = load_superseded(runs_dir)
    live = {key: entry for key, entry in index.items() if not entry.stale}
    stale = tuple(entry for entry in index.values() if entry.stale) + superseded
    blocked = protections(runs_dir, stale, live, superseded)
    blocked_dirs = blocked_directories(blocked)
    eligible = tuple(entry for entry in stale if entry.directory not in blocked_dirs)
    return index, superseded, eligible, blocked_dirs


def _delete_listed(runs_dir: Path, directories: Sequence[str], blocked_dirs: frozenset[str]) -> int:
    root = runs_dir.resolve()
    removed = 0
    for directory in directories:
        target = Path(directory).resolve()
        _refuse_protected(directory, target, blocked_dirs, root)
        if target.is_dir():
            _remove_tree(target)
            removed += 1
    return removed


def _refuse_protected(
    directory: str, target: Path, blocked_dirs: frozenset[str], root: Path
) -> None:
    if directory in blocked_dirs or target.as_posix() in blocked_dirs:
        raise PruneRefusedError(f"refusing to delete protected data: {target}")
    if root not in target.parents:
        raise PruneRefusedError(f"refusing to delete path outside RUNS_DIR: {target}")


def _save_after_delete(
    runs_dir: Path,
    index: dict[str, ReuseEntry],
    superseded: tuple[ReuseEntry, ...],
    directories: Sequence[str],
) -> None:
    listed_set = {Path(directory).resolve() for directory in directories}
    remaining = {
        key: entry
        for key, entry in index.items()
        if Path(entry.directory).resolve() not in listed_set
    }
    remaining_superseded = tuple(
        entry for entry in superseded if Path(entry.directory).resolve() not in listed_set
    )
    before_keys = set(index) | {entry.reuse_key for entry in superseded}
    after_keys = set(remaining) | {entry.reuse_key for entry in remaining_superseded}
    save_reuse_index(
        runs_dir,
        remaining,
        compact_lineage(load_lineage(runs_dir), tuple(sorted(before_keys - after_keys))),
        remaining_superseded,
    )


def _write_event(runs_dir: Path, plan_id: str, fingerprint: str, removed: int) -> PruneEvent:
    from arxiv_int.pipeline.persist import write_json

    event = PruneEvent(PRUNE_SCHEMA, plan_id, fingerprint, "applied", removed, (), "")
    write_json(
        runs_dir / PRUNE_DIR / f"{plan_id}.event.json",
        {
            "bytes_removed": event.bytes_removed,
            "fingerprint": event.fingerprint,
            "plan_id": event.plan_id,
            "schema": event.schema,
            "status": event.status,
        },
    )
    return event


def _remove_tree(directory: Path) -> None:
    for child in directory.iterdir():
        if child.is_dir():
            _remove_tree(child)
        else:
            child.unlink()
    directory.rmdir()
