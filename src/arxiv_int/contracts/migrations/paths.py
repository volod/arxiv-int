"""Locations of the owned Alembic script directory and its review manifests."""

import os
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.runtime.config_schema import DEFAULTS

MIGRATION_METHOD = "migrations"

SCRIPT_PACKAGE = "arxiv_int/migrations"
VERSIONS_DIRNAME = "versions"
HEAD_STATE_FILENAME = "head_state.json"
REVISION_MANIFEST_FILENAME = "revision_manifest.json"


def script_location(project_root: Path) -> Path:
    """Return the Alembic script directory shipped inside the package."""
    return project_root / "src" / SCRIPT_PACKAGE


def versions_dir(project_root: Path) -> Path:
    """Return the immutable revision directory."""
    return script_location(project_root) / VERSIONS_DIRNAME


def head_state_path(project_root: Path) -> Path:
    """Return the frozen owned-schema state produced by the revision history."""
    return script_location(project_root) / HEAD_STATE_FILENAME


def revision_manifest_path(project_root: Path) -> Path:
    """Return the revision checksum manifest that keeps applied revisions immutable."""
    return script_location(project_root) / REVISION_MANIFEST_FILENAME


def data_root(project_root: Path) -> Path:
    """Resolve the tool artifact root from DATA_DIR without machine-specific paths."""
    configured = os.environ.get("DATA_DIR", "").strip() or str(DEFAULTS["DATA_DIR"])
    root = Path(configured).expanduser()
    return root if root.is_absolute() else project_root / root


def migration_artifact_dir(project_root: Path, run_id: str | None = None) -> Path:
    """Return `$DATA_DIR/migrations/<run-id>/` for offline review artifacts."""
    identifier = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return data_root(project_root) / MIGRATION_METHOD / identifier
