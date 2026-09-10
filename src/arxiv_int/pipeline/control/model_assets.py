"""Content identities for local extraction models, without loading inference engines."""

import hashlib
import json
from pathlib import Path

from arxiv_int.pipeline.control.artifacts import hash_file


def docling_asset_fingerprint(cache: Path) -> str:
    """Hash names and bytes on each lookup so an in-place refresh cannot reuse old text."""
    root = cache / "docling"
    files: dict[str, str] = {}
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                files[path.relative_to(root).as_posix()] = hash_file(path)[0]
    payload = {"available": root.is_dir(), "files": files}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("ascii")).hexdigest()
