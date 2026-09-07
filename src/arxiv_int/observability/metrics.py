"""Refuse high-cardinality metric labels; keep only the declared name set."""

from collections.abc import Mapping

from arxiv_int.observability.constants import (
    FORBIDDEN_LABEL_NAMES,
    MAX_LABEL_VALUE_LEN,
    METRIC_LABEL_NAMES,
)


class MetricLabelError(ValueError):
    """A metric label name or value would explode cardinality or leak content."""


def bind_metric_labels(labels: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of labels after enforcing the bounded name and value policy."""
    names = set(labels)
    forbidden = names & FORBIDDEN_LABEL_NAMES
    if forbidden:
        joined = ", ".join(sorted(forbidden))
        raise MetricLabelError(f"metric labels must not include high-cardinality keys: {joined}")
    unknown = names - METRIC_LABEL_NAMES
    if unknown:
        joined = ", ".join(sorted(unknown))
        allowed = ", ".join(sorted(METRIC_LABEL_NAMES))
        raise MetricLabelError(f"unknown metric labels {joined}; allowed: {allowed}")
    bound: dict[str, str] = {}
    for name, value in labels.items():
        if len(value) > MAX_LABEL_VALUE_LEN:
            raise MetricLabelError(f"metric label {name} exceeds {MAX_LABEL_VALUE_LEN} characters")
        if any(char in value for char in ("\n", "\r", "/", " ")) and not (
            name == "device" and value.startswith("cuda:")
        ):
            raise MetricLabelError(f"metric label {name} has a non-token value")
        bound[name] = value
    return bound


def labels_for_snapshot(stage: str, event: str, worker_state: str, device: str) -> dict[str, str]:
    """Build the only labels attached to a progress metric point."""
    return bind_metric_labels(
        {
            "stage": stage,
            "event": event,
            "worker_state": worker_state,
            "device": device,
        }
    )
