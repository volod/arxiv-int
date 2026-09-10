"""Reusable evaluation metrics and evidence guards."""

import math
from collections.abc import Mapping

from arxiv_int.evaluation.scoring.constants import (
    METRIC_CLASS_HELD_OUT,
    METRIC_CLASS_STRUCTURAL,
)
from arxiv_int.evaluation.scoring.errors import MissingEvidenceError
from arxiv_int.evaluation.scoring.linkage import LinkageLabel, score_linkage
from arxiv_int.evaluation.scoring.paired import PairedComparison, paired_verdict
from arxiv_int.evaluation.scoring.payload import as_float, as_items


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
