"""Read the checksum-validated upstream extraction snapshot."""

from collections.abc import Iterator, Mapping
from importlib import import_module
from pathlib import Path
from typing import Any

from arxiv_int.extraction.artifacts import validate_manifest as validate_extraction_manifest
from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.pipeline.lake.artifacts import batch_sidecar
from arxiv_int.pipeline.normalize.model import DocumentInput

_PARQUET_BATCH_ROWS = 256


def extraction_snapshot(context: StageContext) -> tuple[Path, str, dict[str, Any]]:
    """Return the referenced extraction manifest, its digest, and validated summary."""
    referenced = context.options.get("extraction_manifest", "")
    digest = context.options.get("extraction_manifest_sha256", "")
    if not referenced or not digest:
        raise ValueError("normalize requires a validated upstream extraction manifest")
    manifest = Path(referenced)
    if manifest.is_symlink() or manifest.resolve() != manifest:
        raise ValueError("symlinked extraction manifest reference")
    summary = validate_extraction_manifest(manifest, digest)
    return manifest, digest, summary


def snapshot_roots(summary: Mapping[str, Any]) -> dict[str, Path]:
    """Return the immutable extraction roots recorded by the upstream manifest."""
    return {name: Path(value) for name, value in summary["roots"].items()}


def document_inputs(roots: Mapping[str, Path]) -> Iterator[DocumentInput]:
    """Stream extracted documents in stable partition order without loading all rows."""
    documents = roots["documents"]
    text_root = documents / "text"
    parquet = import_module("pyarrow.parquet")
    for path in sorted(documents.glob("part-*.parquet")):
        sidecar = batch_sidecar(path, "document_id")
        reader = parquet.ParquetFile(path)
        for batch in reader.iter_batches(batch_size=_PARQUET_BATCH_ROWS):
            for row in batch.to_pylist():
                document_id = str(row["document_id"])
                extra = sidecar.get(document_id, {})
                yield DocumentInput(
                    document_id,
                    str(row["content_hash"] or ""),
                    str(extra.get("text_sha256") or ""),
                    str(row["media_type"] or ""),
                    str(row["title"] or ""),
                    int(row["text_chars"] or 0),
                    text_root / f"{document_id}.txt",
                )
