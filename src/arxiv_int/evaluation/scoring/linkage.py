"""Labelled pair metrics for probabilistic-linkage results."""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinkageLabel:
    """A reviewer's decision for an unordered pair of record identifiers."""

    left_id: str
    right_id: str
    match: bool


@dataclass(frozen=True, slots=True)
class LinkageMetrics:
    """Confusion counts and quality metrics at one operating threshold."""

    threshold: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


def _pair(left: str, right: str) -> tuple[str, str]:
    if left == right:
        raise ValueError("a linkage pair must name two different records")
    return (left, right) if left < right else (right, left)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def score_linkage(
    predicted_matches: Iterable[tuple[str, str]],
    labels: Iterable[LinkageLabel],
    *,
    threshold: float,
) -> LinkageMetrics:
    """Score proposed unordered pairs against reviewed match/non-match labels."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    predicted = {_pair(left, right) for left, right in predicted_matches}
    outcomes = {(True, True): 0, (True, False): 0, (False, True): 0, (False, False): 0}
    seen: set[tuple[str, str]] = set()
    for label in labels:
        pair = _pair(label.left_id, label.right_id)
        if pair in seen:
            raise ValueError(f"duplicate linkage label for pair {pair!r}")
        seen.add(pair)
        outcomes[(pair in predicted, label.match)] += 1
    true_positives = outcomes[(True, True)]
    false_positives = outcomes[(True, False)]
    false_negatives = outcomes[(False, True)]
    precision = _ratio(true_positives, true_positives + false_positives)
    recall = _ratio(true_positives, true_positives + false_negatives)
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return LinkageMetrics(
        threshold,
        true_positives,
        false_positives,
        outcomes[(False, False)],
        false_negatives,
        precision,
        recall,
        f1,
    )
