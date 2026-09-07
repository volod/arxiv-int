"""Evaluate one materialized batch rule against an eager Polars frame."""

from typing import Any

from arxiv_int.data_quality.batch_kinds import KIND_HANDLERS, result
from arxiv_int.data_quality.io import refuse_lazyframe
from arxiv_int.data_quality.model import (
    BACKEND_PANDERA,
    STATUS_FAIL,
    CheckResult,
    QualityRule,
    ValidationLimits,
)
from arxiv_int.data_quality.results import empty_result


def check_batch_rule(rule: QualityRule, frame: Any, limits: ValidationLimits) -> CheckResult:
    """Evaluate one batch-local rule against an eager frame."""
    refuse_lazyframe(frame)
    if frame.height == 0:
        return empty_result(rule, tool=BACKEND_PANDERA, reason="empty dataset")
    column = rule.column
    if column is None or column not in frame.columns:
        return result(
            rule,
            status=STATUS_FAIL,
            checked=frame.height,
            failed=frame.height,
            reason=f"column {column!r} is missing from the batch",
        )
    handler = KIND_HANDLERS.get(rule.kind)
    if handler is None:
        return result(
            rule,
            status=STATUS_FAIL,
            checked=frame.height,
            failed=0,
            reason=f"unsupported batch rule kind {rule.kind!r}",
        )
    return handler(rule, frame, column, limits)
