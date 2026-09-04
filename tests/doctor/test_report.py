"""Tests for accumulated preflight reporting."""

import pytest

from arxiv_int.doctor import PreflightReport


def test_report_accumulates_all_statuses_before_blocking() -> None:
    report = PreflightReport("fixture")
    report.add("python", "ready", "3.12")
    report.add("disk", "degraded", "rotational")
    report.add("model", "blocked", "not cached")

    assert report.status == "blocked"
    assert [finding.name for finding in report.findings] == ["python", "disk", "model"]
    with pytest.raises(RuntimeError, match="model: not cached"):
        report.require_ready()
