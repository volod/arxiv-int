"""Tool artifact roots for Git-bound proof export diagnostics."""

import os
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.runtime.config_schema import DEFAULTS

METHOD = "proof-export"


def data_root(project_root: Path) -> Path:
    """Resolve DATA_DIR without embedding a machine-specific default path."""
    configured = os.environ.get("DATA_DIR", "").strip() or str(DEFAULTS["DATA_DIR"])
    root = Path(configured).expanduser()
    return root if root.is_absolute() else project_root / root


def export_artifact_dir(project_root: Path, run_id: str | None = None) -> Path:
    """Return `$DATA_DIR/proof-export/<run-id>/` for local maps and receipts."""
    identifier = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return data_root(project_root) / METHOD / identifier
