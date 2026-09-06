"""Verified-work fingerprints reused across setup retries."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.runtime.setup.model import PhaseName


@dataclass(frozen=True, slots=True)
class VerifiedPhase:
    """Last successful fingerprint for one phase."""

    name: str
    fingerprint: str


def fingerprint_for(*parts: str) -> str:
    """Return a short stable digest of the supplied identity parts."""
    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]


def state_path(data_dir: Path) -> Path:
    """Return `$DATA_DIR/setup/verified.json`."""
    return data_dir / "setup" / "verified.json"


def load_verified(data_dir: Path) -> dict[str, str]:
    """Load previously verified phase fingerprints, or an empty map."""
    path = state_path(data_dir)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    phases = payload.get("phases") if isinstance(payload, dict) else None
    if not isinstance(phases, dict):
        return {}
    return {str(name): str(value) for name, value in phases.items() if value}


def store_verified(data_dir: Path, phases: dict[str, str]) -> None:
    """Persist successful fingerprints without secrets."""
    path = state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"phases": phases}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def matches(verified: dict[str, str], name: PhaseName, fingerprint: str) -> bool:
    """Return whether a phase can be reused for the current fingerprint."""
    return bool(fingerprint) and verified.get(name) == fingerprint
