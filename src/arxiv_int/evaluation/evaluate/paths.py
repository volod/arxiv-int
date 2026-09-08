"""Artifact roots for evaluate runs, fixture catalogs, and proof bundles."""

import os
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.resources.paths import configs_root
from arxiv_int.runtime.config_schema import DEFAULTS

EVALUATION_METHOD = "evaluation"
PROOF_METHOD = "proofs"
FIXTURE_RELATIVE = Path("tests") / "fixtures" / "evaluation"


def data_root(project_root: Path) -> Path:
    """Resolve DATA_DIR without embedding a machine-specific default path."""
    configured = os.environ.get("DATA_DIR", "").strip() or str(DEFAULTS["DATA_DIR"])
    root = Path(configured).expanduser()
    return root if root.is_absolute() else project_root / root


def evaluation_artifact_dir(project_root: Path, run_id: str | None = None) -> Path:
    """Return ``$DATA_DIR/evaluation/<run-id>/`` for tool evidence."""
    identifier = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return data_root(project_root) / EVALUATION_METHOD / identifier


def published_evaluation_dir(runs_dir: Path, run_id: str) -> Path:
    """Return ``$RUNS_DIR/<run-id>/evaluation/`` for the immutable run bundle."""
    return runs_dir / run_id / EVALUATION_METHOD


def published_proof_dir(results_dir: Path, capability: str, proof_id: str) -> Path:
    """Return ``$RESULTS_DIR/proofs/<capability>/<proof-id>/``."""
    return results_dir / PROOF_METHOD / capability / proof_id


def fixture_root(project_root: Path) -> Path:
    """Return the committed frozen-fixture directory."""
    return project_root / FIXTURE_RELATIVE


def proof_config_path(project_root: Path) -> Path:
    """Return the committed capability-to-validator registry."""
    return configs_root(project_root) / "proofs" / "capabilities.json"


def threshold_config_path(project_root: Path) -> Path:
    """Return committed metric threshold configuration."""
    return configs_root(project_root) / "evaluation" / "thresholds.json"
