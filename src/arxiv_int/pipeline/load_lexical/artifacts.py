"""Lexical load manifest layout and external artifact validation."""

import json
from pathlib import Path
from typing import Any

from arxiv_int.pipeline.control.artifacts import hash_file

SCHEMA = "arxiv-int.lexical-load.v1"
DATASET = "lexical-projection"
CONTRACT_VERSION = "1.0.0"
MANIFEST_NAME = "lexical.json"
DOCUMENTS_CONTRACT = "documents"
CHUNKS_CONTRACT = "chunks"
LOADED_CONTRACTS: tuple[str, ...] = (DOCUMENTS_CONTRACT, CHUNKS_CONTRACT)


def search_root(runs_dir: Path, run_id: str) -> Path:
    """Return the run-scoped lexical evidence root under ``$RUNS_DIR``."""
    return runs_dir / run_id / "search"


def manifest_path(runs_dir: Path, run_id: str) -> Path:
    """Return the lexical load manifest for one run."""
    return search_root(runs_dir, run_id) / MANIFEST_NAME


def validate_manifest(path: Path, digest: str) -> dict[str, Any]:
    """Rehash the lexical load manifest and check its schema before reuse."""
    if path.is_symlink() or hash_file(path)[0] != digest:
        raise ValueError("lexical load manifest identity mismatch")
    summary: dict[str, Any] = json.loads(path.read_text(encoding="ascii"))
    if summary.get("schema") != SCHEMA:
        raise ValueError("unexpected lexical load manifest schema")
    return summary
