"""Pure extraction and reference-text metrics."""

import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractionMetrics:
    """Set-style extraction counts and their precision, recall, and F1."""

    expected: int
    predicted: int
    matched: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True, slots=True)
class TextMetrics:
    """Normalized exact and bag-of-token overlap for one predicted value."""

    exact: float
    precision: float
    recall: float
    f1: float


def normalize_text(text: str) -> str:
    """Normalize case, compatibility forms, punctuation, symbols, and whitespace."""
    normalized: list[str] = []
    for character in unicodedata.normalize("NFKC", text):
        category = unicodedata.category(character)
        if category[0] in {"P", "S"}:
            normalized.append(" ")
        elif category[0] != "C":
            normalized.append(character.lower())
    return " ".join("".join(normalized).split())


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def extraction_metrics(predicted: Iterable[str], expected: Iterable[str]) -> ExtractionMetrics:
    """Score extracted identities as multisets, so duplicate output is penalized."""
    predicted_counts = Counter(predicted)
    expected_counts = Counter(expected)
    matched = sum((predicted_counts & expected_counts).values())
    predicted_total = sum(predicted_counts.values())
    expected_total = sum(expected_counts.values())
    precision = _ratio(matched, predicted_total)
    recall = _ratio(matched, expected_total)
    return ExtractionMetrics(
        expected=expected_total,
        predicted=predicted_total,
        matched=matched,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
    )


def text_metrics(prediction: str, reference: str) -> TextMetrics:
    """Score one text value with normalized exact match and token overlap."""
    predicted = normalize_text(prediction).split()
    expected = normalize_text(reference).split()
    overlap = sum((Counter(predicted) & Counter(expected)).values())
    precision = _ratio(overlap, len(predicted))
    recall = _ratio(overlap, len(expected))
    exact = float(bool(expected) and predicted == expected)
    return TextMetrics(exact, precision, recall, _f1(precision, recall))
