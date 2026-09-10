"""Anomaly cohort, false-positive, review-budget, and resource-cost metrics."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from arxiv_int.evaluation.scoring.accuracy import percentile
from arxiv_int.evaluation.scoring.constants import THRESHOLD_REVIEW_BUDGET
from arxiv_int.evaluation.scoring.errors import MissingEvidenceError
from arxiv_int.evaluation.scoring.payload import as_float, as_int, as_items


@dataclass(frozen=True, slots=True)
class AnomalyScore:
    """Detector operating-point quality for one frozen finding."""

    flagged_match: float
    false_positive: float
    review_needed_match: float
    leakage_refused: float
    insufficient_match: float


@dataclass(frozen=True, slots=True)
class ResourceCost:
    """Recorded resource use for one evaluation or proof run."""

    latency_p95_ms: float
    peak_vram_mib: float
    peak_ram_mib: float
    tokens: int
    disk_bytes: int


def score_anomaly(gold: Mapping[str, object], prediction: Mapping[str, object]) -> AnomalyScore:
    """Score detector flags against cohort labels without promoting leakage."""
    flagged_gold = bool(gold.get("flagged"))
    flagged_pred = bool(prediction.get("flagged"))
    false_positive = float(flagged_pred and not flagged_gold)
    leakage = bool(gold.get("time_leakage"))
    leakage_refused = float(prediction.get("valid") is False) if leakage else 1.0
    if leakage and flagged_pred and prediction.get("valid") is True:
        leakage_refused = 0.0
    insufficient_gold = bool(gold.get("insufficient"))
    insufficient_pred = bool(prediction.get("insufficient"))
    return AnomalyScore(
        flagged_match=float(flagged_gold == flagged_pred),
        false_positive=false_positive,
        review_needed_match=float(
            bool(gold.get("review_needed")) == bool(prediction.get("review_needed"))
        ),
        leakage_refused=leakage_refused,
        insufficient_match=float(insufficient_gold == insufficient_pred),
    )


def review_budget_precision(
    scores: Sequence[AnomalyScore], *, budget: float = THRESHOLD_REVIEW_BUDGET
) -> float:
    """Precision among items that consume the review budget."""
    reviewed = [item for item in scores if item.review_needed_match == 1.0]
    if not reviewed:
        raise MissingEvidenceError("review-budget precision needs reviewed items")
    true_reviews = [item for item in reviewed if item.false_positive == 0.0]
    precision = len(true_reviews) / len(reviewed)
    if budget <= 0.0:
        raise ValueError("review budget must be positive")
    return precision


def score_resource(prediction: Mapping[str, object]) -> ResourceCost:
    """Read resource fields; missing latency samples refuse a p95."""
    latencies = prediction.get("latencies_ms") or prediction.get("latency_ms")
    samples: tuple[float, ...]
    if isinstance(latencies, (int, float)) and not isinstance(latencies, bool):
        samples = (float(latencies),)
    elif isinstance(latencies, list) and latencies:
        samples = tuple(as_float(value) for value in as_items(latencies))
    else:
        raise MissingEvidenceError("resource cost needs latency samples")
    return ResourceCost(
        latency_p95_ms=percentile(samples),
        peak_vram_mib=as_float(prediction.get("peak_vram_mib")),
        peak_ram_mib=as_float(prediction.get("peak_ram_mib")),
        tokens=as_int(prediction.get("tokens")),
        disk_bytes=as_int(prediction.get("disk_bytes")),
    )


def resource_metrics(cost: ResourceCost) -> dict[str, float]:
    """Flatten resource cost for bundle metrics."""
    return {
        "disk_bytes": float(cost.disk_bytes),
        "latency_p95_ms": cost.latency_p95_ms,
        "peak_ram_mib": cost.peak_ram_mib,
        "peak_vram_mib": cost.peak_vram_mib,
        "tokens": float(cost.tokens),
    }
