"""Dispatch frozen items to metrics and refuse verdicts without evidence."""

import math
from collections.abc import Mapping
from typing import Any

from arxiv_int.evaluation.accuracy import (
    score_classification,
    score_extraction_item,
    score_retrieval,
)
from arxiv_int.evaluation.anomaly_eval import score_anomaly
from arxiv_int.evaluation.domain_eval import (
    score_catalog,
    score_domain_artifact,
    score_domain_negative,
    score_graph,
)
from arxiv_int.evaluation.eval_errors import MissingEvidenceError
from arxiv_int.evaluation.fixture_kinds import (
    KIND_ANOMALY,
    KIND_CATALOG,
    KIND_CLASSIFICATION,
    KIND_DOMAIN_ARTIFACT,
    KIND_DOMAIN_NEGATIVE,
    KIND_ENTITY,
    KIND_EXTRACTION,
    KIND_FACT,
    KIND_GEOTEMPORAL,
    KIND_GRAPH,
    KIND_ONTOLOGY,
    KIND_REPORTING,
    KIND_RUSSIAN_RETRIEVAL,
    KIND_SEMANTIC,
    METRIC_CLASS_HELD_OUT,
    METRIC_CLASS_STRUCTURAL,
)
from arxiv_int.evaluation.fixture_model import EvaluationItem
from arxiv_int.evaluation.geo_eval import score_geotemporal, score_ontology
from arxiv_int.evaluation.linkage import LinkageLabel, score_linkage
from arxiv_int.evaluation.paired import PairedComparison, paired_verdict
from arxiv_int.evaluation.payload import as_float, as_items


def _mean(values: Mapping[str, float]) -> float:
    if not values:
        raise MissingEvidenceError("metric vector is empty")
    return sum(values.values()) / len(values)


def score_entity(gold: Mapping[str, object], prediction: Mapping[str, object]) -> dict[str, float]:
    """Score unordered linkage pairs at the recorded threshold."""
    labels = [LinkageLabel(str(gold["left_id"]), str(gold["right_id"]), bool(gold["match"]))]
    predicted = []
    for pair in as_items(prediction.get("predicted_matches")):
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            predicted.append((str(pair[0]), str(pair[1])))
    metrics = score_linkage(predicted, labels, threshold=as_float(prediction.get("threshold"), 0.9))
    pair = tuple(sorted((str(gold["left_id"]), str(gold["right_id"]))))
    predicted_pairs = {tuple(sorted(item)) for item in predicted}
    correct = float((pair in predicted_pairs) == bool(gold["match"]))
    return {
        "correct": correct,
        "f1": metrics.f1,
        "precision": metrics.precision,
        "recall": metrics.recall,
    }


def score_fact(gold: Mapping[str, object], prediction: Mapping[str, object]) -> dict[str, float]:
    """Score fact identity, citation span, and validity."""
    identity = float(
        gold.get("subject_id") == prediction.get("subject_id")
        and gold.get("predicate") == prediction.get("predicate")
        and gold.get("object_id") == prediction.get("object_id")
    )
    valid = float(bool(gold.get("valid")) == bool(prediction.get("valid")))
    span_ok = 1.0
    if isinstance(gold.get("span"), dict) and isinstance(prediction.get("span"), dict):
        span_ok = float(gold.get("span") == prediction.get("span"))
    failure = 1.0
    if "failure" in gold:
        failure = float(gold.get("failure") == prediction.get("failure"))
    return {
        "fact_identity": identity,
        "span_match": span_ok,
        "validity": valid,
        "failure_match": failure,
    }


def score_reporting(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    """Score coverage numerators only when citations exist."""
    cited = float(bool(gold.get("cited")) == bool(prediction.get("cited")))
    coverage = float(gold.get("coverage") == prediction.get("coverage"))
    cited_pred = bool(prediction.get("cited"))
    if gold.get("cited") is True and not cited_pred:
        coverage = 0.0
    return {"cited": cited, "coverage_match": coverage}


def _anomaly_metrics(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    score = score_anomaly(gold, prediction)
    return {
        "flagged_match": score.flagged_match,
        "insufficient_match": score.insufficient_match,
        "leakage_refused": score.leakage_refused,
        "not_false_positive": 1.0 - score.false_positive,
        "review_needed_match": score.review_needed_match,
    }


def _classification_metrics(
    gold: Mapping[str, object], prediction: Mapping[str, object]
) -> dict[str, float]:
    score = score_classification(gold, prediction)
    return {
        "exact": score.exact,
        "exceptional": score.exceptional,
        "hierarchical_precision": score.hierarchical_precision,
        "hierarchical_recall": score.hierarchical_recall,
    }


SCORERS: dict[str, Any] = {
    KIND_ANOMALY: _anomaly_metrics,
    KIND_CATALOG: score_catalog,
    KIND_CLASSIFICATION: _classification_metrics,
    KIND_DOMAIN_ARTIFACT: score_domain_artifact,
    KIND_DOMAIN_NEGATIVE: score_domain_negative,
    KIND_ENTITY: score_entity,
    KIND_EXTRACTION: score_extraction_item,
    KIND_FACT: score_fact,
    KIND_GEOTEMPORAL: score_geotemporal,
    KIND_GRAPH: score_graph,
    KIND_ONTOLOGY: score_ontology,
    KIND_REPORTING: score_reporting,
    KIND_RUSSIAN_RETRIEVAL: score_retrieval,
    KIND_SEMANTIC: score_retrieval,
}


def score_item(item: EvaluationItem, prediction: Mapping[str, object] | None) -> dict[str, float]:
    """Score one item or refuse when the prediction is missing."""
    if prediction is None:
        raise MissingEvidenceError(f"item {item.item_id} has no prediction")
    scorer = SCORERS.get(item.item_kind)
    if scorer is None:
        raise MissingEvidenceError(f"no scorer for item_kind {item.item_kind}")
    return dict(scorer(item.gold, prediction))


def polarity_scores(item: EvaluationItem) -> tuple[float, float]:
    """Return mean scores for the frozen positive and negative predictions."""
    positive = _mean(score_item(item, item.positive))
    negative = _mean(score_item(item, item.negative))
    return positive, negative


def refuse_empty_metrics(metrics: Mapping[str, float]) -> Mapping[str, float]:
    """Refuse a verdict when no finite metric evidence exists."""
    if not metrics:
        raise MissingEvidenceError("metrics are empty")
    for name, value in metrics.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise MissingEvidenceError(f"metric {name} is not finite")
    return metrics


def structural_is_not_accuracy(result: object) -> str:
    """Label Pandera/dbt outcomes as structural, never held-out accuracy."""
    del result
    return METRIC_CLASS_STRUCTURAL


def metric_class_for(*, data_class: str, held_out: bool) -> str:
    """Distinguish transformed/raw data from held-out versus structural metrics."""
    del data_class
    if held_out:
        return METRIC_CLASS_HELD_OUT
    return METRIC_CLASS_STRUCTURAL


def comparison_verdict(comparison: PairedComparison) -> str:
    """Adopt/retain/inconclusive only when the paired interval has evidence."""
    if comparison.wins + comparison.losses + comparison.ties <= 0:
        raise MissingEvidenceError("paired comparison has no items")
    return paired_verdict(comparison)
