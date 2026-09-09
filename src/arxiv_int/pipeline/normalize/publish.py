"""Publish canonical, search, and offset-map views as one immutable snapshot."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, TextIO

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.lake.artifacts import write_json_line
from arxiv_int.pipeline.lake.publish import SnapshotPublisher
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.pipeline.normalize.artifacts import (
    CONTRACT,
    DATASETS,
    DOCUMENTS_KIND,
    LAYOUT,
    QUARANTINE_KIND,
    SCHEMA,
    VIEW_DIRECTORIES,
    view_path,
)
from arxiv_int.pipeline.normalize.language import LanguageResult
from arxiv_int.pipeline.normalize.model import DocumentInput, normalized_document_id
from arxiv_int.pipeline.normalize.text import TextView


class NormalizationPublisher:
    """Write one bounded normalized-document snapshot beside its evidence."""

    def __init__(
        self,
        results: Path,
        generation: str,
        validator: SnapshotValidator,
        normalizer: str,
        batch_rows: int,
    ) -> None:
        self.normalizer = normalizer
        self.snapshot = SnapshotPublisher(
            results, "normalize", generation, validator, LAYOUT, DATASETS, batch_rows
        )
        self.generation = generation
        self.documents = self.snapshot.directory(DOCUMENTS_KIND)
        for view in VIEW_DIRECTORIES:
            (self.documents / view).mkdir(parents=True)
        self.languages: Counter[str] = Counter()
        self.documents_count = 0
        self.quarantine_count = 0
        self.canonical_chars = 0
        self.search_chars = 0
        self._quarantine: TextIO = self.snapshot.open_stream(QUARANTINE_KIND, "quarantine.jsonl")

    def add_document(
        self,
        item: DocumentInput,
        canonical: TextView,
        search: TextView,
        language: LanguageResult,
    ) -> str:
        """Write every derived view and queue the canonical contract row."""
        identity = normalized_document_id(item.document_id, self.normalizer)
        canonical_path = self._write_view(identity, "canonical", canonical.text)
        search_path = self._write_view(identity, "search", search.text)
        offsets = {
            "normalized_document_id": identity,
            "document_id": item.document_id,
            "canonical_from_original": canonical.offsets.serialize(),
            "search_from_canonical": search.offsets.serialize(),
        }
        offsets_path = view_path(self.documents, "offsets", identity)
        offsets_path.write_text(
            json.dumps(offsets, ensure_ascii=True, sort_keys=True) + "\n", encoding="ascii"
        )
        self.snapshot.record(DOCUMENTS_KIND, offsets_path)
        row: dict[str, object] = {
            "normalized_document_id": identity,
            "document_id": item.document_id,
            "normalizer_id": self.normalizer,
            "language": language.language,
            "language_confidence": language.confidence,
            "normalized_sha256": hash_file(canonical_path)[0],
            "text_chars": len(canonical.text),
            "generation_id": self.generation,
            "contract_version": "1.0.0",
            "bucket": identity[0],
        }
        metadata: dict[str, object] = {
            "normalized_document_id": identity,
            "document_id": item.document_id,
            "content_hash": item.content_hash,
            "text_sha256": item.text_sha256,
            "media_type": item.media_type,
            "title": item.title,
            "original_chars": item.text_chars,
            "canonical_chars": len(canonical.text),
            "search_chars": len(search.text),
            "search_sha256": hash_file(search_path)[0],
            "offset_map_sha256": hash_file(offsets_path)[0],
            "canonical_runs": len(canonical.offsets.runs),
            "search_runs": len(search.offsets.runs),
        }
        self.snapshot.add_row(CONTRACT, row, metadata)
        self.documents_count += 1
        self.canonical_chars += len(canonical.text)
        self.search_chars += len(search.text)
        self.languages[language.language] += 1
        return identity

    def add_quarantine(self, item: DocumentInput, reason: str, detail: str) -> None:
        """Retain one actionable normalization failure without source content."""
        write_json_line(
            self._quarantine,
            {
                "document_id": item.document_id,
                "content_hash": item.content_hash,
                "media_type": item.media_type,
                "reason": reason,
                "detail": detail[:2000],
            },
        )
        self.quarantine_count += 1

    def finish(self, extraction: dict[str, str]) -> Path:
        """Seal the snapshot and record the upstream extraction it normalized."""
        return self.snapshot.finish(
            SCHEMA,
            {
                "normalized_documents": self.documents_count,
                "quarantined": self.quarantine_count,
            },
            {
                "normalizer_id": self.normalizer,
                "extraction": extraction,
                "languages": dict(sorted(self.languages.items())),
                "coverage": {
                    "canonical_chars": self.canonical_chars,
                    "search_chars": self.search_chars,
                },
            },
        )

    def abort(self) -> None:
        """Remove unpublished scratch and any root moved before a failed seal."""
        self.snapshot.abort()

    def _write_view(self, identity: str, view: str, text: str) -> Path:
        path = view_path(self.documents, view, identity)
        path.write_text(text, encoding="utf-8")
        self.snapshot.record(DOCUMENTS_KIND, path)
        return path


def manifest_reference(manifest: Path) -> dict[str, Any]:
    """Return the checksum-bound pointer downstream stages revalidate."""
    return {"manifest": str(manifest), "sha256": hash_file(manifest)[0]}
