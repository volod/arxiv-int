"""Chunk-level quality, precision, and gate readings for one arm and case."""

import math
from collections.abc import Iterable, Mapping, Sequence

from arxiv_int.retrieval.metrics import (
    RetrievalCase,
    RetrievedChunk,
    SourceSpan,
    evaluate_retrieval,
)
from arxiv_int.retrieval.second_opinion.model import CaseRun, CaseScore, SplitCase, SplitChunk


def score_case(
    case: SplitCase,
    run: CaseRun,
    chunks: Mapping[str, SplitChunk],
    *,
    k_quality: int,
    k_precision: int,
) -> CaseScore:
    """Score one arm's ranked chunk identities against the case's judgments.

    Returned precision counts every non-relevant returned chunk, judged or not, and an
    empty result is fully precise. A no-answer case is a false positive when anything
    is returned within the precision cutoff.
    """
    relevant = set(case.relevant)
    top_quality = run.hits[:k_quality]
    top_precision = run.hits[:k_precision]
    found = [chunk_id for chunk_id in top_precision if chunk_id in relevant]
    judged = relevant | set(case.hard_negatives) | set(case.forbidden)
    return CaseScore(
        arm_id=run.arm_id,
        case_id=case.case_id,
        cohort=case.cohort,
        ndcg=ndcg(top_quality, relevant, k_quality),
        recall=(
            len(relevant & set(top_quality)) / len(relevant) if relevant else float(not top_quality)
        ),
        reciprocal_rank=_reciprocal_rank(run.hits, relevant),
        precision=len(found) / len(top_precision) if top_precision else 1.0,
        intact=_intact(case, top_quality, chunks, k_quality),
        false_positive=not relevant and bool(top_precision),
        hard_negatives=sum(1 for item in top_precision if item in case.hard_negatives),
        forbidden_hits=sum(1 for item in run.hits if item in case.forbidden),
        unjudged=sum(1 for item in top_precision if item not in judged),
        exact=set(run.hits) == relevant and not run.error,
    )


def ndcg(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """Binary-gain nDCG at ``k``; a no-answer case scores 1.0 only when nothing is returned."""
    if not relevant:
        return float(not ranked[:k])
    gain = sum(
        1.0 / math.log2(rank + 2) for rank, item in enumerate(ranked[:k]) if item in relevant
    )
    ideal = sum(1.0 / math.log2(rank + 2) for rank in range(min(len(relevant), k)))
    return gain / ideal


def mean(values: Iterable[float]) -> float:
    """Return the arithmetic mean, or 0.0 for no values."""
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def _reciprocal_rank(hits: Sequence[str], relevant: set[str]) -> float:
    return next((1.0 / rank for rank, item in enumerate(hits, 1) if item in relevant), 0.0)


def _intact(
    case: SplitCase, ranked: Sequence[str], chunks: Mapping[str, SplitChunk], k: int
) -> float:
    if not case.relevant:
        return 1.0
    retrieved = tuple(
        RetrievedChunk(item.document_id, item.start_char, item.end_char, item.body)
        for chunk_id in ranked
        if (item := chunks.get(chunk_id)) is not None
    )
    spans = tuple(
        SourceSpan(item.document_id, item.start_char, item.end_char)
        for chunk_id in case.relevant
        if (item := chunks.get(chunk_id)) is not None
    )
    return evaluate_retrieval((RetrievalCase(retrieved, spans),), k=k).span_intact_at_k
