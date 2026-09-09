"""Adapt a sealed inventory to the existing in-memory reconciliation interface."""

import json
from pathlib import Path

from arxiv_int.pipeline.inventory.publish import validate_manifest
from arxiv_int.pipeline.reconcile.model import SiloScan, SourceManifest, SourceOccurrence
from arxiv_int.pipeline.run.persist import load_status


def load_inventory_sources(runs_dir: Path, run_id: str) -> SourceManifest | None:
    """Use verified inventory classifications rather than silently omitting links."""
    if not (runs_dir / run_id / "status.json").is_file():
        return None
    executions = load_status(runs_dir, run_id).executions
    candidates = [
        item
        for item in executions
        if item.stage == "inventory"
        and item.directory
        and item.status in {"succeeded", "quarantined"}
    ]
    if not candidates:
        return None
    selected = candidates[-1]
    stage = json.loads((Path(str(selected.directory)) / "stage.json").read_text(encoding="ascii"))
    output = stage["outputs"][0]
    partition = output["partition"]
    manifest = Path(partition["manifest"])
    summary = validate_manifest(manifest, partition["sha256"])
    scopes = summary["completed_source_set"]
    rows: dict[str, list[SourceOccurrence]] = {silo: [] for silo in scopes}
    with (manifest.parent / "partitions.jsonl").open(encoding="ascii") as index:
        for line in index:
            record = json.loads(line)
            _read_rows(manifest.parent / record["metadata"], rows)
    silos = tuple(
        SiloScan(
            silo,
            bool(scopes[silo]) and all(row.readable for row in items),
            bool(scopes[silo]),
            tuple(items),
        )
        for silo, items in rows.items()
    )
    return SourceManifest(summary["generation_id"], silos, all(s.complete for s in silos))


def _read_rows(path: Path, rows: dict[str, list[SourceOccurrence]]) -> None:
    with path.open(encoding="ascii") as handle:
        for line in handle:
            item = json.loads(line)
            if item["members"] or item["relative_path"] == ".":
                continue
            digest = item["content_hash"]
            rows[item["silo_id"]].append(
                SourceOccurrence(
                    item["silo_id"],
                    item["relative_path"],
                    digest or "unreadable",
                    bool(digest),
                    bool(digest),
                )
            )
