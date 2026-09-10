"""Span extraction, hierarchical classification, retrieval, and latency metrics."""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from arxiv_int.evaluation.scoring.constants import EXCEPTIONAL_CLASSES, LATENCY_P95, RETRIEVAL_K
from arxiv_int.evaluation.scoring.errors import MissingEvidenceError
from arxiv_int.evaluation.scoring.metrics import extraction_metrics
from arxiv_int.evaluation.scoring.payload import as_int, as_maps, as_str, as_strings
from arxiv_int.retrieval.metrics import (
    RetrievalCase,
    RetrievedChunk,
    SourceSpan,
    evaluate_retrieval,
)


@dataclass(frozen=True, slots=True)
class SpanScore:
    """Exact-span extraction quality for one item."""

    precision: float
    recall: float
    f1: float
    matched: int


@dataclass(frozen=True, slots=True)
class ClassificationScore:
    """Exact and ancestor-aware hierarchical classification quality."""

    exact: float
    hierarchical_precision: float
    hierarchical_recall: float
    exceptional: float


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def _span_key(payload: Mapping[str, object]) -> tuple[str, int, int]:
    return (
        as_str(payload.get("document_id")),
        as_int(payload.get("start")),
        as_int(payload.get("end")),
    )


def score_spans(
    predicted: Sequence[Mapping[str, object]], expected: Sequence[Mapping[str, object]]
) -> SpanScore:
    """Score exact document/offset spans as sets."""
    predicted_keys = {_span_key(item) for item in predicted}
    expected_keys = {_span_key(item) for item in expected}
    matched = len(predicted_keys & expected_keys)
    precision = _ratio(matched, len(predicted_keys))
    recall = _ratio(matched, len(expected_keys))
    return SpanScore(precision, recall, _f1(precision, recall), matched)


def score_extraction_item(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    """Score extracted strings, spans, and quarantine agreement."""
    expected = as_strings(gold.get("expected"))
    predicted = as_strings(prediction.get("predicted"))
    identity = extraction_metrics(predicted, expected)
    spans = score_spans(as_maps(prediction.get("spans")), as_maps(gold.get("anchors")))
    gold_failure = gold.get("failure")
    pred_failure = prediction.get("failure")
    failure_ok = float(gold_failure == pred_failure)
    return {
        "extraction_f1": identity.f1,
        "failure_agreement": failure_ok,
        "span_f1": spans.f1,
    }


def score_classification(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> ClassificationScore:
    """Score a hierarchical path, including exceptional outcomes."""
    gold_path = as_strings(gold.get("path"))
    pred_path = as_strings(prediction.get("path"))
    gold_primary = as_str(gold.get("primary"))
    pred_primary = as_str(prediction.get("primary"))
    exact = float(gold_path == pred_path and gold_primary == pred_primary)
    gold_set = set(gold_path)
    pred_set = set(pred_path)
    precision = _ratio(len(gold_set & pred_set), len(pred_set))
    recall = _ratio(len(gold_set & pred_set), len(gold_set))
    exceptional = 0.0
    if gold_primary in EXCEPTIONAL_CLASSES:
        exceptional = float(pred_primary == gold_primary)
    return ClassificationScore(exact, precision, recall, exceptional)


def _chunk(payload: Mapping[str, object]) -> RetrievedChunk:
    return RetrievedChunk(
        as_str(payload.get("document_id")),
        as_int(payload.get("start")),
        as_int(payload.get("end")),
        as_str(payload.get("text")),
    )


def _span(payload: Mapping[str, object]) -> SourceSpan:
    return SourceSpan(
        as_str(payload.get("document_id")),
        as_int(payload.get("start")),
        as_int(payload.get("end")),
    )


def score_retrieval(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    """Wrap source-span recall@k, MRR, and intactness for one frozen case."""
    k = as_int(gold.get("k"), RETRIEVAL_K) or RETRIEVAL_K
    spans = tuple(_span(item) for item in as_maps(gold.get("spans")))
    chunks = tuple(_chunk(item) for item in as_maps(prediction.get("chunks")))
    metrics = evaluate_retrieval((RetrievalCase(chunks, spans),), k=k)
    return {
        "mean_reciprocal_rank": metrics.mean_reciprocal_rank,
        "recall_at_k": metrics.recall_at_k,
        "span_intact_at_k": metrics.span_intact_at_k,
    }


def percentile(values: Sequence[float], p: float = LATENCY_P95) -> float:
    """Return a nearest-rank percentile; empty input is missing evidence."""
    if not values:
        raise MissingEvidenceError("latency percentile needs at least one sample")
    if not 0.0 < p <= 100.0:
        raise ValueError("percentile must be in (0, 100]")
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100.0 * len(ordered)))
    return float(ordered[rank - 1])
