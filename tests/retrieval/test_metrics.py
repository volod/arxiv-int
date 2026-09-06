import pytest

from arxiv_int.retrieval.metrics import (
    RetrievalCase,
    RetrievedChunk,
    SourceSpan,
    evaluate_retrieval,
    spans_overlap,
)


def test_overlap_requires_shared_characters_in_one_document() -> None:
    assert spans_overlap(SourceSpan("a", 0, 10), SourceSpan("a", 5, 15))
    assert not spans_overlap(SourceSpan("a", 0, 10), SourceSpan("a", 10, 20))
    assert not spans_overlap(SourceSpan("a", 0, 10), SourceSpan("b", 5, 15))


def test_retrieval_aggregates_rank_coverage_intactness_and_cost() -> None:
    whole = RetrievalCase(
        (RetrievedChunk("a", 0, 100, "x" * 100),),
        (SourceSpan("a", 40, 60),),
    )
    split = RetrievalCase(
        (
            RetrievedChunk("a", 0, 50, "x" * 50),
            RetrievedChunk("a", 50, 100, "x" * 50),
        ),
        (SourceSpan("a", 40, 60),),
    )

    metrics = evaluate_retrieval((whole, split), k=5)

    assert metrics.count == 2
    assert metrics.recall_at_k == 1.0
    assert metrics.mean_reciprocal_rank == 1.0
    assert metrics.span_character_coverage_at_k == 1.0
    assert metrics.span_intact_at_k == 0.5
    assert metrics.mean_served_characters_at_k == 100.0


def test_retrieval_uses_duplicate_occurrences_and_the_k_cut() -> None:
    chunks = (
        RetrievedChunk("a", 0, 10, "first"),
        RetrievedChunk("a", 20, 30, "second", (SourceSpan("b", 100, 200),)),
    )
    case = RetrievalCase(chunks, (SourceSpan("b", 120, 140),))

    top_one = evaluate_retrieval((case,), k=1)
    top_two = evaluate_retrieval((case,), k=2)

    assert top_one.recall_at_k == 0.0
    assert top_two.recall_at_k == 1.0
    assert top_two.mean_reciprocal_rank == 0.5
    assert top_two.span_intact_at_k == 1.0


def test_empty_retrieval_has_zero_evidence_and_validates_k() -> None:
    assert evaluate_retrieval((), k=5).recall_at_k == 0.0
    with pytest.raises(ValueError, match="positive"):
        evaluate_retrieval((), k=0)
