"""Tool artifact roots for data-quality runs."""

import os
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.runtime.config_schema import DEFAULTS

METHOD = "data-quality"
PUBLISH_CHILD = "quality"


def data_root(project_root: Path) -> Path:
    """Resolve DATA_DIR without embedding a machine-specific default path."""
    configured = os.environ.get("DATA_DIR", "").strip() or str(DEFAULTS["DATA_DIR"])
    root = Path(configured).expanduser()
    return root if root.is_absolute() else project_root / root


def quality_artifact_dir(project_root: Path, run_id: str | None = None) -> Path:
    """Return `$DATA_DIR/data-quality/<run-id>/` for tool evidence."""
    identifier = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return data_root(project_root) / METHOD / identifier


def published_quality_dir(runs_dir: Path, run_id: str) -> Path:
    """Return `$RUNS_DIR/<run-id>/quality/` for sanitized published evidence."""
    return runs_dir / run_id / PUBLISH_CHILD
