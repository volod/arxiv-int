"""Declared live lexical load, BM25 query, citation, and rebuild observability."""

import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.pipeline.load_lexical.loader import load_contract
from arxiv_int.pipeline.load_lexical.reconcile import reconcile
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.retrieval.citations import resolve_citations, unresolved_citations
from arxiv_int.retrieval.lexical import LexicalRequest, explain, lookup, search
from arxiv_int.retrieval.projection import (
    LexicalUnavailableError,
    active_target,
    index_size,
)
from arxiv_int.stores.postgres.apply import apply_revisions
from arxiv_int.stores.postgres.disposable import disposable_store, image_present
from arxiv_int.stores.postgres_image.pins import load_image_pins
from arxiv_int.stores.projections.lifecycle import build_projections
from arxiv_int.stores.projections.model import KIND_LEXICAL, ProjectionRequest

pytestmark = [
    pytest.mark.heavy,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_LEXICAL") != "1",
        reason="set ARXIV_INT_RUN_LEXICAL=1 for the declared disposable lexical run",
    ),
]

GENERATION = "gen-lexical"
DOCUMENTS: tuple[dict[str, Any], ...] = (
    {
        "document_id": "doc-1",
        "generation_id": GENERATION,
        "contract_version": "1.0.0",
        "title": "Nasosnaya stanciya",
        "language": "rus",
    },
    {
        "document_id": "doc-2",
        "generation_id": GENERATION,
        "contract_version": "1.0.0",
        "title": "Pump station",
        "language": "eng",
    },
)
CHUNKS: tuple[dict[str, Any], ...] = (
    {
        "chunk_id": "chunk-1",
        "document_id": "doc-1",
        "generation_id": GENERATION,
        "contract_version": "1.0.0",
        "text": "Nasosy peredayut zhidkost. Nasos model P-100 rabotaet.",
        "chunker_id": "sent-1",
        "start_char": 0,
        "end_char": 54,
    },
    {
        "chunk_id": "chunk-2",
        "document_id": "doc-2",
        "generation_id": GENERATION,
        "contract_version": "1.0.0",
        "text": "The pump moves liquid.",
        "chunker_id": "sent-1",
        "start_char": 0,
        "end_char": 22,
    },
)


def _root() -> Path:
    return discover_project_root(Path(__file__))


def _seed(url: str) -> None:
    root = _root()
    model = load_schema_model_from_root(contracts_root_for(root))
    validator = SnapshotValidator(root, ("documents", "chunks"))
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            load_contract(
                connection,
                model=model,
                validator=validator,
                contract="documents",
                key="document_id",
                batches=[list(DOCUMENTS)],
            )
            counts = load_contract(
                connection,
                model=model,
                validator=validator,
                contract="chunks",
                key="chunk_id",
                batches=[list(CHUNKS)],
            )
    finally:
        engine.dispose()
    assert counts.rows == len(CHUNKS)


def test_live_lexical_load_query_and_citations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pins = load_image_pins(_root())
    if not image_present(pins.local_image_ref):
        pytest.skip(f"image {pins.local_image_ref} is not present; build it first")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    with disposable_store(_root(), tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(_root(), url=store.url, run_id="lex-schema", revision="head").ok
        engine = create_engine(store.url)
        try:
            with (
                engine.connect() as connection,
                pytest.raises(LexicalUnavailableError, match="no active lexical projection"),
            ):
                active_target(connection)
        finally:
            engine.dispose()
        _seed(store.url)
        result = build_projections(
            ProjectionRequest(
                run_id="lex-a",
                project_root=_root(),
                database_url=store.url,
                kinds=(KIND_LEXICAL,),
                activate=True,
            )
        )
        assert result.status == "ok", result.detail
        _assert_queries(store.url, result.kinds[0].engine_object.split(":")[0])


def _assert_queries(url: str, table: str) -> None:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            target = active_target(connection)
            assert target.table == table
            assert target.row_count == len(CHUNKS)
            assert index_size(connection, target)["index_bytes"] > 0
            reconciliation = reconcile(
                connection,
                table=table,
                loaded_chunks=len(CHUNKS),
                loaded_checksum=target.checksum,
                projection_checksum=target.checksum,
            )
            assert reconciliation.ok, reconciliation.detail
            _assert_search(connection)
    finally:
        engine.dispose()


def _assert_search(connection: Any) -> None:
    ranked = search(connection, LexicalRequest(query="nasos", facets=("language",)))
    assert [hit.chunk_id for hit in ranked.hits] == ["chunk-1"]
    assert "[[" in ranked.hits[0].snippet
    assert ranked.facets["language"] == (("rus", 1),)
    assert ranked.total == 1
    filtered = search(connection, LexicalRequest(query="pump", language="rus"))
    assert filtered.hits == ()
    english = search(connection, LexicalRequest(query="pump", language="eng"))
    assert [hit.chunk_id for hit in english.hits] == ["chunk-2"]
    assert lookup(connection, "chunk-1")[0].document_id == "doc-1"
    assert lookup(connection, "doc-2")[0].chunk_id == "chunk-2"
    assert lookup(connection, "P-100") == ()
    plan = "\n".join(explain(connection, LexicalRequest(query="nasos")))
    assert "ParadeDB" in plan
    citations = resolve_citations(connection, [hit.chunk_id for hit in ranked.hits])
    assert citations[0].span.document_id == "doc-1"
    assert citations[0].span.end == CHUNKS[0]["end_char"]
    assert unresolved_citations(["chunk-1", "absent"], citations) == ("absent",)
