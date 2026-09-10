"""Normalization snapshot layout and external artifact validation."""

from pathlib import Path
from typing import Any

from arxiv_int.pipeline.lake.artifacts import validate_snapshot_manifest

SCHEMA = "arxiv-int.text-normalization.v1"
CONTRACT = "normalized-documents"
DOCUMENTS_KIND = "normalized-documents"
QUARANTINE_KIND = "quarantine"
MANIFEST_KIND = "manifest"

LAYOUT: dict[str, str] = {
    DOCUMENTS_KIND: "normalized/normalized-documents",
    QUARANTINE_KIND: "quarantine/normalize",
    MANIFEST_KIND: "normalized/normalization",
}
DATASETS: dict[str, str] = {CONTRACT: DOCUMENTS_KIND}
VIEW_DIRECTORIES: tuple[str, ...] = ("canonical", "search", "offsets")


def validate_manifest(path: Path, digest: str) -> dict[str, Any]:
    """Rehash every normalization artifact before reuse."""
    return validate_snapshot_manifest(path, digest, label="normalization")


def view_path(root: Path, view: str, normalized_document_id: str) -> Path:
    """Return the per-document path of one derived normalization view."""
    suffix = "json" if view == "offsets" else "txt"
    return root / view / f"{normalized_document_id}.{suffix}"
