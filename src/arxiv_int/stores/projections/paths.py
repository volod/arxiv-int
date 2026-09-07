"""Tool artifact roots for projection lifecycle evidence."""

import os
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.runtime.config_schema import DEFAULTS
from arxiv_int.transformations.paths import PUBLISH_MANIFESTS

METHOD = "projections"
ACTIVE_POINTER = "active-projections.json"


def data_root(project_root: Path) -> Path:
    """Resolve DATA_DIR without embedding a machine-specific default path."""
    configured = os.environ.get("DATA_DIR", "").strip() or str(DEFAULTS["DATA_DIR"])
    root = Path(configured).expanduser()
    return root if root.is_absolute() else project_root / root


def projection_artifact_dir(project_root: Path, run_id: str | None = None) -> Path:
    """Return ``$DATA_DIR/projections/<run-id>/`` for tool evidence."""
    identifier = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return data_root(project_root) / METHOD / identifier


def lock_path(project_root: Path, version_id: str) -> Path:
    """Return the exclusive-ownership lock for one projection version."""
    return data_root(project_root) / METHOD / "locks" / f"{version_id}.lock"


def published_manifest_dir(runs_dir: Path, run_id: str) -> Path:
    """Return ``$RUNS_DIR/<run-id>/manifests/`` for sanitized projection evidence."""
    return runs_dir / run_id / PUBLISH_MANIFESTS


def export_dir(artifact_dir: Path) -> Path:
    """Return the open-export directory for graph-disabled or AGE builds."""
    return artifact_dir / "exports"
