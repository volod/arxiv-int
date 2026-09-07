"""Normalize generated text and compute stable fingerprints."""

import hashlib
import json
from typing import Any


def normalize_text(content: str) -> str:
    """Normalize newlines and trailing whitespace for byte-stable artifacts."""
    lines = [line.rstrip() for line in content.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def normalize_json(document: Any) -> str:
    """Return canonical JSON with sorted keys."""
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(content: str) -> str:
    """Return the SHA-256 hex digest of normalized UTF-8 text."""
    return hashlib.sha256(normalize_text(content).encode("utf-8")).hexdigest()
