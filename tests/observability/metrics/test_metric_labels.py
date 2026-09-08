"""Metric labels stay on a bounded name set."""

import pytest

from arxiv_int.observability.metrics import (
    MetricLabelError,
    bind_metric_labels,
    labels_for_snapshot,
)


def test_bind_metric_labels_rejects_run_and_document_ids() -> None:
    with pytest.raises(MetricLabelError, match="high-cardinality"):
        bind_metric_labels({"run_id": "run-1", "stage": "extract"})
    with pytest.raises(MetricLabelError, match="high-cardinality"):
        bind_metric_labels({"stage": "extract", "document_id": "doc"})
    with pytest.raises(MetricLabelError, match="unknown metric labels"):
        bind_metric_labels({"stage": "extract", "hostname": "box-1"})


def test_labels_for_snapshot_are_bounded() -> None:
    labels = labels_for_snapshot("extract", "progress", "running", "cuda:0")
    assert set(labels) == {"stage", "event", "worker_state", "device"}
    assert labels["device"] == "cuda:0"
