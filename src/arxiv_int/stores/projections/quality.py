"""Shared quality results that gate projection activation."""

from collections.abc import Sequence

from arxiv_int.data_quality.model import (
    BACKEND_DISK,
    KIND_SEMANTIC,
    SCOPE_SNAPSHOT,
    SEVERITY_ERROR,
    STATUS_FAIL,
    STATUS_NOT_APPLICABLE,
    STATUS_PASS,
    VALIDATION_DEPTH_DATA,
    CheckResult,
    DatasetValidationResult,
    QualityRule,
    RuleCatalog,
    ToolFingerprint,
    ValidationLimits,
)
from arxiv_int.data_quality.results import build_result, input_fingerprint

TOOL_PROJECTION = "projection"
CATALOG_VERSION = "1.0.0"

RULE_ROW_COUNT = "projection.row_count"
RULE_CHECKSUM = "projection.logical_id_checksum"
RULE_PARITY = "projection.sampled_parity"
RULE_ENGINE = "projection.engine_object"


def projection_catalog(kind: str) -> RuleCatalog:
    """Return required lifecycle checks for one projection kind."""
    rules = (
        _rule(RULE_ROW_COUNT, f"{kind} row count matches the relational input"),
        _rule(RULE_CHECKSUM, f"{kind} logical ids are complete and ordered"),
        _rule(RULE_PARITY, f"{kind} sampled SQL or Cypher paths match the reference"),
        _rule(RULE_ENGINE, f"{kind} engine object exists after the staging build"),
    )
    return RuleCatalog(
        contract_id=f"projection-{kind}",
        odcs_id=f"urn:arxiv-int:projection:{kind}:1.0.0",
        version=CATALOG_VERSION,
        description=f"Lifecycle checks for rebuildable {kind} projections",
        schema_name="search",
        table_name=kind,
        primary_key=("logical_id",),
        rules=rules,
    )


def check_result(
    rule_id: str,
    *,
    status: str,
    checked_count: int,
    failed_count: int = 0,
    reason: str | None = None,
) -> CheckResult:
    """Build one executed lifecycle check result."""
    return CheckResult(
        rule_id=rule_id,
        status=status,
        scope=SCOPE_SNAPSHOT,
        severity=SEVERITY_ERROR,
        checked_count=checked_count,
        failed_count=failed_count,
        description=rule_id,
        backend=BACKEND_DISK,
        tool=TOOL_PROJECTION,
        reason=reason,
    )


def pass_fail(ok: bool, *, checked: int, reason: str | None = None) -> str:
    """Return pass or fail from a boolean gate."""
    if ok:
        return STATUS_PASS
    return STATUS_FAIL


def not_applicable(rule_id: str, reason: str) -> CheckResult:
    """Record a required check that does not apply in this engine mode."""
    return check_result(rule_id, status=STATUS_NOT_APPLICABLE, checked_count=0, reason=reason)


def assemble_result(
    kind: str,
    checks: Sequence[CheckResult],
    *,
    checked_rows: int,
    fingerprint_parts: Sequence[str],
) -> DatasetValidationResult:
    """Assemble a typed result that cannot look publishable when a required check failed."""
    return build_result(
        projection_catalog(kind),
        checks,
        checked_rows=checked_rows,
        input_fingerprint_value=input_fingerprint(fingerprint_parts),
        tool_fingerprint=ToolFingerprint({TOOL_PROJECTION: CATALOG_VERSION}),
        limits=ValidationLimits(),
        validation_depth=VALIDATION_DEPTH_DATA,
    )


def evidence_maps(result: DatasetValidationResult) -> tuple[dict[str, object], ...]:
    """Return relational evidence rows from one typed quality result."""
    rows: list[dict[str, object]] = []
    for item in result.checks:
        rows.append(
            {
                "check_name": item.rule_id,
                "status": item.status,
                "detail": item.reason,
                "checked_count": item.checked_count,
                "failed_count": item.failed_count,
            }
        )
    return tuple(rows)


def _rule(rule_id: str, description: str) -> QualityRule:
    return QualityRule(
        rule_id=rule_id,
        kind=KIND_SEMANTIC,
        scope=SCOPE_SNAPSHOT,
        backend=BACKEND_DISK,
        severity=SEVERITY_ERROR,
        required=True,
        description=description,
    )
