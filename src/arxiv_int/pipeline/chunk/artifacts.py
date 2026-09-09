"""Chunk snapshot layout and external artifact validation."""

from pathlib import Path
from typing import Any

from arxiv_int.pipeline.lake.artifacts import validate_snapshot_manifest

SCHEMA = "arxiv-int.text-chunking.v1"
CONTRACT = "chunks"
CHUNKS_KIND = "chunks"
QUARANTINE_KIND = "quarantine"
MANIFEST_KIND = "manifest"

LAYOUT: dict[str, str] = {
    CHUNKS_KIND: "normalized/chunks",
    QUARANTINE_KIND: "quarantine/chunk",
    MANIFEST_KIND: "normalized/chunking",
}
DATASETS: dict[str, str] = {CONTRACT: CHUNKS_KIND}


def validate_manifest(path: Path, digest: str) -> dict[str, Any]:
    """Rehash every chunk artifact before reuse."""
    return validate_snapshot_manifest(path, digest, label="chunking")
