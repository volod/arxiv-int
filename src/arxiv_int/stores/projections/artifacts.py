"""Persist secret-free projection manifests under DATA_DIR and optional RUNS_DIR."""

import json
from pathlib import Path

from arxiv_int.stores.projections.model import ProjectionRequest, ProjectionResult
from arxiv_int.stores.projections.paths import published_manifest_dir
from arxiv_int.transformations.artifacts import sanitize_value


def write_result(artifact_dir: Path, result: ProjectionResult) -> Path:
    """Write result.json under the projection artifact directory."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / "result.json"
    payload = sanitize_value(result.as_json_dict())
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def publish_result(request: ProjectionRequest, artifact_dir: Path) -> Path | None:
    """Copy the sanitized manifest to RUNS_DIR when requested."""
    if not request.publish or request.runs_dir is None:
        return None
    destination = published_manifest_dir(request.runs_dir, request.run_id)
    destination.mkdir(parents=True, exist_ok=True)
    source = artifact_dir / "result.json"
    if source.is_file():
        (destination / "projections.json").write_bytes(source.read_bytes())
    return destination
