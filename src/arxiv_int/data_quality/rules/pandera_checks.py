"""Pandera Polars adapters for materialized batch checks."""

from collections.abc import Sequence
from typing import Any

from arxiv_int.data_quality.engine.batch_eval import check_batch_rule
from arxiv_int.data_quality.engine.io import refuse_lazyframe
from arxiv_int.data_quality.engine.model import (
    STATUS_FAIL,
    STATUS_NOT_APPLICABLE,
    CheckResult,
    RuleCatalog,
    ValidationLimits,
)
from arxiv_int.data_quality.rules.pandera_schema import polars_dtype, schema_for

__all__ = ["check_batch_rule", "merge_batch_results", "polars_dtype", "run_batch_checks"]


def merge_batch_results(left: CheckResult, right: CheckResult) -> CheckResult:
    """Combine per-batch outcomes for the same rule."""
    failed = left.failed_count + right.failed_count
    status = STATUS_FAIL if failed else left.status
    if left.status == STATUS_NOT_APPLICABLE:
        return right
    if right.status == STATUS_NOT_APPLICABLE:
        return left
    if left.status == STATUS_FAIL or right.status == STATUS_FAIL:
        status = STATUS_FAIL
    samples = (left.samples + right.samples)[:5]
    reason = left.reason or right.reason
    return CheckResult(
        rule_id=left.rule_id,
        status=status,
        scope=left.scope,
        severity=left.severity,
        checked_count=left.checked_count + right.checked_count,
        failed_count=failed,
        description=left.description,
        backend=left.backend,
        tool=left.tool,
        reason=reason,
        samples=samples,
    )


def run_batch_checks(
    catalog: RuleCatalog, batches: Sequence[Any], limits: ValidationLimits
) -> list[CheckResult]:
    """Validate every materialized batch with Pandera and merge per-rule outcomes."""
    schema = schema_for(catalog)
    combined: dict[str, CheckResult] = {}
    for frame in batches:
        refuse_lazyframe(frame)
        try:
            schema.validate(frame)
        except Exception as error:
            if type(error).__name__ not in {"SchemaError", "SchemaErrors"}:
                raise
        for rule in catalog.rules:
            if rule.scope != "batch":
                continue
            outcome = check_batch_rule(rule, frame, limits)
            previous = combined.get(rule.rule_id)
            combined[rule.rule_id] = (
                outcome if previous is None else merge_batch_results(previous, outcome)
            )
    return list(combined.values())
