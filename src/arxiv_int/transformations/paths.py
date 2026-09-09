"""Tool artifact roots for dbt runs."""

import os
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.resources.paths import contracts_root, dbt_project_root
from arxiv_int.runtime.config_schema import DEFAULTS

METHOD = "dbt"
PROJECT_DIRNAME = "dbt"
GENERATED_SOURCES = Path("generated") / "dbt" / "sources.yml"
ACTIVE_POINTER = "active-generation.json"
PUBLISH_MANIFESTS = "manifests"
PUBLISH_QUALITY = "quality"


def data_root(project_root: Path) -> Path:
    """Resolve DATA_DIR without embedding a machine-specific default path."""
    configured = os.environ.get("DATA_DIR", "").strip() or str(DEFAULTS["DATA_DIR"])
    root = Path(configured).expanduser()
    return root if root.is_absolute() else project_root / root


def dbt_artifact_dir(project_root: Path, run_id: str | None = None) -> Path:
    """Return `$DATA_DIR/dbt/<run-id>/` for tool evidence."""
    identifier = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return data_root(project_root) / METHOD / identifier


def authored_project_dir(project_root: Path) -> Path:
    """Return the packaged dbt project, or an overlay under ``project_root``."""
    return dbt_project_root(project_root)


def generated_sources_path(project_root: Path) -> Path:
    """Return the contract-generated combined sources YAML."""
    return contracts_root(project_root) / GENERATED_SOURCES


def working_project_dir(artifact_dir: Path) -> Path:
    """Return the isolated working copy of the dbt project."""
    return artifact_dir / "project"


def profiles_dir(artifact_dir: Path) -> Path:
    """Return the profiles directory that holds env_var-only credentials."""
    return artifact_dir / "profiles"


def lock_path(project_root: Path, generation_id: str) -> Path:
    """Return the exclusive-ownership lock for one derived generation."""
    return data_root(project_root) / METHOD / "locks" / f"{generation_id}.lock"


def active_pointer_path(project_root: Path) -> Path:
    """Return the local active-generation pointer under DATA_DIR."""
    return data_root(project_root) / METHOD / ACTIVE_POINTER


def published_manifest_dir(runs_dir: Path, run_id: str) -> Path:
    """Return `$RUNS_DIR/<run-id>/manifests/` for sanitized dbt evidence."""
    return runs_dir / run_id / PUBLISH_MANIFESTS


def published_quality_dir(runs_dir: Path, run_id: str) -> Path:
    """Return `$RUNS_DIR/<run-id>/quality/` for dbt rule outcomes."""
    return runs_dir / run_id / PUBLISH_QUALITY
