"""Extraction artifact identities, summaries, and external checksum validation."""

import hashlib
import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO, TypedDict

from arxiv_int.extraction.model import InventoryInput
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.pipeline.control.artifacts import hash_file


class DocumentQuality(TypedDict):
    """Content-free extraction quality counters."""

    text_chars: int
    anchor_count: int
    anchored_chars: int
    anchor_coverage: float
    table_cells: int


def abort_publication(
    staging: Path, handles: tuple[TextIO, ...], moved: list[Path], sealed: bool
) -> None:
    """Remove unpublished scratch and any roots moved before a failed seal."""
    for handle in handles:
        if not handle.closed:
            handle.close()
    shutil.rmtree(staging, ignore_errors=True)
    if not sealed:
        for path in moved:
            shutil.rmtree(path, ignore_errors=True)


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
    if path.is_symlink() or hash_file(path)[0] != digest:
        raise ValueError("extraction manifest identity mismatch")
    summary: dict[str, Any] = json.loads(path.read_text(encoding="ascii"))
    index = path.parent / "files.jsonl"
    if index.is_symlink() or hash_file(index)[0] != summary["files_sha256"]:
        raise ValueError("extraction file index mismatch")
    roots = {name: Path(value) for name, value in summary["roots"].items()}
    with index.open(encoding="ascii") as handle:
        for line in handle:
            record = json.loads(line)
            relative = Path(record["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("invalid extraction artifact path")
            artifact = roots[record["kind"]] / relative
            if artifact.is_symlink() or hash_file(artifact)[0] != record["sha256"]:
                raise ValueError("extraction artifact checksum mismatch")
    return summary


def final_roots(results: Path, generation: str, snapshot: str) -> dict[str, Path]:
    """Return immutable configured product roots for one extraction snapshot."""
    suffix = Path("contract_version=1.0.0") / f"generation_id={generation}" / f"snapshot={snapshot}"
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


def write_json_line(handle: TextIO, value: dict[str, object]) -> None:
    """Write one deterministic ASCII JSON line."""
    handle.write(json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n")


def record_file(handle: TextIO, kind: str, path: Path, root: Path) -> None:
    """Append one rooted artifact checksum to a streamed file index."""
    write_json_line(
        handle,
        {"kind": kind, "path": str(path.relative_to(root)), "sha256": hash_file(path)[0]},
    )
