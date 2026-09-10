"""Chunk stage overlays, golden offsets, and stable identities."""

import json
from pathlib import Path

import pytest

from arxiv_int.pipeline.chunk.artifacts import validate_manifest
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.normalize.text import load_offset_map
from tests.pipeline.chain import COPY_DOCUMENT, PROSE_DOCUMENT, ChainRun, run_chain


@pytest.fixture(scope="module")
def chain(tmp_path_factory: pytest.TempPathFactory) -> ChainRun:
    return run_chain(tmp_path_factory.mktemp("chunk"))


def _parquet_rows(root: Path) -> list[dict[str, object]]:
    polars = pytest.importorskip("polars")
    files = sorted(root.glob("part-*.parquet"))
    if not files:
        return []
    return polars.read_parquet(files).to_dicts()


def _summary(run: ChainRun, kind: str) -> dict[str, object]:
    return json.loads(run.manifest(getattr(run, kind)).read_text(encoding="ascii"))


def _rows(run: ChainRun, kind: str, contract: str) -> list[dict[str, object]]:
    return _parquet_rows(Path(str(_summary(run, kind)["roots"][contract])))


def _metadata(run: ChainRun) -> list[dict[str, object]]:
    root = Path(str(_summary(run, "chunk")["roots"]["chunks"]))
    records: list[dict[str, object]] = []
    for path in sorted(root.glob("part-*.metadata.jsonl")):
        records.extend(json.loads(line) for line in path.read_text(encoding="ascii").splitlines())
    return records


def test_stage_chunks_representatives_and_skips_suppressed_duplicates(chain: ChainRun) -> None:
    summary = _summary(chain, "chunk")
    suppressed = {
        str(row["document_id"])
        for row in _rows(chain, "dedupe", "duplicate-groups")
        if row["suppressed"]
    }
    chunked = {str(row["document_id"]) for row in _rows(chain, "chunk", "chunks")}

    assert chain.chunk.outcome in {"produced", "partial"}
    assert int(summary["chunks"]) > 0
    assert int(summary["suppressed_documents"]) == len(suppressed)
    assert not (chunked & suppressed)
    assert any(item["kind"] == "table" for item in _metadata(chain))


def test_table_headers_and_original_offsets_survive_chunking(chain: ChainRun) -> None:
    extraction = _summary(chain, "extract")
    documents = Path(str(extraction["roots"]["documents"]))
    offsets_root = (
        Path(str(_summary(chain, "normalize")["roots"]["normalized-documents"])) / "offsets"
    )
    chunks = {str(row["chunk_id"]): row for row in _rows(chain, "chunk", "chunks")}
    tables = [item for item in _metadata(chain) if item["kind"] == "table"]
    assert tables
    for item in tables:
        chunk = chunks[str(item["chunk_id"])]
        assert str(chunk["text"]).startswith("| Item | Amount |")
        original = (documents / "text" / f"{item['document_id']}.txt").read_text(encoding="utf-8")
        payload = json.loads(
            (offsets_root / f"{item['normalized_document_id']}.json").read_text(encoding="ascii")
        )
        mapping = load_offset_map(payload["canonical_from_original"])
        start = mapping.to_source(int(item["canonical_start"]))
        end = mapping.to_source(int(item["canonical_end"]))
        assert 0 <= start <= end <= len(original)
        assert int(chunk["start_char"]) == start
        assert int(chunk["end_char"]) == end


def test_unchanged_input_yields_stable_chunk_ids(tmp_path: Path) -> None:
    first = run_chain(tmp_path / "a")
    second = run_chain(tmp_path / "b")
    left = {row["chunk_id"] for row in _rows(first, "chunk", "chunks")}
    right = {row["chunk_id"] for row in _rows(second, "chunk", "chunks")}
    assert left == right
    assert left


def test_manifest_rejects_a_tampered_chunk_batch(tmp_path: Path) -> None:
    run = run_chain(tmp_path, fixtures={"prose.txt": PROSE_DOCUMENT, "copy.txt": COPY_DOCUMENT})
    manifest = run.manifest(run.chunk)
    parquet = next(Path(str(_summary(run, "chunk")["roots"]["chunks"])).glob("part-*.parquet"))
    parquet.write_bytes(parquet.read_bytes() + b"\x00")
    with pytest.raises(ValueError, match="checksum"):
        validate_manifest(manifest, hash_file(manifest)[0])


def test_source_offsets_address_carriage_returns_in_the_extracted_artifact(
    chain: ChainRun,
) -> None:
    documents = Path(str(_summary(chain, "extract")["roots"]["documents"])) / "text"
    chunks = {str(row["chunk_id"]): row for row in _rows(chain, "chunk", "chunks")}
    shifted = [
        item
        for item in _metadata(chain)
        if int(item["canonical_start"]) != int(item["original_start"])
    ]
    assert shifted, "the chain must retain a document whose canonical view shifts source offsets"
    for item in shifted:
        row = chunks[str(item["chunk_id"])]
        original = (documents / f"{item['document_id']}.txt").read_bytes().decode("utf-8")
        assert "\r" in original
        segment = original[int(row["start_char"]) : int(row["end_char"])]
        assert segment.replace("\r\n", "\n") == str(row["text"])
        assert int(row["start_char"]) == int(item["original_start"])
        assert int(row["end_char"]) == int(item["original_end"])
