"""Persist secret-free transform results and publish sanitized evidence."""

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.transformations.artifacts import input_fingerprint, write_sanitized_json
from arxiv_int.transformations.model import TransformRequest, TransformResult
from arxiv_int.transformations.paths import published_manifest_dir, published_quality_dir


def build_result(
    request: TransformRequest,
    *,
    status: str,
    detail: str,
    generation_id: str,
    artifact_dir: Path,
    activatable: bool = False,
    model_fp: str = "",
    rules: tuple[Mapping[str, Any], ...] = (),
    relations: tuple[str, ...] = (),
    counts: Mapping[str, int] | None = None,
    published: Path | None = None,
    quality: Path | None = None,
) -> TransformResult:
    """Assemble one secret-free TransformResult."""
    return TransformResult(
        status=status,
        command=request.command,
        run_id=request.run_id,
        generation_id=generation_id,
        activatable=activatable,
        detail=detail,
        artifact_dir=str(artifact_dir),
        selected=request.select,
        input_fingerprint=input_fingerprint(
            command=request.command,
            generation_id=generation_id,
            policy_version=request.policy_version,
            select=request.select,
            full_refresh=request.full_refresh,
        ),
        model_fingerprint=model_fp,
        rule_outcomes=rules,
        relation_names=relations,
        row_counts=dict(counts or {}),
        published_manifest_dir=str(published) if published else None,
        published_quality_dir=str(quality) if quality else None,
    )


def write_result(artifact_dir: Path, result: TransformResult) -> Path:
    """Write result.json under the dbt artifact directory."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / "result.json"
    path.write_text(
        json.dumps(result.as_json_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def publish_result(
    request: TransformRequest, artifact_dir: Path
) -> tuple[Path | None, Path | None]:
    """Copy sanitized manifests and quality JSON to RUNS_DIR when requested."""
    if not request.publish or request.runs_dir is None:
        return None, None
    manifests = published_manifest_dir(request.runs_dir, request.run_id)
    quality = published_quality_dir(request.runs_dir, request.run_id)
    for name in ("manifest.json", "run_results.json"):
        source = artifact_dir / "manifests" / name
        if source.is_file():
            manifests.mkdir(parents=True, exist_ok=True)
            (manifests / name).write_bytes(source.read_bytes())
    result_path = artifact_dir / "result.json"
    if result_path.is_file():
        quality.mkdir(parents=True, exist_ok=True)
        (quality / "result.json").write_bytes(result_path.read_bytes())
    return manifests, quality


def sanitize_target(artifact_dir: Path) -> None:
    """Copy sanitized manifest and run-results next to other run evidence."""
    target = artifact_dir / "target"
    manifests = artifact_dir / "manifests"
    for name in ("manifest.json", "run_results.json"):
        write_sanitized_json(target / name, manifests / name)


def vars_payload(request: TransformRequest, generation_id: str) -> str:
    """Render dbt --vars JSON for one isolated generation."""
    payload = {
        "generation_id": generation_id,
        "policy_version": request.policy_version,
        "fail_tests": "true" if request.fail_tests else "false",
        "derived_schema": "derived",
        "reconcile_deletes": True,
        **dict(request.vars),
    }
    return json.dumps(payload)


def clear_execution_artifacts(artifact_dir: Path) -> None:
    """Remove prior invocation artifacts so missing current evidence cannot reuse them."""
    for directory in (artifact_dir / "target", artifact_dir / "manifests"):
        if directory.exists():
            shutil.rmtree(directory)
