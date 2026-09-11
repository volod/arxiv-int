"""Corpus chain reads apply detected languages and stream bounded batches."""

from pathlib import Path
from typing import Any

import pytest

from arxiv_int.pipeline.chunk.artifacts import CHUNKS_KIND
from arxiv_int.pipeline.load_lexical.source import (
    BATCH_ROWS,
    CorpusChain,
    ValidatedSnapshot,
    chunk_batches,
    document_batches,
    document_languages,
)
from arxiv_int.pipeline.normalize.artifacts import DOCUMENTS_KIND

pytest.importorskip("pyarrow")


def _write(root: Path, rows: list[dict[str, Any]]) -> Path:
    import pyarrow as pa
    import pyarrow.parquet as parquet

    root.mkdir(parents=True, exist_ok=True)
    parquet.write_table(pa.Table.from_pylist(rows), root / "part-00000.parquet")
    return root


def _snapshot(name: str, roots: dict[str, Path]) -> ValidatedSnapshot:
    manifest = Path("/nonexistent") / f"{name}.json"
    return ValidatedSnapshot(name, manifest, "digest", {"roots": roots})


def _chain(
    tmp_path: Path,
    *,
    normalized: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> CorpusChain:
    return CorpusChain(
        chunks=_snapshot("chunking", {CHUNKS_KIND: _write(tmp_path / "chunked", chunks)}),
        normalization=_snapshot(
            "normalization", {DOCUMENTS_KIND: _write(tmp_path / "normalized", normalized)}
        ),
        extraction=_snapshot(
            "extraction", {"documents": _write(tmp_path / "extracted", documents)}
        ),
    )


def test_detected_language_replaces_the_missing_extraction_value(tmp_path: Path) -> None:
    chain = _chain(
        tmp_path,
        normalized=[{"document_id": "d1", "language": "rus"}],
        documents=[
            {"document_id": "d1", "language": None},
            {"document_id": "d2", "language": None},
        ],
        chunks=[{"chunk_id": "c1", "document_id": "d1"}],
    )
    languages = document_languages(chain)
    assert languages == {"d1": "rus"}
    rows = [row for batch in document_batches(chain, languages) for row in batch]
    assert [(row["document_id"], row["language"]) for row in rows] == [("d1", "rus"), ("d2", None)]


def test_undetected_language_is_not_treated_as_a_detection(tmp_path: Path) -> None:
    chain = _chain(
        tmp_path,
        normalized=[{"document_id": "d1", "language": "und"}],
        documents=[{"document_id": "d1", "language": None}],
        chunks=[{"chunk_id": "c1", "document_id": "d1"}],
    )
    assert document_languages(chain) == {}


def test_chunk_rows_stream_in_bounded_batches(tmp_path: Path) -> None:
    chain = _chain(
        tmp_path,
        normalized=[{"document_id": "d1", "language": "rus"}],
        documents=[{"document_id": "d1", "language": None}],
        chunks=[{"chunk_id": f"c{index}", "document_id": "d1"} for index in range(BATCH_ROWS + 5)],
    )
    batches = list(chunk_batches(chain))
    assert [len(batch) for batch in batches] == [BATCH_ROWS, 5]
    assert [row["chunk_id"] for row in batches[1]] == [
        f"c{index}" for index in range(BATCH_ROWS, BATCH_ROWS + 5)
    ]


def test_chain_references_bind_every_upstream_checksum(tmp_path: Path) -> None:
    chain = _chain(
        tmp_path,
        normalized=[{"document_id": "d1", "language": "rus"}],
        documents=[{"document_id": "d1", "language": None}],
        chunks=[{"chunk_id": "c1", "document_id": "d1"}],
    )
    references = chain.references()
    assert sorted(references) == ["chunking", "extraction", "normalization"]
    assert all(item["sha256"] == "digest" for item in references.values())
