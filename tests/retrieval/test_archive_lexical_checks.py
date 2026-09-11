"""Deterministic checks for archive lexical probe helpers."""

from arxiv_int.retrieval.citations import ChunkCitation
from arxiv_int.retrieval.lexical_model import LexicalHit
from arxiv_int.retrieval.metrics import RetrievedChunk, SourceSpan
from tests.integration.lexical.checks import (
    filter_matches,
    gold_span,
    identifier_exactness,
    limit_honored,
    offset_matches,
    probe_terms,
    retrieved_chunks,
)


def _hit(chunk_id: str, document_id: str, rank: int = 1, snippet: str = "") -> LexicalHit:
    return LexicalHit(rank, chunk_id, document_id, "", "rus", 1.0, snippet)


def test_probe_terms_prefer_the_longest_distinct_letter_tokens() -> None:
    body = "aa bb nasosnaya stanciya nasosnaya P-100 zhidkost"
    assert probe_terms(body, limit=3) == ("nasosnaya", "stanciya", "zhidkost")


def test_probe_terms_normalize_cyrillic_case_without_keeping_short_tokens() -> None:
    body = "\u041d\u0430\u0441\u043e\u0441 \u043d\u0430\u0441\u043e\u0441\u044b \u0438 \u0442\u043e\u043a"
    assert probe_terms(body, limit=2) == ("\u043d\u0430\u0441\u043e\u0441\u044b",)


def test_identifier_filter_limit_and_offset_helpers() -> None:
    first = (_hit("c1", "d1", 1), _hit("c2", "d1", 2), _hit("c3", "d2", 3))
    assert identifier_exactness(first[:1], "c1", "d1") == 1.0
    assert identifier_exactness((), "c1", "d1") == 0.0
    assert filter_matches(first[:2], document_id="d1")
    assert not filter_matches(first, document_id="d1")
    assert limit_honored(3, 10, 3)
    assert limit_honored(2, 2, 3)
    assert not limit_honored(4, 10, 3)
    assert offset_matches(first, (_hit("c2", "d1", 1),))
    assert not offset_matches(first[:1], (_hit("c2", "d1", 1),))


def test_retrieved_chunks_drop_unresolved_hits_and_omit_source_text() -> None:
    hits = (_hit("c1", "d1", snippet="secret"), _hit("missing", "d1"))
    citations = (ChunkCitation("c1", "sent-1", SourceSpan("d1", 4, 12)),)
    chunks = retrieved_chunks(hits, citations)
    assert chunks == (RetrievedChunk("d1", 4, 12, ""),)
    assert gold_span("d1", 4, 12) == SourceSpan("d1", 4, 12)
    assert chunks[0].text == ""
