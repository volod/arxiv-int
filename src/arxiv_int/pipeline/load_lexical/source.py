"""Read the checksum-validated corpus chain the lexical load projects."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from arxiv_int.extraction.artifacts import validate_manifest as validate_extraction_manifest
from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.pipeline.chunk.artifacts import CHUNKS_KIND
from arxiv_int.pipeline.chunk.artifacts import validate_manifest as validate_chunk_manifest
from arxiv_int.pipeline.normalize.artifacts import DOCUMENTS_KIND
from arxiv_int.pipeline.normalize.artifacts import (
    validate_manifest as validate_normalization_manifest,
)

BATCH_ROWS = 2000
_EXTRACTION_DOCUMENTS = "documents"
_UNKNOWN_LANGUAGE = "und"


@dataclass(frozen=True, slots=True)
class ValidatedSnapshot:
    """One upstream manifest whose artifacts were rehashed before any read."""

    name: str
    manifest: Path
    sha256: str
    summary: Mapping[str, Any]

    def root(self, kind: str) -> Path:
        """Return one immutable artifact root recorded by the manifest."""
        return Path(self.summary["roots"][kind])

    def reference(self) -> dict[str, str]:
        """Return the checksum-bound pointer retained in the load manifest."""
        return {"manifest": str(self.manifest), "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class CorpusChain:
    """The chunk, normalization, and extraction snapshots one load projects."""

    chunks: ValidatedSnapshot
    normalization: ValidatedSnapshot
    extraction: ValidatedSnapshot

    def references(self) -> dict[str, dict[str, str]]:
        """Return every validated upstream pointer for the load manifest."""
        return {
            item.name: item.reference()
            for item in (self.chunks, self.normalization, self.extraction)
        }


def corpus_chain(context: StageContext) -> CorpusChain:
    """Validate the chunk snapshot and the upstream snapshots it names."""
    chunks = _validated(
        "chunking",
        context.options.get("chunking_manifest", ""),
        context.options.get("chunking_manifest_sha256", ""),
        validate_chunk_manifest,
    )
    normalization = _linked(chunks, "normalization", validate_normalization_manifest)
    extraction = _linked(normalization, "extraction", validate_extraction_manifest)
    return CorpusChain(chunks, normalization, extraction)


def document_languages(chain: CorpusChain) -> dict[str, str]:
    """Map each document to the language normalization detected for it."""
    root = chain.normalization.root(DOCUMENTS_KIND)
    languages: dict[str, str] = {}
    for row in _rows(root):
        language = str(row.get("language") or _UNKNOWN_LANGUAGE)
        if language != _UNKNOWN_LANGUAGE:
            languages[str(row["document_id"])] = language
    return languages


def document_batches(
    chain: CorpusChain, languages: Mapping[str, str]
) -> Iterator[list[dict[str, Any]]]:
    """Stream extracted document rows with the detected language applied."""
    root = chain.extraction.root(_EXTRACTION_DOCUMENTS)
    batch: list[dict[str, Any]] = []
    for row in _rows(root):
        row["language"] = languages.get(str(row["document_id"])) or row.get("language")
        batch.append(row)
        if len(batch) >= BATCH_ROWS:
            yield batch
            batch = []
    if batch:
        yield batch


def chunk_batches(chain: CorpusChain) -> Iterator[list[dict[str, Any]]]:
    """Stream published chunk rows in stable partition order."""
    root = chain.chunks.root(CHUNKS_KIND)
    batch: list[dict[str, Any]] = []
    for row in _rows(root):
        batch.append(row)
        if len(batch) >= BATCH_ROWS:
            yield batch
            batch = []
    if batch:
        yield batch


def _rows(root: Path) -> Iterator[dict[str, Any]]:
    parquet = import_module("pyarrow.parquet")
    for path in sorted(root.glob("part-*.parquet")):
        reader = parquet.ParquetFile(path)
        for batch in reader.iter_batches(batch_size=BATCH_ROWS):
            yield from batch.to_pylist()


def _validated(name: str, referenced: str, digest: str, validate: Any) -> ValidatedSnapshot:
    if not referenced or not digest:
        raise ValueError(f"load-lexical requires a validated upstream {name} manifest")
    manifest = Path(referenced)
    if manifest.is_symlink() or manifest.resolve() != manifest:
        raise ValueError(f"symlinked {name} manifest reference")
    return ValidatedSnapshot(name, manifest, digest, validate(manifest, digest))


def _linked(parent: ValidatedSnapshot, name: str, validate: Any) -> ValidatedSnapshot:
    pointer = parent.summary.get("upstream", {}).get(name) or parent.summary.get(name)
    if not isinstance(pointer, Mapping):
        raise ValueError(f"{parent.name} manifest does not name its {name} snapshot")
    return _validated(
        name, str(pointer.get("manifest", "")), str(pointer.get("sha256", "")), validate
    )
