"""Tests for accumulated preflight reporting."""

from datetime import UTC, datetime

import pytest

from arxiv_int.readiness import PreflightReport


def test_report_accumulates_all_statuses_before_blocking() -> None:
    report = PreflightReport("fixture")
    report.add("python", "ready", "3.12")
    report.add("disk", "degraded", "rotational")
    report.add("model", "blocked", "not cached")

    assert report.status == "blocked"
    assert report.exit_code == 1
    assert [finding.name for finding in report.findings] == ["python", "disk", "model"]
    assert report.as_dict(generated_at=datetime(2026, 1, 1, tzinfo=UTC))["generated_at"] == (
        "2026-01-01T00:00:00+00:00"
    )
    with pytest.raises(RuntimeError, match="model: not cached"):
        report.require_ready()


def test_ready_report_does_not_raise() -> None:
    report = PreflightReport("fixture")
    report.add("python", "ready", "3.12")

    report.require_ready()
