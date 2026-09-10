"""Publish source-aligned chunks as one immutable snapshot."""

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO

from arxiv_int.pipeline.chunk.artifacts import (
    CHUNKS_KIND,
    CONTRACT,
    DATASETS,
    LAYOUT,
    QUARANTINE_KIND,
    SCHEMA,
)
from arxiv_int.pipeline.chunk.model import Chunk, chunk_id
from arxiv_int.pipeline.chunk.source import ChunkInput
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.lake.artifacts import write_json_line
from arxiv_int.pipeline.lake.publish import SnapshotPublisher
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.pipeline.normalize.text import OffsetMap


class ChunkPublisher:
    """Write one bounded chunk snapshot beside its quarantine evidence."""

    def __init__(
        self,
        results: Path,
        generation: str,
        validator: SnapshotValidator,
        chunker: str,
        batch_rows: int,
    ) -> None:
        self.chunker = chunker
        self.generation = generation
        self.snapshot = SnapshotPublisher(
            results, "chunk", generation, validator, LAYOUT, DATASETS, batch_rows
        )
        self.kinds: Counter[str] = Counter()
        self.documents = 0
        self.chunks = 0
        self.chunk_chars = 0
        self.truncated = 0
        self.suppressed = 0
        self.quarantine_count = 0
        self._quarantine: TextIO = self.snapshot.open_stream(QUARANTINE_KIND, "quarantine.jsonl")

    def add_document(
        self,
        item: ChunkInput,
        chunks: Sequence[Chunk],
        offsets: OffsetMap,
        *,
        truncated: bool,
    ) -> None:
        """Queue every chunk of one document with both coordinate spaces recorded."""
        for chunk in chunks:
            identity = chunk_id(item.document_id, self.chunker, chunk)
            start = offsets.to_source(chunk.start)
            end = offsets.to_source(chunk.end)
            row: dict[str, object] = {
                "chunk_id": identity,
                "document_id": item.document_id,
                "chunker_id": self.chunker,
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "start_char": start,
                "end_char": end,
                "generation_id": self.generation,
                "contract_version": "1.0.0",
                "bucket": identity[0],
            }
            metadata: dict[str, object] = {
                "chunk_id": identity,
                "document_id": item.document_id,
                "normalized_document_id": item.normalized_document_id,
                "kind": chunk.kind,
                "language": item.language,
                "canonical_start": chunk.start,
                "canonical_end": chunk.end,
                "original_start": start,
                "original_end": end,
                "section_path": list(chunk.section_path),
                "sentences": chunk.sentences,
                "repeated_prefix_chars": chunk.prefix_chars,
                "repeated_prefix_span": list(chunk.prefix_span)
                if chunk.prefix_span is not None
                else None,
            }
            self.snapshot.add_row(CONTRACT, row, metadata)
            self.kinds[chunk.kind] += 1
            self.chunks += 1
            self.chunk_chars += len(chunk.text)
        self.documents += 1
        self.truncated += int(truncated)

    def add_suppressed(self) -> None:
        """Count one duplicate the grouping overlay already represents elsewhere."""
        self.suppressed += 1

    def add_quarantine(self, item: ChunkInput, reason: str, detail: str) -> None:
        """Retain one actionable chunking failure without source content."""
        write_json_line(
            self._quarantine,
            {
                "document_id": item.document_id,
                "normalized_document_id": item.normalized_document_id,
                "reason": reason,
                "detail": detail[:2000],
            },
        )
        self.quarantine_count += 1

    def finish(self, upstream: Mapping[str, Mapping[str, str]]) -> Path:
        """Seal the snapshot and record the upstream snapshots it chunked."""
        return self.snapshot.finish(
            SCHEMA,
            {
                "chunks": self.chunks,
                "chunked_documents": self.documents,
                "suppressed_documents": self.suppressed,
                "quarantined": self.quarantine_count,
            },
            {
                "chunker_id": self.chunker,
                "upstream": {name: dict(value) for name, value in upstream.items()},
                "kinds": dict(sorted(self.kinds.items())),
                "coverage": {
                    "chunk_chars": self.chunk_chars,
                    "truncated_documents": self.truncated,
                },
            },
        )

    def abort(self) -> None:
        """Remove unpublished scratch and any root moved before a failed seal."""
        self.snapshot.abort()

    def directory(self) -> Path:
        """Return the scratch root backing published chunk batches."""
        return self.snapshot.directory(CHUNKS_KIND)


def manifest_reference(manifest: Path) -> dict[str, Any]:
    """Return the checksum-bound pointer downstream stages revalidate."""
    return {"manifest": str(manifest), "sha256": hash_file(manifest)[0]}
