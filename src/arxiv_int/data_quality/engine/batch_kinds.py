"""Per-kind handlers for materialized batch quality rules."""

from collections.abc import Callable
from typing import Any

from arxiv_int.contracts.catalog.normalize import is_floating
from arxiv_int.data_quality.engine.model import (
    BACKEND_PANDERA,
    KIND_ACCEPTED_VALUES,
    KIND_BATCH_UNIQUE,
    KIND_DECIMAL,
    KIND_MAX_LENGTH,
    KIND_NULLABILITY,
    KIND_TYPE,
    KIND_UNIT,
    STATUS_FAIL,
    STATUS_PASS,
    CheckResult,
    FailureSample,
    QualityRule,
    ValidationLimits,
    redact_value,
)
from arxiv_int.data_quality.rules.pandera_schema import polars_dtype
from arxiv_int.features import require_module

KindHandler = Callable[[QualityRule, Any, str, ValidationLimits], CheckResult]


def _polars() -> Any:
    return require_module("polars")


def samples_from_frame(
    frame: Any, column: str | None, reason: str, limits: ValidationLimits
) -> tuple[FailureSample, ...]:
    """Return a bounded, redacted sample of failing rows."""
    if frame is None or column is None or frame.height == 0:
        return ()
    samples: list[FailureSample] = []
    for index, row in enumerate(frame.head(limits.failure_samples).iter_rows(named=True)):
        samples.append(
            FailureSample(
                row_ref=f"batch-row:{index}",
                column=column,
                value=redact_value(column, row.get(column), limit=limits.value_chars),
                reason=reason,
            )
        )
    return tuple(samples)


def result(
    rule: QualityRule,
    *,
    status: str,
    checked: int,
    failed: int,
    reason: str | None,
    samples: tuple[FailureSample, ...] = (),
) -> CheckResult:
    """Build a CheckResult for one batch-local rule."""
    return CheckResult(
        rule_id=rule.rule_id,
        status=status,
        scope=rule.scope,
        severity=rule.severity,
        checked_count=checked,
        failed_count=failed,
        description=rule.description,
        backend=BACKEND_PANDERA,
        tool=BACKEND_PANDERA,
        reason=reason,
        samples=samples,
    )


def dtype_ok(actual: Any, expected: Any, rule: QualityRule) -> bool:
    """Compare dtypes, accepting any Decimal width for declared decimal columns."""
    if rule.logical_type == "number" or rule.kind == KIND_DECIMAL:
        if is_floating(rule.physical_type):
            return str(actual) == str(expected)
        return "Decimal" in str(actual)
    return str(actual) == str(expected)


def filter_result(
    rule: QualityRule,
    frame: Any,
    column: str,
    failed_frame: Any,
    *,
    reason: str,
    sample_reason: str,
    limits: ValidationLimits,
) -> CheckResult:
    """Pass or fail from a filtered frame of violating rows."""
    failed = int(failed_frame.height)
    return result(
        rule,
        status=STATUS_FAIL if failed else STATUS_PASS,
        checked=frame.height,
        failed=failed,
        reason=None if failed == 0 else reason,
        samples=samples_from_frame(failed_frame, column, sample_reason, limits),
    )


def check_type(rule: QualityRule, frame: Any, column: str, limits: ValidationLimits) -> CheckResult:
    del limits
    expected = polars_dtype(rule)
    actual = frame.get_column(column).dtype
    ok = dtype_ok(actual, expected, rule)
    return result(
        rule,
        status=STATUS_PASS if ok else STATUS_FAIL,
        checked=frame.height,
        failed=0 if ok else frame.height,
        reason=None if ok else f"{column} has dtype {actual}, expected {expected}",
    )


def check_nullability(
    rule: QualityRule, frame: Any, column: str, limits: ValidationLimits
) -> CheckResult:
    polars = _polars()
    failed_frame = frame.filter(polars.col(column).is_null())
    return filter_result(
        rule,
        frame,
        column,
        failed_frame,
        reason=f"{int(failed_frame.height)} null {column} value(s)",
        sample_reason="null value",
        limits=limits,
    )


def check_max_length(
    rule: QualityRule, frame: Any, column: str, limits: ValidationLimits
) -> CheckResult:
    if rule.max_length is None:
        return result(
            rule,
            status=STATUS_FAIL,
            checked=frame.height,
            failed=0,
            reason=f"unsupported batch rule kind {rule.kind!r}",
        )
    polars = _polars()
    failed_frame = frame.filter(
        polars.col(column).cast(polars.Utf8).str.len_chars() > rule.max_length
    )
    return filter_result(
        rule,
        frame,
        column,
        failed_frame,
        reason=f"{int(failed_frame.height)} {column} value(s) exceed maxLength",
        sample_reason="max length",
        limits=limits,
    )


def check_decimal(
    rule: QualityRule, frame: Any, column: str, limits: ValidationLimits
) -> CheckResult:
    del limits
    expected = polars_dtype(rule)
    actual = frame.get_column(column).dtype
    if not dtype_ok(actual, expected, rule) and "Decimal" not in str(actual):
        return result(
            rule,
            status=STATUS_FAIL,
            checked=frame.height,
            failed=frame.height,
            reason=f"{column} must be decimal, found {actual}",
        )
    return result(rule, status=STATUS_PASS, checked=frame.height, failed=0, reason=None)


def check_accepted_values(
    rule: QualityRule, frame: Any, column: str, limits: ValidationLimits
) -> CheckResult:
    polars = _polars()
    allowed = list(rule.accepted_values)
    failed_frame = frame.filter(
        ~polars.col(column).is_in(allowed) & polars.col(column).is_not_null()
    )
    return filter_result(
        rule,
        frame,
        column,
        failed_frame,
        reason=f"{int(failed_frame.height)} {column} value(s) outside accepted values",
        sample_reason="accepted values",
        limits=limits,
    )


def check_unit(rule: QualityRule, frame: Any, column: str, limits: ValidationLimits) -> CheckResult:
    if rule.unit_column is None:
        return result(
            rule,
            status=STATUS_FAIL,
            checked=frame.height,
            failed=0,
            reason=f"unsupported batch rule kind {rule.kind!r}",
        )
    polars = _polars()
    failed_frame = frame.filter(
        polars.col(column).is_not_null() & polars.col(rule.unit_column).is_null()
    )
    return filter_result(
        rule,
        frame,
        column,
        failed_frame,
        reason=f"{int(failed_frame.height)} {column} value(s) missing {rule.unit_column}",
        sample_reason="missing unit",
        limits=limits,
    )


def check_batch_unique(
    rule: QualityRule, frame: Any, column: str, limits: ValidationLimits
) -> CheckResult:
    polars = _polars()
    duplicates = frame.filter(polars.col(column).is_duplicated())
    return filter_result(
        rule,
        frame,
        column,
        duplicates,
        reason=f"{int(duplicates.height)} duplicate {column} value(s) in batch",
        sample_reason="batch duplicate",
        limits=limits,
    )


KIND_HANDLERS: dict[str, KindHandler] = {
    KIND_TYPE: check_type,
    KIND_NULLABILITY: check_nullability,
    KIND_MAX_LENGTH: check_max_length,
    KIND_DECIMAL: check_decimal,
    KIND_ACCEPTED_VALUES: check_accepted_values,
    KIND_UNIT: check_unit,
    KIND_BATCH_UNIQUE: check_batch_unique,
}
