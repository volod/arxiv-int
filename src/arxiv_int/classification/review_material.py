"""Read sealed mapping rows and bounded normalized previews for human labeling."""

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path
from typing import Any

from arxiv_int.classification.artifacts import validate_manifest
from arxiv_int.pipeline.lake.artifacts import batch_sidecar, validate_snapshot_manifest
from arxiv_int.pipeline.normalize.artifacts import view_path

PREVIEW_CHARS = 500


def _rows(root: Path, identity: str) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    parquet = import_module("pyarrow.parquet")
    for path in sorted(root.glob("part-*.parquet")):
        sidecar = batch_sidecar(path, identity)
        observed: set[str] = set()
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=256):
            for row in batch.to_pylist():
                key = str(row[identity])
                if key not in sidecar or key in observed:
                    raise ValueError("mapping metadata sidecar does not match Parquet rows")
                observed.add(key)
                yield row, sidecar[key]
        if observed != set(sidecar):
            raise ValueError("mapping metadata sidecar contains unmatched rows")


def load_review_material(
    manifest: Path, digest: str
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], dict[str, Any]]], dict[str, str]]:
    """Validate the immutable mapping and its normalization source before review."""
    summary = validate_manifest(manifest, digest)
    mapping = list(_rows(Path(summary["roots"]["file-classifications"]), "classification_id"))
    if len(mapping) != summary["accounting"]["classified_rows"]:
        raise ValueError("mapping rows do not match the sealed classification count")
    pointer = summary["upstream"]["normalization"]
    normalized = validate_snapshot_manifest(
        Path(pointer["manifest"]), pointer["sha256"], label="normalize"
    )
    views = Path(normalized["roots"]["normalized-documents"])
    document_views = {
        row["document_id"]: str(view_path(views, "search", row["normalized_document_id"]))
        for row, _ in _rows(views, "normalized_document_id")
    }
    return summary, mapping, document_views


def review_order(
    mapping: list[tuple[dict[str, Any], dict[str, Any]]], limit: int
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Interleave outcome strata deterministically without using predictions as truth."""
    if limit < 1:
        raise ValueError("review limit must be positive")
    groups: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for item in mapping:
        groups[str(item[0]["primary_class_id"])].append(item)
    for rows in groups.values():
        rows.sort(key=lambda item: hashlib.sha256(item[0]["occurrence_id"].encode()).hexdigest())
    order: list[tuple[dict[str, Any], dict[str, Any]]] = []
    while groups and len(order) < limit:
        for name in sorted(tuple(groups)):
            order.append(groups[name].pop(0))
            if not groups[name]:
                del groups[name]
            if len(order) >= limit:
                break
    return order


def review_preview(row: dict[str, Any], document_views: dict[str, str]) -> str:
    """Return a bounded decoded view; missing text is explicit, not inferred."""
    document_id = row.get("document_id")
    if not document_id or document_id not in document_views:
        return "[No normalized text; inspect the extraction failure and original file.]"
    with Path(document_views[document_id]).open(encoding="utf-8") as handle:
        sample = handle.read(PREVIEW_CHARS + 1)
    sample = " ".join(sample.split())
    return sample[:PREVIEW_CHARS] + ("..." if len(sample) > PREVIEW_CHARS else "")


def evidence_terms(row: dict[str, Any]) -> list[str]:
    """Decode the serialized evidence for terminal display only."""
    return [str(item["term"]) for item in json.loads(row["evidence_json"])[:5]]
