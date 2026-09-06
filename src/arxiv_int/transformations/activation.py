"""Activate a successful derived generation without mutating canonical rows."""

import json
from pathlib import Path

from arxiv_int.transformations.model import TransformResult
from arxiv_int.transformations.paths import active_pointer_path


class ActivationRefusedError(RuntimeError):
    """Raised when a failed or incomplete build tries to become active."""


def load_active_generation(project_root: Path) -> dict[str, object] | None:
    """Return the current active-generation pointer, if any."""
    path = active_pointer_path(project_root)
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def activate_generation(project_root: Path, result: TransformResult) -> Path:
    """Write the active pointer only after tests passed and relations exist."""
    if not result.activatable or result.status != "ok":
        raise ActivationRefusedError(
            "refusing to activate a generation that is not activatable: "
            f"status={result.status} activatable={result.activatable}"
        )
    path = active_pointer_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifactDir": result.artifact_dir,
        "generationId": result.generation_id,
        "inputFingerprint": result.input_fingerprint,
        "modelFingerprint": result.model_fingerprint,
        "relationNames": list(result.relation_names),
        "runId": result.run_id,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
