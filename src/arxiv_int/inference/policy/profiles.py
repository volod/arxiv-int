"""Declared local model identities, capabilities, and resource footprints."""

import json
from pathlib import Path

from arxiv_int.inference.client.types import KNOWN_CAPABILITIES, ModelIdentity
from arxiv_int.inference.policy.footprint import ModelFootprint, footprint_from_mapping
from arxiv_int.resources.paths import configs_root


def load_profiles(project_root: Path) -> tuple[ModelIdentity, ...]:
    """Load optional registry identities; unknown live models still work via discovery."""
    return tuple(identity for identity, _footprint in _load_registry(project_root))


def load_footprints(project_root: Path) -> dict[tuple[str, str], ModelFootprint]:
    """Load declared GPU/RAM envelopes keyed by backend and model id."""
    footprints: dict[tuple[str, str], ModelFootprint] = {}
    for identity, footprint in _load_registry(project_root):
        if footprint is not None:
            footprints[(identity.backend, identity.model_id)] = footprint
    return footprints


def profile_for(
    profiles: tuple[ModelIdentity, ...], backend: str, model_id: str
) -> ModelIdentity | None:
    """Return a registry profile matching backend and model id."""
    for profile in profiles:
        if profile.backend == backend and profile.model_id == model_id:
            return profile
    return None


def _load_registry(project_root: Path) -> tuple[tuple[ModelIdentity, ModelFootprint | None], ...]:
    path = configs_root(project_root) / "models" / "registry.json"
    if not path.is_file():
        return ()
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("models"), list):
        raise ValueError("configs/models/registry.json must contain a models array")
    return tuple(_parse_entry(item) for item in document["models"])


def _parse_entry(item: object) -> tuple[ModelIdentity, ModelFootprint | None]:
    if not isinstance(item, dict):
        raise ValueError("each model profile must be an object")
    identity = _parse_identity(item)
    raw_footprint = item.get("footprint")
    footprint = footprint_from_mapping(raw_footprint) if raw_footprint is not None else None
    return identity, footprint


def _parse_identity(item: dict[str, object]) -> ModelIdentity:
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
