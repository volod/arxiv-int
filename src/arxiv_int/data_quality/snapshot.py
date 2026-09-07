"""Disk-backed whole-snapshot uniqueness and relationship checks."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arxiv_int.data_quality.io import concat_key_frame
from arxiv_int.data_quality.model import (
    BACKEND_DISK,
    KIND_RELATIONSHIP,
    KIND_UNIQUE,
    STATUS_FAIL,
    STATUS_NOT_APPLICABLE,
    STATUS_NOT_RUN,
    STATUS_PASS,
    CheckResult,
    FailureSample,
    QualityRule,
    RuleCatalog,
    ValidationLimits,
    redact_value,
)
from arxiv_int.features import require_module


def _polars() -> Any:
    return require_module("polars")


def _hash_row(values: Sequence[object]) -> str:
    return "row:" + "|".join("" if item is None else str(item) for item in values)


def _samples(
    frame: Any, columns: Sequence[str], reason: str, limits: ValidationLimits
) -> tuple[FailureSample, ...]:
    samples: list[FailureSample] = []
    for row in frame.head(limits.failure_samples).iter_rows(named=True):
        column = columns[0] if columns else None
        samples.append(
            FailureSample(
                row_ref=_hash_row([row.get(name) for name in columns]),
                column=column,
                value=redact_value(
                    column, row.get(column) if column else None, limit=limits.value_chars
                ),
                reason=reason,
            )
        )
    return tuple(samples)


def spill_keys(frame: Any, destination: Path) -> Path:
    """Write key columns to parquet so uniqueness can scan without holding every batch."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(destination)
    return destination


def check_unique(
    catalog: RuleCatalog,
    rule: QualityRule,
    batches: Sequence[Any],
    *,
    spill_dir: Path,
    limits: ValidationLimits,
    row_count: int,
) -> CheckResult:
    """Find duplicate key values across all materialized batches."""
    if row_count == 0:
        return CheckResult(
            rule_id=rule.rule_id,
            status=STATUS_NOT_APPLICABLE,
            scope=rule.scope,
            severity=rule.severity,
            checked_count=0,
            failed_count=0,
            description=rule.description,
            backend=BACKEND_DISK,
            tool=BACKEND_DISK,
            reason="empty dataset",
        )
    if limits.min_rows > 0 and row_count < limits.min_rows:
        return CheckResult(
            rule_id=rule.rule_id,
            status=STATUS_FAIL,
            scope=rule.scope,
            severity=rule.severity,
            checked_count=row_count,
            failed_count=0,
            description=rule.description,
            backend=BACKEND_DISK,
            tool=BACKEND_DISK,
            reason=f"insufficient rows: {row_count} < min_rows {limits.min_rows}",
        )
    column = rule.column
    if column is None:
        raise ValueError(f"{rule.rule_id}: unique check requires a column")
    keys = concat_key_frame(batches, (column,))
    spill_keys(keys, spill_dir / f"{rule.rule_id}.parquet")
    polars = _polars()
    duplicates = keys.group_by(column).len().filter(polars.col("len") > 1).rename({"len": "count"})
    failed = int(duplicates.height)
    status = STATUS_FAIL if failed else STATUS_PASS
    return CheckResult(
        rule_id=rule.rule_id,
        status=status,
        scope=rule.scope,
        severity=rule.severity,
        checked_count=row_count,
        failed_count=failed,
        description=rule.description,
        backend=BACKEND_DISK,
        tool=BACKEND_DISK,
        reason=None if failed == 0 else f"{failed} duplicate {column} value(s) across batches",
        samples=_samples(duplicates, (column,), "duplicate key", limits),
    )


def check_relationship(
    rule: QualityRule,
    child_batches: Sequence[Any],
    parent_keys: Any | None,
    *,
    limits: ValidationLimits,
    row_count: int,
) -> CheckResult:
    """Require child key values to exist in the related parent key set."""
    if parent_keys is None:
        return CheckResult(
            rule_id=rule.rule_id,
            status=STATUS_NOT_RUN,
            scope=rule.scope,
            severity=rule.severity,
            checked_count=0,
            failed_count=0,
            description=rule.description,
            backend=BACKEND_DISK,
            tool=BACKEND_DISK,
            reason=(
                f"related dataset {rule.target_contract_id} was not provided; "
                "unexecuted global checks cannot pass"
            ),
        )
    column = rule.column
    if column is None:
        raise ValueError(f"{rule.rule_id}: relationship check requires a column")
    if row_count == 0:
        return CheckResult(
            rule_id=rule.rule_id,
            status=STATUS_NOT_APPLICABLE,
            scope=rule.scope,
            severity=rule.severity,
            checked_count=0,
            failed_count=0,
            description=rule.description,
            backend=BACKEND_DISK,
            tool=BACKEND_DISK,
            reason="empty dataset",
        )
    polars = _polars()
    child = concat_key_frame(child_batches, (column,)).filter(polars.col(column).is_not_null())
    parent_column = rule.target_column or column
    parents = parent_keys.select(parent_column).unique()
    missing = child.join(parents, left_on=column, right_on=parent_column, how="anti")
    failed = int(missing.height)
    status = STATUS_FAIL if failed else STATUS_PASS
    return CheckResult(
        rule_id=rule.rule_id,
        status=status,
        scope=rule.scope,
        severity=rule.severity,
        checked_count=int(child.height),
        failed_count=failed,
        description=rule.description,
        backend=BACKEND_DISK,
        tool=BACKEND_DISK,
        reason=None if failed == 0 else f"{failed} broken {column} relationship(s)",
        samples=_samples(missing, (column,), "missing parent key", limits),
    )


def run_snapshot_checks(
    catalog: RuleCatalog,
    batches: Sequence[Any],
    *,
    related: Mapping[str, Any],
    spill_dir: Path,
    limits: ValidationLimits,
    row_count: int,
    execute: bool,
    dbt_results: Mapping[str, CheckResult],
) -> list[CheckResult]:
    """Run disk-backed snapshot checks, or record not-run when execution is skipped."""
    results: list[CheckResult] = []
    for rule in catalog.rules:
        if rule.scope != "snapshot":
            continue
        supplied = dbt_results.get(rule.rule_id)
        if supplied is not None:
            results.append(supplied)
            continue
        if not execute:
            results.append(
                CheckResult(
                    rule_id=rule.rule_id,
                    status=STATUS_NOT_RUN,
                    scope=rule.scope,
                    severity=rule.severity,
                    checked_count=0,
                    failed_count=0,
                    description=rule.description,
                    backend=rule.backend,
                    tool="dbt",
                    reason="declared dbt/disk snapshot check was not executed",
                )
            )
            continue
        if rule.kind == KIND_UNIQUE:
            results.append(
                check_unique(
                    catalog, rule, batches, spill_dir=spill_dir, limits=limits, row_count=row_count
                )
            )
        elif rule.kind == KIND_RELATIONSHIP:
            parent = None
            if rule.target_contract_id is not None:
                parent = related.get(rule.target_contract_id)
            results.append(
                check_relationship(rule, batches, parent, limits=limits, row_count=row_count)
            )
    return results
