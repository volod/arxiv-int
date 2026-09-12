"""Held-out hierarchical, calibration, exception, and resource evaluation."""

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from arxiv_int.classification.model import ClassifierPolicy
from arxiv_int.classification.vocabulary.outcomes import EXCEPTIONAL_OUTCOMES


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Serializable frozen-label metrics and predeclared gate results."""

    metrics: Mapping[str, Any]
    gates: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return all(self.gates.values())

    def as_dict(self) -> dict[str, Any]:
        return {"gates": dict(self.gates), "metrics": dict(self.metrics), "passed": self.passed}


def evaluate(
    labels: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    policy: ClassifierPolicy,
    *,
    split: str | None = "test",
) -> EvaluationReport:
    """Evaluate one immutable prediction snapshot against a non-leaking frozen split."""
    selected = [row for row in labels if split is None or row.get("split") == split]
    if not selected:
        raise ValueError(f"classification evaluation split {split!r} is empty")
    by_occurrence = _unique(predictions, "occurrence_id", "prediction")
    gold = _unique(selected, "item_id", "label")
    missing = sorted(set(gold) - set(by_occurrence))
    if missing:
        raise ValueError(f"classification predictions miss {len(missing)} frozen label(s)")
    pairs = [(gold[key], by_occurrence[key]) for key in sorted(gold)]
    exact = [float(str(left["primary"]) == str(right["primary_class_id"])) for left, right in pairs]
    exact_precision, exact_recall = _exact_label_metrics(pairs)
    precision, recall, distances = zip(
        *(_hierarchy(left, right) for left, right in pairs), strict=True
    )
    hierarchical_precision = sum(precision) / len(precision)
    hierarchical_recall = sum(recall) / len(recall)
    hierarchical_f1 = _f1(hierarchical_precision, hierarchical_recall)
    calibration_error = _calibration_error(pairs)
    exceptional = _exceptional_metrics(pairs)
    runtime = _mapping(manifest.get("runtime"), "classification runtime")
    reproducibility = _mapping(manifest.get("reproducibility"), "reproducibility")
    metrics: dict[str, Any] = {
        "calibration_error": calibration_error,
        "exact_accuracy": sum(exact) / len(exact),
        "exact_f1": _f1(exact_precision, exact_recall),
        "exact_precision": exact_precision,
        "exact_recall": exact_recall,
        "exceptional": exceptional,
        "hierarchical_f1": hierarchical_f1,
        "hierarchical_precision": hierarchical_precision,
        "hierarchical_recall": hierarchical_recall,
        "items": len(pairs),
        "mean_hierarchical_distance": sum(distances) / len(distances),
        "peak_memory_mib": float(runtime.get("peak_memory_mib", 0.0)),
        "selective_coverage": _selective_coverage(pairs),
        "split": split,
        "throughput_files_per_second": float(runtime.get("throughput_files_per_second", 0.0)),
    }
    limits = policy.gates
    gates = {
        "calibration_error": calibration_error <= limits.calibration_error,
        "exact_accuracy": metrics["exact_accuracy"] >= limits.exact_accuracy,
        "exceptional_f1": exceptional["macro_f1"] >= limits.exceptional_f1,
        "hierarchical_distance": (
            metrics["mean_hierarchical_distance"] <= limits.mean_hierarchical_distance
        ),
        "hierarchical_f1": hierarchical_f1 >= limits.hierarchical_f1,
        "peak_memory": metrics["peak_memory_mib"] <= limits.maximum_peak_memory_mib,
        "reproducibility": reproducibility.get("status") == "pass",
        "throughput": (
            metrics["throughput_files_per_second"] >= limits.minimum_throughput_files_per_second
        ),
    }
    metrics["limits"] = asdict(limits)
    return EvaluationReport(metrics, gates)


def _unique(
    rows: Sequence[Mapping[str, Any]], key: str, label: str
) -> dict[str, Mapping[str, Any]]:
    found: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        identity = str(row.get(key) or "")
        if not identity or identity in found:
            raise ValueError(f"{label} {key} values must be non-empty and unique")
        found[identity] = row
    return found


def _path(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return tuple(part for part in str(value or "").split(">") if part)


def _exact_label_metrics(
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> tuple[float, float]:
    precisions = []
    recalls = []
    for gold, prediction in pairs:
        expected = {str(gold["primary"]), *(str(item) for item in gold.get("alternates", []))}
        raw_alternates = prediction.get("alternate_class_ids_json") or "[]"
        parsed = json.loads(str(raw_alternates))
        if not isinstance(parsed, list):
            raise ValueError("prediction alternate classes must be a JSON list")
        actual = {str(prediction["primary_class_id"]), *(str(item) for item in parsed)}
        overlap = len(expected & actual)
        precisions.append(overlap / len(actual))
        recalls.append(overlap / len(expected))
    return sum(precisions) / len(precisions), sum(recalls) / len(recalls)


def _hierarchy(
    gold: Mapping[str, Any], prediction: Mapping[str, Any]
) -> tuple[float, float, float]:
    left = _path(gold.get("path"))
    right = _path(prediction.get("ancestor_path"))
    overlap = len(set(left) & set(right))
    precision = overlap / len(right) if right else 0.0
    recall = overlap / len(left) if left else 0.0
    common = 0
    for expected, actual in zip(left, right, strict=False):
        if expected != actual:
            break
        common += 1
    return precision, recall, float(len(left) + len(right) - 2 * common)


def _calibration_error(pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]]) -> float:
    bins: dict[int, list[tuple[float, float]]] = {}
    for gold, prediction in pairs:
        confidence = min(1.0, max(0.0, float(prediction.get("confidence") or 0.0)))
        correct = float(str(gold["primary"]) == str(prediction["primary_class_id"]))
        bins.setdefault(min(9, int(confidence * 10)), []).append((confidence, correct))
    return sum(
        len(items)
        / len(pairs)
        * abs(sum(conf for conf, _ in items) / len(items) - sum(ok for _, ok in items) / len(items))
        for items in bins.values()
    )


def _exceptional_metrics(
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> dict[str, Any]:
    matrix = Counter(
        f"{gold['primary']}>{prediction['primary_class_id']}" for gold, prediction in pairs
    )
    scores = []
    for outcome in sorted(EXCEPTIONAL_OUTCOMES):
        true_positive = false_positive = false_negative = 0
        for gold, prediction in pairs:
            expected = str(gold["primary"])
            actual = str(prediction["primary_class_id"])
            true_positive += int(expected == outcome and actual == outcome)
            false_positive += int(expected != outcome and actual == outcome)
            false_negative += int(expected == outcome and actual != outcome)
        precision = true_positive / max(1, true_positive + false_positive)
        recall = true_positive / max(1, true_positive + false_negative)
        scores.append(_f1(precision, recall))
    return {"confusion": dict(sorted(matrix.items())), "macro_f1": sum(scores) / len(scores)}


def _selective_coverage(
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> list[dict[str, float]]:
    result = []
    for threshold in (0.0, 0.5, 0.7, 0.9):
        selected = [pair for pair in pairs if float(pair[1].get("confidence") or 0.0) >= threshold]
        accuracy = (
            sum(str(left["primary"]) == str(right["primary_class_id"]) for left, right in selected)
            / len(selected)
            if selected
            else 0.0
        )
        result.append(
            {"accuracy": accuracy, "coverage": len(selected) / len(pairs), "threshold": threshold}
        )
    return result


def _f1(precision: float, recall: float) -> float:
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} is missing from the classification manifest")
    return value
