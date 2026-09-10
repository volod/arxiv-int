"""Typed lexical requests, results, and citation resolution."""

import pytest

from arxiv_int.retrieval.citations import ChunkCitation, unresolved_citations
from arxiv_int.retrieval.lexical import (
    MAX_LIMIT,
    LexicalHit,
    LexicalRequest,
    LexicalResult,
)
from arxiv_int.retrieval.metrics import SourceSpan
from arxiv_int.retrieval.projection import LexicalTarget
from arxiv_int.retrieval.query_normalization import (
    SELECTED_QUERY_PROFILE,
    query_policy_fingerprint,
)
from arxiv_int.stores.projections.adapters.lexical import TOKENIZER_FINGERPRINT
from arxiv_int.stores.projections.adapters.lexical_search import LexicalFieldError

TARGET = LexicalTarget(
    projection_id="lexical:v1",
    version_id="v1",
    table="search.lexical_p_v1",
    index="lexical_p_v1_bm25",
    row_count=3,
    checksum="abc",
    status="active",
)


def test_request_reports_only_applied_filters() -> None:
    assert LexicalRequest(query="насос").filters() == {}
    assert LexicalRequest(query="насос", language="rus").filters() == {"language": "rus"}
    assert LexicalRequest(query="насос", language="", document_id="d1").filters() == {
        "document_id": "d1"
    }


@pytest.mark.parametrize(
    "kwargs,message",
    (
        ({"query": "   "}, "at least one term"),
        ({"query": "x", "limit": 0}, "limit must be between"),
        ({"query": "x", "limit": MAX_LIMIT + 1}, "limit must be between"),
        ({"query": "x", "offset": -1}, "offset must not be negative"),
        ({"query": "x", "snippet_chars": 0}, "snippet_chars must be positive"),
        ({"query": "x", "facet_limit": 0}, "facet_limit must be between"),
    ),
)
def test_request_refuses_out_of_range_values(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(LexicalFieldError, match=message):
        LexicalRequest(**kwargs)  # type: ignore[arg-type]


def test_result_json_reports_projection_identity_and_facets() -> None:
    hit = LexicalHit(1, "c1", "d1", "Nasos", "rus", 2.5, "[[насос]]")
    result = LexicalResult(TARGET, (hit,), 7, {"language": (("rus", 6), ("eng", 1))}, 1.5)
    payload = result.as_json_dict()
    assert payload["total"] == 7
    assert payload["facets"] == {
        "language": [{"matched": 6, "value": "rus"}, {"matched": 1, "value": "eng"}]
    }
    assert payload["hits"] == [hit.as_json_dict()]
    projection = payload["projection"]
    assert isinstance(projection, dict)
    assert projection["projectionId"] == "lexical:v1"
    assert projection["tokenizerFingerprint"] == TOKENIZER_FINGERPRINT
    assert payload["queryPolicyFingerprint"] == query_policy_fingerprint()
    assert payload["queryProfile"] == SELECTED_QUERY_PROFILE
    assert payload["queryStage"] == "primary"


def test_unresolved_citations_reports_hits_without_a_canonical_chunk() -> None:
    citation = ChunkCitation("c1", "sent-1", SourceSpan("d1", 10, 20))
    assert citation.as_json_dict() == {
        "chunkId": "c1",
        "chunkerId": "sent-1",
        "documentId": "d1",
        "endChar": 20,
        "startChar": 10,
    }
    assert unresolved_citations(["c1", "c2", "c2"], [citation]) == ("c2",)
    assert unresolved_citations([], [citation]) == ()
