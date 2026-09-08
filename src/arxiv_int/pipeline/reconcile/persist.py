"""Write delta, invalidation, rebuild, and tombstone artifacts under a run."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.pipeline.reconcile.model import (
    DELTA_SCHEMA,
    INVALIDATION_SCHEMA,
    MANIFEST_SCHEMA,
    REBUILD_SCHEMA,
    TOMBSTONE_SCHEMA,
    InvalidationPlan,
    RebuildReport,
    SiloScan,
    SourceDelta,
    SourceManifest,
    SourceOccurrence,
    Tombstone,
)
from arxiv_int.pipeline.run.persist import StageExecution, load_json, run_dir, write_json

DELTA_DIR = "delta"
INVALIDATION_DIR = "invalidation"
REBUILD_DIR = "rebuild"


def load_manifest(runs_dir: Path, run_id: str) -> SourceManifest | None:
    """Load a previously written source manifest, if present."""
    path = run_dir(runs_dir, run_id) / DELTA_DIR / "manifest.json"
    if not path.is_file():
        return None
    payload = load_json(path)
    silos = []
    for item in payload.get("silos", ()):
        occurrences = tuple(
            SourceOccurrence(
                str(occ["silo_id"]),
                str(occ["relative_path"]),
                str(occ["content_hash"]),
                bool(occ.get("stable", True)),
                bool(occ.get("readable", True)),
                str(occ.get("container_path", "")),
                str(occ.get("member_path", "")),
            )
            for occ in item.get("occurrences", ())
        )
        silos.append(
            SiloScan(
                str(item["silo_id"]),
                bool(item.get("complete", False)),
                bool(item.get("readable", False)),
                occurrences,
                str(item.get("reason", "")),
            )
        )
    return SourceManifest(
        str(payload["scan_id"]),
        tuple(silos),
        bool(payload.get("comparable", False)),
        str(payload.get("schema", MANIFEST_SCHEMA)),
    )


def write_manifest(runs_dir: Path, run_id: str, manifest: SourceManifest) -> Path:
    """Persist the comparable source manifest next to the delta."""
    payload = {
        "comparable": manifest.comparable,
        "scan_id": manifest.scan_id,
        "schema": MANIFEST_SCHEMA,
        "silos": [_silo_payload(silo) for silo in manifest.silos],
    }
    path = run_dir(runs_dir, run_id) / DELTA_DIR / "manifest.json"
    write_json(path, payload)
    return path


def write_delta(runs_dir: Path, run_id: str, delta: SourceDelta) -> Path:
    """Persist add/change/rename/remove events for one update."""
    payload = {
        "comparable": delta.comparable,
        "current_scan_id": delta.current_scan_id,
        "events": [_event_payload(event) for event in delta.events],
        "previous_scan_id": delta.previous_scan_id,
        "schema": DELTA_SCHEMA,
        "withheld_removals": list(delta.withheld_removals),
    }
    path = run_dir(runs_dir, run_id) / DELTA_DIR / "delta.json"
    write_json(path, payload)
    return path


def write_tombstones(runs_dir: Path, run_id: str, rows: Sequence[Tombstone]) -> Path:
    """Persist removal tombstones without deleting archive sources."""
    payload = {
        "schema": TOMBSTONE_SCHEMA,
        "tombstones": [_tombstone_payload(row) for row in rows],
    }
    path = run_dir(runs_dir, run_id) / DELTA_DIR / "tombstones.json"
    write_json(path, payload)
    return path


def write_invalidation(runs_dir: Path, run_id: str, plan: InvalidationPlan) -> Path:
    """Persist the logical stale closure and recomputation estimate."""
    payload = {
        "bytes": plan.bytes,
        "document_id": plan.document_id,
        "marked": list(plan.marked),
        "recompute_shards": plan.recompute_shards,
        "roots": list(plan.roots),
        "schema": INVALIDATION_SCHEMA,
        "stage": plan.stage,
    }
    path = run_dir(runs_dir, run_id) / INVALIDATION_DIR / "plan.json"
    write_json(path, payload)
    return path


def comparable_checksums(executions: Sequence[StageExecution]) -> dict[str, str]:
    """Hash stage payloads after stripping generation tokens."""
    checksums: dict[str, str] = {}
    for item in executions:
        if not item.directory:
            continue
        payload = json.loads(
            Path(item.directory).joinpath("stage.json").read_text(encoding="utf-8")
        )
        outputs: list[Any] = []
        for row in payload.get("outputs", ()):
            if isinstance(row, dict):
                cleaned = dict(row)
                cleaned.pop("generationId", None)
                outputs.append(cleaned)
            else:
                outputs.append(row)
        comparable = {
            "detail": payload.get("detail"),
            "outcome": payload.get("outcome"),
            "outputs": outputs,
            "stage": payload.get("stage"),
        }
        checksums[f"{item.stage}:{item.shard_id}"] = sha256_text(normalize_json(comparable))
    return checksums


def write_rebuild(runs_dir: Path, run_id: str, report: RebuildReport) -> Path:
    """Persist isolated-generation rebuild evidence."""
    payload = {
        "activated": report.activated,
        "baseline_match": report.baseline_match,
        "checksums": dict(report.checksums),
        "generation_id": report.generation_id,
        "previous_generation_id": report.previous_generation_id,
        "quality_allowed": report.quality_allowed,
        "run_id": report.run_id,
        "schema": REBUILD_SCHEMA,
    }
    path = run_dir(runs_dir, run_id) / REBUILD_DIR / "report.json"
    write_json(path, payload)
    return path


def _silo_payload(silo: Any) -> dict[str, Any]:
    return {
        "complete": silo.complete,
        "occurrences": [
            {
                "content_hash": item.content_hash,
                "container_path": item.container_path,
                "member_path": item.member_path,
                "readable": item.readable,
                "relative_path": item.relative_path,
                "silo_id": item.silo_id,
                "stable": item.stable,
            }
            for item in silo.occurrences
        ],
        "readable": silo.readable,
        "reason": silo.reason,
        "silo_id": silo.silo_id,
    }


def _event_payload(event: Any) -> dict[str, str]:
    return {
        "content_hash": event.content_hash,
        "kind": event.kind,
        "previous_hash": event.previous_hash,
        "previous_path": event.previous_path,
        "relative_path": event.relative_path,
        "silo_id": event.silo_id,
    }


def _tombstone_payload(row: Tombstone) -> Mapping[str, object]:
    return {
        "content_hash": row.content_hash,
        "generation_id": row.generation_id,
        "last_occurrence": row.last_occurrence,
        "occurrence_id": row.occurrence_id,
        "reason": row.reason,
        "relative_path": row.relative_path,
        "scan_id": row.scan_id,
        "schema": row.schema,
        "silo_id": row.silo_id,
    }
