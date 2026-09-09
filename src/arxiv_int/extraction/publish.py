"""Bounded contract publication and extraction artifact validation."""

import os
from collections import Counter, defaultdict
from pathlib import Path
from uuid import uuid4

from arxiv_int.extraction.artifacts import (
    abort_publication,
    document_quality,
    extraction_summary,
    final_roots,
    record_file,
    write_occurrence,
    write_quarantine,
)
from arxiv_int.extraction.artifacts import (
    span_id as build_span_id,
)
from arxiv_int.extraction.batches import write_batch
from arxiv_int.extraction.model import InventoryInput
from arxiv_int.extraction.validate import ExtractionValidator
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.inventory.publish import atomic_json


class ExtractionPublisher:
    """Write bounded immutable document/span batches and explicit quarantine."""

    def __init__(
        self,
        results: Path,
        generation: str,
        validator: ExtractionValidator,
        batch_rows: int,
    ) -> None:
        self.results = results
        self.generation = generation
        self.validator = validator
        self.batch_rows = batch_rows
        self.snapshot = uuid4().hex
        self.staging = results / f".extract-{self.snapshot}.tmp"
        self.staging.mkdir(parents=True)
        self.documents = self.staging / "documents"
        self.spans = self.staging / "spans"
        self.quarantine = self.staging / "quarantine"
        self.manifest = self.staging / "manifest"
        for path in (self.documents / "text", self.spans, self.quarantine, self.manifest):
            path.mkdir(parents=True)
        self.document_rows: list[dict[str, object]] = []
        self.document_metadata: list[dict[str, object]] = []
        self.span_rows: list[dict[str, object]] = []
        self.span_metadata: list[dict[str, object]] = []
        self.document_part = 0
        self.span_part = 0
        self.documents_count = 0
        self.spans_count = 0
        self.quarantine_count = 0
        self.reused_count = 0
        self._moved: list[Path] = []
        self._sealed = False
        self.formats: dict[str, Counter[str]] = defaultdict(Counter)
        self.tables = 0
        self.anchored = 0
        self._files = (self.manifest / "files.jsonl").open("w", encoding="ascii")
        self._occurrences = (self.documents / "occurrences.jsonl").open("w", encoding="ascii")
        self._quarantines = (self.quarantine / "quarantine.jsonl").open("w", encoding="ascii")

    def add_document(
        self,
        item: InventoryInput,
        document: ExtractedDocument,
        document_id: str,
    ) -> None:
        """Write source text and queue its canonical rows and rich anchor sidecars."""
        text_path = self.documents / "text" / f"{document_id}.txt"
        text_path.write_text(document.text, encoding="utf-8")
        record_file(self._files, "documents", text_path, self.documents)
        quality = document_quality(document)
        row: dict[str, object] = {
            "document_id": document_id,
            "content_hash": item.content_hash,
            "extractor_profile": document.extractor_profile,
            "media_type": document.media_type,
            "language": None,
            "title": document.metadata.get("title") or Path(item.relative_path).name,
            "byte_size": item.size,
            "text_chars": len(document.text),
            "generation_id": self.generation,
            "contract_version": "1.0.0",
            "bucket": document_id[0],
        }
        self.document_rows.append(row)
        self.document_metadata.append(
            {
                "document_id": document_id,
                "raw_sha256": item.content_hash,
                "text_sha256": hash_file(text_path)[0],
                "tool": document.extractor_profile,
                "tool_metadata": dict(document.metadata),
                "quality": quality,
            }
        )
        for index, anchor in enumerate(document.anchors):
            span_id = build_span_id(
                document_id, index, anchor.start_char, anchor.end_char, anchor.kind
            )
            self.span_rows.append(
                {
                    "span_id": span_id,
                    "document_id": document_id,
                    "start_char": anchor.start_char,
                    "end_char": anchor.end_char,
                    "page": anchor.page,
                    "kind": anchor.kind or "text",
                    "generation_id": self.generation,
                    "contract_version": "1.0.0",
                    "bucket": span_id[0],
                }
            )
            self.span_metadata.append(
                {
                    "span_id": span_id,
                    "occurrence_id": item.occurrence_id,
                    "silo_id": item.silo_id,
                    "relative_path": item.relative_path,
                    "member_path": list(item.members),
                    "sheet": anchor.sheet or None,
                    "cell_range": anchor.cell_range or None,
                    "row": anchor.row,
                    "column": anchor.column,
                    "bbox": None
                    if anchor.bbox is None
                    else {
                        "x0": anchor.bbox.x0,
                        "y0": anchor.bbox.y0,
                        "x1": anchor.bbox.x1,
                        "y1": anchor.bbox.y1,
                    },
                    "coordinate_space": anchor.space,
                }
            )
            if len(self.span_rows) >= self.batch_rows:
                self._flush("spans")
        self.documents_count += 1
        self.spans_count += len(document.anchors)
        format_coverage = self.formats[item.media_type]
        format_coverage["documents"] += 1
        format_coverage["text_chars"] += len(document.text)
        format_coverage["anchors"] += len(document.anchors)
        format_coverage["anchored_chars"] += int(quality["anchored_chars"])
        format_coverage["table_cells"] += int(quality["table_cells"])
        self.tables += int(any(anchor.is_cell for anchor in document.anchors))
        self.anchored += int(bool(document.anchors))
        self.add_occurrence(item, document_id, reused=False)
        if len(self.document_rows) >= self.batch_rows:
            self._flush("documents")

    def add_occurrence(self, item: InventoryInput, document_id: str, *, reused: bool) -> None:
        """Map each physical occurrence to its content-addressed document."""
        write_occurrence(self._occurrences, item, document_id, reused)
        self.reused_count += int(reused)

    def add_quarantine(self, item: InventoryInput, reason: str, detail: str) -> None:
        """Retain an actionable failure without source content or absolute paths."""
        write_quarantine(self._quarantines, item, reason, detail)
        self.quarantine_count += 1

    def finish(self) -> Path:
        """Seal checksums last, then move all roots into immutable snapshots."""
        self._flush("documents")
        self._flush("spans")
        for handle in (self._occurrences, self._quarantines):
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
        record_file(self._files, "documents", self.documents / "occurrences.jsonl", self.documents)
        record_file(
            self._files, "quarantine", self.quarantine / "quarantine.jsonl", self.quarantine
        )
        self._files.flush()
        os.fsync(self._files.fileno())
        self._files.close()
        final = final_roots(self.results, self.generation, self.snapshot)
        for path in final.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        self.documents.replace(final["documents"])
        self._moved.append(final["documents"])
        self.spans.replace(final["spans"])
        self._moved.append(final["spans"])
        self.quarantine.replace(final["quarantine"])
        self._moved.append(final["quarantine"])
        (self.manifest / "files.jsonl").replace(self.staging / "files.jsonl")
        summary = extraction_summary(
            self.generation,
            final,
            {
                "documents": self.documents_count,
                "spans": self.spans_count,
                "quarantined": self.quarantine_count,
                "reused_content": self.reused_count,
            },
            self.formats,
            {"anchor_documents": self.anchored, "table_documents": self.tables},
            self.validator.fingerprint,
            hash_file(self.staging / "files.jsonl")[0],
        )
        atomic_json(self.staging / "extraction.json", summary)
        self.staging.replace(final["manifest"])
        self._sealed = True
        return final["manifest"] / "extraction.json"

    def abort(self) -> None:
        """Remove unpublished scratch while preserving already published immutable roots."""
        abort_publication(
            self.staging,
            (self._files, self._occurrences, self._quarantines),
            self._moved,
            self._sealed,
        )

    def _flush(self, kind: str) -> None:
        rows = self.document_rows if kind == "documents" else self.span_rows
        if not rows:
            return
        metadata = self.document_metadata if kind == "documents" else self.span_metadata
        root = self.documents if kind == "documents" else self.spans
        validator = self.validator.documents if kind == "documents" else self.validator.spans
        part = self.document_part if kind == "documents" else self.span_part
        for path in write_batch(validator, rows, metadata, root, part):
            record_file(self._files, kind, path, root)
        if kind == "documents":
            self.document_part += 1
        else:
            self.span_part += 1
        rows.clear()
        metadata.clear()
