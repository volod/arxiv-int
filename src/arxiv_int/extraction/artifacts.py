"""Extraction artifact identities, summaries, and external checksum validation."""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO, TypedDict

from arxiv_int.extraction.model import InventoryInput
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.pipeline.lake.artifacts import (
    abort_publication,
    record_file,
    snapshot_suffix,
    validate_snapshot_manifest,
    write_json_line,
)

__all__ = [
    "DocumentQuality",
    "abort_publication",
    "document_quality",
    "extraction_summary",
    "final_roots",
    "record_file",
    "span_id",
    "validate_manifest",
    "write_json_line",
    "write_occurrence",
    "write_quarantine",
]


class DocumentQuality(TypedDict):
    """Content-free extraction quality counters."""

    text_chars: int
    anchor_count: int
    anchored_chars: int
    anchor_coverage: float
    table_cells: int


def write_occurrence(handle: TextIO, item: InventoryInput, document_id: str, reused: bool) -> None:
    """Write one physical-to-content occurrence mapping."""
    write_json_line(
        handle,
        {
            "occurrence_id": item.occurrence_id,
            "document_id": document_id,
            "silo_id": item.silo_id,
            "relative_path": item.relative_path,
            "member_path": list(item.members),
            "reused_content": reused,
        },
    )


def write_quarantine(handle: TextIO, item: InventoryInput, reason: str, detail: str) -> None:
    """Write one actionable source failure without absolute paths."""
    write_json_line(
        handle,
        {
            "occurrence_id": item.occurrence_id,
            "silo_id": item.silo_id,
            "relative_path": item.relative_path,
            "member_path": list(item.members),
            "content_hash": item.content_hash,
            "media_type": item.media_type,
            "reason": reason,
            "detail": detail[:2000],
        },
    )


def extraction_summary(
    generation: str,
    roots: Mapping[str, Path],
    counts: Mapping[str, int],
    formats: Mapping[str, Mapping[str, int]],
    coverage: Mapping[str, int],
    catalog_fingerprint: str,
    files_sha256: str,
) -> dict[str, object]:
    """Build the content-free extraction manifest summary."""
    return {
        "schema": "arxiv-int.tiered-extraction.v1",
        "generation_id": generation,
        "contracts": {"documents": "1.0.0", "spans": "1.0.0"},
        "roots": {name: str(path) for name, path in roots.items()},
        **counts,
        "formats": {
            media_type: dict(sorted(values.items()))
            for media_type, values in sorted(formats.items())
        },
        "coverage": dict(coverage),
        "pandera": {"status": "pass", "catalog_fingerprint": catalog_fingerprint},
        "files_sha256": files_sha256,
    }


def validate_manifest(path: Path, digest: str) -> dict[str, Any]:
    """Rehash every extraction artifact before reuse."""
    return validate_snapshot_manifest(path, digest, label="extraction")


def final_roots(results: Path, generation: str, snapshot: str) -> dict[str, Path]:
    """Return immutable configured product roots for one extraction snapshot."""
    suffix = snapshot_suffix(generation, snapshot)
    return {
        "documents": results / "normalized/documents" / suffix,
        "spans": results / "normalized/spans" / suffix,
        "quarantine": results / "quarantine/extract" / suffix,
        "manifest": results / "normalized/extraction" / suffix,
    }


def document_quality(document: ExtractedDocument) -> DocumentQuality:
    """Summarize anchored text and table coverage without source content."""
    anchored = sum(
        anchor.end_char - anchor.start_char
        for anchor in document.anchors
        if anchor.start_char is not None and anchor.end_char is not None
    )
    return {
        "text_chars": len(document.text),
        "anchor_count": len(document.anchors),
        "anchored_chars": anchored,
        "anchor_coverage": min(1.0, anchored / max(1, len(document.text))),
        "table_cells": sum(anchor.is_cell for anchor in document.anchors),
    }


def span_id(document_id: str, index: int, start: int | None, end: int | None, kind: str) -> str:
    """Derive a stable span id from content identity and coordinates."""
    value = json.dumps([document_id, index, start, end, kind], ensure_ascii=True)
    return hashlib.sha256(value.encode("ascii")).hexdigest()
