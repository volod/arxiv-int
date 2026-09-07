"""Declared local model identities and capabilities under configs/models."""

import json
from pathlib import Path

from arxiv_int.inference.types import KNOWN_CAPABILITIES, ModelIdentity

REGISTRY_PATH = Path("configs") / "models" / "registry.json"


def load_profiles(project_root: Path) -> tuple[ModelIdentity, ...]:
    """Load optional registry identities; unknown live models still work via discovery."""
    path = project_root / REGISTRY_PATH
    if not path.is_file():
        return ()
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("models"), list):
        raise ValueError("configs/models/registry.json must contain a models array")
    return tuple(_parse_profile(item) for item in document["models"])


def _parse_profile(item: object) -> ModelIdentity:
    if not isinstance(item, dict):
        raise ValueError("each model profile must be an object")
    model_id = item.get("id")
    backend = item.get("backend")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("model profile is missing id")
    if backend not in {"ollama", "vllm"}:
        raise ValueError(f"model profile {model_id!r} has unsupported backend")
    raw = item.get("capabilities", [])
    if not isinstance(raw, list):
        raise ValueError(f"model profile {model_id!r} capabilities must be an array")
    capabilities = frozenset(str(value) for value in raw)
    unknown = capabilities - KNOWN_CAPABILITIES
    if unknown:
        raise ValueError(f"model profile {model_id!r} has unknown capabilities")
    digest = item.get("revision") or item.get("digest") or ""
    if not isinstance(digest, str):
        digest = ""
    return ModelIdentity(
        model_id=model_id,
        digest=digest,
        backend=backend,
        capabilities=capabilities,
        detail="registry",
    )


def profile_for(
    profiles: tuple[ModelIdentity, ...], backend: str, model_id: str
) -> ModelIdentity | None:
    """Return a registry profile matching backend and model id."""
    for profile in profiles:
        if profile.backend == backend and profile.model_id == model_id:
            return profile
    return None
