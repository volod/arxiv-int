"""Silo-root containment and current-hash checks for resolved locations."""

import hashlib
from pathlib import Path

from arxiv_int.interfaces.tokens import require_relative_path

_CHUNK = 65536


def location_status(root: Path | None, relative_path: str, expected_hash: str) -> str:
    """Return matching, missing, changed, escaped, or unchecked for one path."""
    if root is None:
        return "unchecked"
    require_relative_path(relative_path, "relative_path")
    candidate = root.joinpath(*relative_path.split("/"))
    if candidate.is_symlink():
        if _contained(root, candidate) is None:
            return "escaped"
        if not candidate.exists():
            return "missing"
    elif not candidate.exists():
        return "missing"
    elif _contained(root, candidate) is None:
        return "escaped"
    if not candidate.is_file():
        return "missing"
    digest = sha256_file(candidate)
    if expected_hash and digest != expected_hash:
        return "changed"
    return "matching"


def sha256_file(path: Path) -> str:
    """Hash file bytes after containment has been verified."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(root: Path, candidate: Path) -> Path | None:
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return resolved
