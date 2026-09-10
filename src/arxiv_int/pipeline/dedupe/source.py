"""Read the checksum-validated upstream normalization snapshot."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.pipeline.lake.artifacts import batch_sidecar
from arxiv_int.pipeline.normalize.artifacts import DOCUMENTS_KIND, view_path
from arxiv_int.pipeline.normalize.artifacts import (
    validate_manifest as validate_normalization_manifest,
)

_PARQUET_BATCH_ROWS = 256


@dataclass(frozen=True, slots=True)
class NormalizedInput:
    """One normalized document with the keys and text needed for grouping."""

    document_id: str
    normalized_document_id: str
    text_sha256: str
    normalized_sha256: str
    text_chars: int
    search_path: Path


def normalization_snapshot(context: StageContext) -> tuple[Path, str, dict[str, Any]]:
    """Return the referenced normalization manifest, its digest, and validated summary."""
    referenced = context.options.get("normalization_manifest", "")
    digest = context.options.get("normalization_manifest_sha256", "")
    if not referenced or not digest:
        raise ValueError("dedupe requires a validated upstream normalization manifest")
    manifest = Path(referenced)
    if manifest.is_symlink() or manifest.resolve() != manifest:
        raise ValueError("symlinked normalization manifest reference")
    return manifest, digest, validate_normalization_manifest(manifest, digest)


def snapshot_roots(summary: Mapping[str, Any]) -> dict[str, Path]:
    """Return the immutable normalization roots recorded by the upstream manifest."""
    return {name: Path(value) for name, value in summary["roots"].items()}


def normalized_inputs(roots: Mapping[str, Path]) -> Iterator[NormalizedInput]:
    """Stream normalized documents in stable partition order without loading all rows."""
    documents = roots[DOCUMENTS_KIND]
    parquet = import_module("pyarrow.parquet")
    for path in sorted(documents.glob("part-*.parquet")):
        sidecar = batch_sidecar(path, "normalized_document_id")
        reader = parquet.ParquetFile(path)
        for batch in reader.iter_batches(batch_size=_PARQUET_BATCH_ROWS):
            for row in batch.to_pylist():
                identity = str(row["normalized_document_id"])
                extra = sidecar.get(identity, {})
                yield NormalizedInput(
                    str(row["document_id"]),
                    identity,
                    str(extra.get("text_sha256") or ""),
                    str(row["normalized_sha256"] or ""),
                    int(row["text_chars"] or 0),
                    view_path(documents, "search", identity),
                )
