"""Deterministic paired bootstrap comparisons and three-way verdicts."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from random import Random
from typing import Literal

DEFAULT_CONFIDENCE = 0.95
DEFAULT_RESAMPLES = 2_000
DEFAULT_SEED = 13

PairedVerdict = Literal["adopt", "retain baseline", "inconclusive"]


@dataclass(frozen=True, slots=True)
class Interval:
    """A point estimate and percentile-bootstrap bounds."""

    mean: float
    low: float
    high: float


@dataclass(frozen=True, slots=True)
class PairedComparison:
    """Candidate-minus-baseline evidence over aligned items."""

    delta: Interval
    wins: int
    losses: int
    ties: int
    sign_test_p: float
    confidence: float
    resamples: int
    seed: int


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _bounds(samples: list[float], confidence: float) -> tuple[float, float]:
    ordered = sorted(samples)
    last = len(ordered) - 1
    tail = (1.0 - confidence) / 2.0
    return ordered[round(tail * last)], ordered[round((1.0 - tail) * last)]


def _sign_test_p(wins: int, losses: int) -> float:
    decided = wins + losses
    if decided == 0:
        return 1.0
    extreme = min(wins, losses)
    tail = sum(math.comb(decided, index) for index in range(extreme + 1)) / (2.0**decided)
    return min(1.0, 2.0 * tail)


def paired_comparison(
    candidate: Sequence[float],
    baseline: Sequence[float],
    *,
    confidence: float = DEFAULT_CONFIDENCE,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> PairedComparison:
    """Compare aligned values using one seeded paired percentile bootstrap."""
    if len(candidate) != len(baseline):
        raise ValueError("paired comparison needs one baseline value per candidate value")
    if not candidate:
        raise ValueError("paired comparison needs at least one item")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    deltas = [
        candidate_value - baseline_value
        for candidate_value, baseline_value in zip(candidate, baseline, strict=True)
    ]
    wins = sum(delta > 0.0 for delta in deltas)
    losses = sum(delta < 0.0 for delta in deltas)
    random = Random(seed)
    samples = [
        _mean([deltas[random.randrange(len(deltas))] for _ in deltas]) for _ in range(resamples)
    ]
    low, high = _bounds(samples, confidence)
    return PairedComparison(
        Interval(_mean(deltas), low, high),
        wins,
        losses,
        len(deltas) - wins - losses,
        _sign_test_p(wins, losses),
        confidence,
        resamples,
        seed,
    )


def paired_verdict(comparison: PairedComparison) -> PairedVerdict:
    """Adopt or retain only when the interval and exact sign test agree."""
    alpha = 1.0 - comparison.confidence
    if comparison.sign_test_p > alpha:
        return "inconclusive"
    if comparison.delta.low > 0.0:
        return "adopt"
    if comparison.delta.high < 0.0:
        return "retain baseline"
    return "inconclusive"
