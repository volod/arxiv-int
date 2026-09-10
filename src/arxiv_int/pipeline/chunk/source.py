"""Read the checksum-validated normalization and duplicate-grouping snapshots."""

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from arxiv_int.features import require_module
from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.pipeline.dedupe.artifacts import GROUPS_KIND
from arxiv_int.pipeline.dedupe.artifacts import (
    validate_manifest as validate_dedupe_manifest,
)
from arxiv_int.pipeline.normalize.artifacts import DOCUMENTS_KIND, view_path
from arxiv_int.pipeline.normalize.artifacts import (
    validate_manifest as validate_normalization_manifest,
)
from arxiv_int.pipeline.normalize.text import OffsetMap, load_offset_map

_PARQUET_BATCH_ROWS = 256


@dataclass(frozen=True, slots=True)
class ChunkInput:
    """One normalized document and the derived views chunking reads."""

    document_id: str
    normalized_document_id: str
    language: str
    canonical_path: Path
    offsets_path: Path


@dataclass(frozen=True, slots=True)
class UpstreamSnapshot:
    """One validated upstream manifest pointer and its summary."""

    manifest: Path
    sha256: str
    summary: dict[str, Any]

    def roots(self) -> dict[str, Path]:
        """Return the immutable roots recorded by the upstream manifest."""
        return {name: Path(value) for name, value in self.summary["roots"].items()}

    def reference(self) -> dict[str, str]:
        """Return the checksum-bound pointer retained in the chunk manifest."""
        return {"manifest": str(self.manifest), "sha256": self.sha256}


def upstream(context: StageContext, name: str) -> UpstreamSnapshot:
    """Validate one referenced upstream manifest before any artifact is read."""
    referenced = context.options.get(f"{name}_manifest", "")
    digest = context.options.get(f"{name}_manifest_sha256", "")
    if not referenced or not digest:
        raise ValueError(f"chunk requires a validated upstream {name} manifest")
    manifest = Path(referenced)
    if manifest.is_symlink() or manifest.resolve() != manifest:
        raise ValueError(f"symlinked {name} manifest reference")
    validate = (
        validate_normalization_manifest if name == "normalization" else validate_dedupe_manifest
    )
    return UpstreamSnapshot(manifest, digest, validate(manifest, digest))


def suppressed_documents(roots: Mapping[str, Path]) -> frozenset[str]:
    """Return the documents one duplicate group already represents elsewhere."""
    polars = require_module("polars")
    groups = roots[GROUPS_KIND]
    if not any(groups.glob("part-*.parquet")):
        return frozenset()
    frame = (
        polars.scan_parquet(groups / "part-*.parquet")
        .filter(polars.col("suppressed"))
        .select("document_id")
        .unique()
        .collect(engine="streaming")
    )
    return frozenset(str(value) for value in frame["document_id"].to_list())


def chunk_inputs(roots: Mapping[str, Path]) -> Iterator[ChunkInput]:
    """Stream normalized documents in stable partition order."""
    documents = roots[DOCUMENTS_KIND]
    parquet = import_module("pyarrow.parquet")
    for path in sorted(documents.glob("part-*.parquet")):
        reader = parquet.ParquetFile(path)
        for batch in reader.iter_batches(batch_size=_PARQUET_BATCH_ROWS):
            for row in batch.to_pylist():
                identity = str(row["normalized_document_id"])
                yield ChunkInput(
                    str(row["document_id"]),
                    identity,
                    str(row["language"] or "und"),
                    view_path(documents, "canonical", identity),
                    view_path(documents, "offsets", identity),
                )


def canonical_text(item: ChunkInput) -> str:
    """Read one canonical view, refusing symlinked or missing artifacts."""
    if item.canonical_path.is_symlink() or not item.canonical_path.is_file():
        raise ValueError(f"canonical view is missing for {item.document_id}")
    return item.canonical_path.read_bytes().decode("utf-8")


def original_offsets(item: ChunkInput) -> OffsetMap:
    """Rebuild the original-to-canonical offset map retained by normalization."""
    if item.offsets_path.is_symlink() or not item.offsets_path.is_file():
        raise ValueError(f"offset map is missing for {item.document_id}")
    payload = json.loads(item.offsets_path.read_text(encoding="ascii"))
    return load_offset_map(payload["canonical_from_original"])
