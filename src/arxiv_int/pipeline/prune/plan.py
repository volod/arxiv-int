"""Dry-run stale prune planning with a stable fingerprint."""

from pathlib import Path
from uuid import uuid4

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.pipeline.prune.model import PRUNE_SCHEMA, PrunePlan
from arxiv_int.pipeline.prune.protect import blocked_directories, protections
from arxiv_int.pipeline.run.persist import write_json
from arxiv_int.pipeline.run.reuse_index import ReuseEntry, load_reuse_index, load_superseded

PRUNE_DIR = "prune-plans"


def build_prune_plan(runs_dir: Path) -> PrunePlan:
    """List stale derived attempts; apply deletes only non-blocked eligible rows."""
    index = load_reuse_index(runs_dir)
    superseded = load_superseded(runs_dir)
    live = {key: entry for key, entry in index.items() if not entry.stale}
    stale = tuple(entry for entry in index.values() if entry.stale) + superseded
    blocked = protections(runs_dir, stale, live, superseded)
    blocked_dirs = blocked_directories(blocked)
    eligible = tuple(entry for entry in stale if entry.directory not in blocked_dirs)
    plan_id = f"prune-{uuid4().hex}"
    fingerprint = fingerprint_for(eligible)
    plan = PrunePlan(
        PRUNE_SCHEMA,
        plan_id,
        fingerprint,
        stale,
        eligible,
        sum(entry.bytes for entry in stale),
        blocked,
    )
    payload = {
        "blocked": [
            {"detail": item.detail, "directory": item.directory, "kind": item.kind}
            for item in plan.blocked
        ],
        "bytes": plan.bytes,
        "directories": [entry.directory for entry in eligible],
        "fingerprint": fingerprint,
        "plan_id": plan_id,
        "schema": PRUNE_SCHEMA,
    }
    write_json(runs_dir / PRUNE_DIR / f"{plan_id}.json", payload)
    _write_run_copy(runs_dir, plan_id, payload)
    return plan


def fingerprint_for(entries: tuple[ReuseEntry, ...]) -> str:
    """Hash eligible directories and bytes so apply can refuse a stale plan."""
    payload = {
        "bytes": sum(entry.bytes for entry in entries),
        "directories": sorted(entry.directory for entry in entries),
    }
    return sha256_text(normalize_json(payload))


def _write_run_copy(runs_dir: Path, plan_id: str, payload: dict[str, object]) -> None:
    runs = list(runs_dir.glob("run-*/run-context.json"))
    if not runs:
        return
    latest = max(runs, key=lambda path: path.stat().st_mtime).parent
    write_json(latest / "prune" / f"{plan_id}.json", payload)
