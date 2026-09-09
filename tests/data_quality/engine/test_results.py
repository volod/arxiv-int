"""Typed result publication rules."""

from arxiv_int.data_quality.engine.model import (
    STATUS_FAIL,
    STATUS_NOT_RUN,
    STATUS_PASS,
    VALIDATION_DEPTH_DATA,
    VALIDATION_DEPTH_SCHEMA_ONLY,
    CheckResult,
)
from arxiv_int.data_quality.engine.results import is_publishable


def _check(status: str, *, severity: str = "error") -> CheckResult:
    return CheckResult(
        rule_id="documents.document_id.unique",
        status=status,
        scope="snapshot",
        severity=severity,
        checked_count=1,
        failed_count=1 if status == STATUS_FAIL else 0,
        description="unique",
        backend="disk",
        tool="disk",
    )


def test_missing_or_unexecuted_required_checks_are_not_publishable() -> None:
    assert (
        is_publishable(
            status=STATUS_NOT_RUN,
            validation_depth=VALIDATION_DEPTH_DATA,
            missing_required=("documents.document_id.unique",),
            checks=(_check(STATUS_NOT_RUN),),
        )
        is False
    )


def test_schema_only_depth_is_not_publishable() -> None:
    assert (
        is_publishable(
            status=STATUS_PASS,
            validation_depth=VALIDATION_DEPTH_SCHEMA_ONLY,
            missing_required=(),
            checks=(_check(STATUS_PASS),),
        )
        is False
    )


def test_failed_required_check_is_not_publishable() -> None:
    assert (
        is_publishable(
            status=STATUS_FAIL,
            validation_depth=VALIDATION_DEPTH_DATA,
            missing_required=(),
            checks=(_check(STATUS_FAIL),),
        )
        is False
    )


def test_executed_pass_is_publishable() -> None:
    assert (
        is_publishable(
            status=STATUS_PASS,
            validation_depth=VALIDATION_DEPTH_DATA,
            missing_required=(),
            checks=(_check(STATUS_PASS),),
        )
        is True
    )
