"""Aggregate typed check results, fingerprints, and publication eligibility."""

from collections.abc import Sequence

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.data_quality.engine.model import (
    STATUS_FAIL,
    STATUS_NOT_APPLICABLE,
    STATUS_NOT_RUN,
    STATUS_PASS,
    STATUS_WARNING,
    VALIDATION_DEPTH_DATA,
    VALIDATION_DEPTH_SCHEMA_ONLY,
    CheckResult,
    DatasetValidationResult,
    QualityRule,
    RuleCatalog,
    ToolFingerprint,
    ValidationLimits,
)


def catalog_fingerprint(catalog: RuleCatalog) -> str:
    """Fingerprint the stable rule identities and descriptions."""
    payload = "|".join(
        f"{rule.rule_id}:{rule.kind}:{rule.scope}:{rule.description}" for rule in catalog.rules
    )
    return sha256_text(payload)


def input_fingerprint(parts: Sequence[str]) -> str:
    """Fingerprint declared input identities without embedding path secrets."""
    return sha256_text("|".join(parts))


def overall_status(checks: Sequence[CheckResult], missing_required: Sequence[str]) -> str:
    """Combine executed and missing required checks into one dataset status."""
    if any(item.status == STATUS_FAIL for item in checks) or missing_required:
        if missing_required and not any(item.status == STATUS_FAIL for item in checks):
            return STATUS_NOT_RUN
        if missing_required:
            return STATUS_FAIL
        return STATUS_FAIL
    if any(item.status == STATUS_NOT_RUN and _required_result(item) for item in checks):
        return STATUS_NOT_RUN
    if any(item.status == STATUS_WARNING for item in checks):
        return STATUS_WARNING
    if checks and all(item.status == STATUS_NOT_APPLICABLE for item in checks):
        return STATUS_NOT_APPLICABLE
    return STATUS_PASS


def _required_result(item: CheckResult) -> bool:
    return item.severity == "error"


def is_publishable(
    *,
    status: str,
    validation_depth: str,
    missing_required: Sequence[str],
    checks: Sequence[CheckResult],
) -> bool:
    """A dataset is publishable only after required data checks executed and passed."""
    if validation_depth != VALIDATION_DEPTH_DATA:
        return False
    if missing_required:
        return False
    if status not in {STATUS_PASS, STATUS_NOT_APPLICABLE}:
        return False
    for item in checks:
        if item.severity != "error":
            continue
        if item.status == STATUS_NOT_RUN:
            return False
        if item.status == STATUS_FAIL:
            return False
    return True


def missing_required_ids(catalog: RuleCatalog, executed: Sequence[CheckResult]) -> tuple[str, ...]:
    """Return required rule ids that are absent or were not executed."""
    by_id = {item.rule_id: item for item in executed}
    missing: list[str] = []
    for rule in catalog.required_rules():
        item = by_id.get(rule.rule_id)
        if item is None or item.status == STATUS_NOT_RUN:
            missing.append(rule.rule_id)
    return tuple(missing)


def not_run_result(rule: QualityRule, reason: str, *, tool: str) -> CheckResult:
    """Mark a required check as declared but unexecuted."""
    return CheckResult(
        rule_id=rule.rule_id,
        status=STATUS_NOT_RUN,
        scope=rule.scope,
        severity=rule.severity,
        checked_count=0,
        failed_count=0,
        description=rule.description,
        backend=rule.backend,
        tool=tool,
        reason=reason,
    )


def empty_result(rule: QualityRule, *, tool: str, reason: str) -> CheckResult:
    """Record a not-applicable outcome for empty input."""
    return CheckResult(
        rule_id=rule.rule_id,
        status=STATUS_NOT_APPLICABLE,
        scope=rule.scope,
        severity=rule.severity,
        checked_count=0,
        failed_count=0,
        description=rule.description,
        backend=rule.backend,
        tool=tool,
        reason=reason,
    )


def build_result(
    catalog: RuleCatalog,
    checks: Sequence[CheckResult],
    *,
    checked_rows: int,
    input_fingerprint_value: str,
    tool_fingerprint: ToolFingerprint,
    limits: ValidationLimits,
    validation_depth: str = VALIDATION_DEPTH_DATA,
    reason: str | None = None,
    artifact_dir: str | None = None,
) -> DatasetValidationResult:
    """Assemble a typed result, filling missing required checks as not-run."""
    by_id = {item.rule_id: item for item in checks}
    ordered: list[CheckResult] = []
    for rule in catalog.rules:
        existing = by_id.get(rule.rule_id)
        if existing is None:
            ordered.append(
                not_run_result(rule, "required check was not executed", tool=rule.backend)
            )
        else:
            ordered.append(existing)
    for item in checks:
        if item.rule_id not in catalog.by_id():
            ordered.append(item)
    missing = missing_required_ids(catalog, ordered)
    if validation_depth == VALIDATION_DEPTH_SCHEMA_ONLY:
        status = STATUS_FAIL
        depth_reason = reason or "LazyFrame schema-only validation cannot count as data validation"
        return DatasetValidationResult(
            contract_id=catalog.contract_id,
            status=status,
            validation_depth=validation_depth,
            publishable=False,
            checked_rows=checked_rows,
            input_fingerprint=input_fingerprint_value,
            catalog_fingerprint=catalog_fingerprint(catalog),
            tool_fingerprint=tool_fingerprint,
            checks=tuple(ordered),
            missing_required=missing,
            limits=limits,
            reason=depth_reason,
            artifact_dir=artifact_dir,
        )
    status = overall_status(ordered, missing)
    publishable = is_publishable(
        status=status,
        validation_depth=validation_depth,
        missing_required=missing,
        checks=ordered,
    )
    return DatasetValidationResult(
        contract_id=catalog.contract_id,
        status=status,
        validation_depth=validation_depth,
        publishable=publishable,
        checked_rows=checked_rows,
        input_fingerprint=input_fingerprint_value,
        catalog_fingerprint=catalog_fingerprint(catalog),
        tool_fingerprint=tool_fingerprint,
        checks=tuple(ordered),
        missing_required=missing,
        limits=limits,
        reason=reason,
        artifact_dir=artifact_dir,
    )
