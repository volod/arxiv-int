"""Refuse prune of active, pinned, reviewed, rollback, ledger, backup, or sole copies."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.pipeline.persist import load_json
from arxiv_int.pipeline.prune.model import Protection
from arxiv_int.pipeline.publish.model import ACTIVE_GENERATION
from arxiv_int.pipeline.reuse_index import ReuseEntry

PIN_DIR = "pins"
REVIEW_DIR = "review"
ROLLBACK_DIR = "rollback"
LEDGER_DIR = "ledgers"
BACKUP_DIR = "backups"
MOVE_LEDGER_NAME = "move-ledger.json"


@dataclass(frozen=True, slots=True)
class _Markers:
    active_run: str
    pinned: set[Path]
    reviewed: set[Path]
    rollback: set[Path]
    ledgers: set[Path]
    backups: set[Path]
    has_live: bool


def protections(
    runs_dir: Path,
    stale: Sequence[ReuseEntry],
    live: Mapping[str, ReuseEntry],
    superseded: Sequence[ReuseEntry] = (),
) -> tuple[Protection, ...]:
    """Return every protection that blocks physical deletion."""
    markers = _markers(runs_dir, live)
    found: list[Protection] = []
    for entry in tuple(stale) + tuple(superseded):
        item = _protection_for(entry, markers)
        if item is not None:
            found.append(item)
    return tuple(found)


def _markers(runs_dir: Path, live: Mapping[str, ReuseEntry]) -> _Markers:
    live_dirs = {entry.directory for entry in live.values() if not entry.stale}
    return _Markers(
        _active_run(runs_dir),
        _marker_dirs(runs_dir / PIN_DIR) | _pin_payload_dirs(runs_dir),
        _tree_dirs(runs_dir, REVIEW_DIR),
        _tree_dirs(runs_dir, ROLLBACK_DIR),
        _tree_dirs(runs_dir, LEDGER_DIR) | _move_ledgers(runs_dir),
        _marker_dirs(runs_dir / BACKUP_DIR),
        bool(live_dirs),
    )


def _protection_for(entry: ReuseEntry, markers: _Markers) -> Protection | None:
    directory = str(Path(entry.directory))
    resolved = Path(directory).resolve()
    kind = _protection_kind(directory, resolved, markers)
    if kind is None:
        return None
    return Protection(directory, kind, _PROTECTION_DETAIL[kind])


_PROTECTION_DETAIL = {
    "active": "active generation",
    "pinned": "pinned artifact",
    "reviewed": "immutable review history",
    "rollback": "rollback copy",
    "ledger": "decision or move ledger",
    "backup": "backup copy",
    "sole-recovery": "sole recovery copy",
}


def _protection_kind(directory: str, resolved: Path, markers: _Markers) -> str | None:
    if markers.active_run and _run_id(directory) == markers.active_run:
        return "active"
    if directory in markers.pinned or resolved in markers.pinned:
        return "pinned"
    if _intersects(resolved, markers.reviewed):
        return "reviewed"
    if _intersects(resolved, markers.rollback):
        return "rollback"
    if _intersects(resolved, markers.ledgers):
        return "ledger"
    if directory in markers.backups or _intersects(resolved, markers.backups):
        return "backup"
    if not markers.has_live:
        return "sole-recovery"
    return None


def blocked_directories(rows: Sequence[Protection]) -> frozenset[str]:
    """Return directories that prune must not delete."""
    return frozenset(item.directory for item in rows)


def _active_run(runs_dir: Path) -> str:
    path = runs_dir / ACTIVE_GENERATION
    if not path.is_file():
        return ""
    payload = load_json(path)
    return str(payload.get("run_id") or "")


def _run_id(directory: str) -> str:
    parts = Path(directory).parts
    for item in parts:
        if item.startswith("run-"):
            return item
    return ""


def _marker_dirs(root: Path) -> set[Path]:
    if not root.is_dir():
        return set()
    return {path.resolve() for path in root.rglob("*") if path.is_dir() or path.is_file()}


def _pin_payload_dirs(runs_dir: Path) -> set[Path]:
    root = runs_dir / PIN_DIR
    found: set[Path] = set()
    if not root.is_dir():
        return found
    for path in root.glob("*.json"):
        payload = load_json(path)
        directory = payload.get("directory")
        if directory:
            found.add(Path(str(directory)).resolve())
    return found


def _tree_dirs(runs_dir: Path, name: str) -> set[Path]:
    found: set[Path] = set()
    for path in runs_dir.glob(f"*/{name}"):
        if path.exists():
            found.add(path.resolve())
            found.update(_marker_dirs(path))
    return found


def _move_ledgers(runs_dir: Path) -> set[Path]:
    return {path.resolve() for path in runs_dir.glob(f"*/{MOVE_LEDGER_NAME}") if path.is_file()}


def _intersects(target: Path, roots: set[Path]) -> bool:
    for root in roots:
        if target == root or _is_under(target, root) or _is_under(root, target):
            return True
    return False


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
