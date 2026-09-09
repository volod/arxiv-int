"""Bounded scratch tables holding one grouping key and sketch row per document."""

from importlib import import_module
from pathlib import Path
from typing import Any

from arxiv_int.pipeline.dedupe.minhash import bands, shingles, sketch, tokens
from arxiv_int.pipeline.dedupe.model import DedupePolicy
from arxiv_int.pipeline.dedupe.source import NormalizedInput

SKETCH_FILE = "sketches.parquet"
BAND_FILE = "bands.parquet"


class SketchTables:
    """Stream per-document keys, sketches, and band keys to scratch Parquet."""

    def __init__(self, scratch: Path, policy: DedupePolicy) -> None:
        self.policy = policy
        self.arrow = import_module("pyarrow")
        parquet = import_module("pyarrow.parquet")
        self.sketch_path = scratch / SKETCH_FILE
        self.band_path = scratch / BAND_FILE
        self._sketch_schema = self.arrow.schema(
            [
                ("document_id", self.arrow.string()),
                ("normalized_document_id", self.arrow.string()),
                ("exact_key", self.arrow.string()),
                ("normalized_key", self.arrow.string()),
                ("text_chars", self.arrow.int64()),
                ("shingles", self.arrow.int64()),
                ("signature", self.arrow.list_(self.arrow.uint64())),
            ]
        )
        self._band_schema = self.arrow.schema(
            [
                ("band_index", self.arrow.int32()),
                ("band_key", self.arrow.uint64()),
                ("document_id", self.arrow.string()),
            ]
        )
        self._sketch_writer = parquet.ParquetWriter(
            self.sketch_path, self._sketch_schema, compression="zstd"
        )
        self._band_writer = parquet.ParquetWriter(
            self.band_path, self._band_schema, compression="zstd"
        )
        self._sketch_rows: list[dict[str, Any]] = []
        self._band_rows: list[dict[str, Any]] = []
        self.documents = 0
        self.sketched = 0
        self._closed = False

    def add(self, item: NormalizedInput, search_text: str) -> None:
        """Sketch one normalized document and queue its keys and band rows."""
        words = tokens(search_text, self.policy.max_shingle_tokens)
        signature, consumed = sketch(
            shingles(words, self.policy.shingle_words), self.policy.sketch_bins
        )
        self._sketch_rows.append(
            {
                "document_id": item.document_id,
                "normalized_document_id": item.normalized_document_id,
                "exact_key": item.text_sha256 or None,
                "normalized_key": item.normalized_sha256 or None,
                "text_chars": item.text_chars,
                "shingles": consumed,
                "signature": list(signature),
            }
        )
        self.documents += 1
        if consumed >= self.policy.min_sketch_shingles:
            for index, key in enumerate(bands(signature, self.policy.band_rows)):
                self._band_rows.append(
                    {"band_index": index, "band_key": key, "document_id": item.document_id}
                )
            self.sketched += 1
        if len(self._sketch_rows) >= self.policy.batch_rows:
            self.flush()

    def flush(self) -> None:
        """Write every buffered row so peak memory stays one batch wide."""
        if self._sketch_rows:
            self._sketch_writer.write_table(
                self.arrow.Table.from_pylist(self._sketch_rows, schema=self._sketch_schema)
            )
            self._sketch_rows.clear()
        if self._band_rows:
            self._band_writer.write_table(
                self.arrow.Table.from_pylist(self._band_rows, schema=self._band_schema)
            )
            self._band_rows.clear()

    def close(self) -> None:
        """Flush and close both scratch writers exactly once."""
        if self._closed:
            return
        self._closed = True
        self.flush()
        self._sketch_writer.close()
        self._band_writer.close()
