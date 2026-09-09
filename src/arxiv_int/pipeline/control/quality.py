"""Activation policy: required quality and exact-generation model results."""

from collections.abc import Sequence
from dataclasses import dataclass

from arxiv_int.data_quality.engine.model import (
    STATUS_FAIL,
    STATUS_NOT_RUN,
    STATUS_PASS,
    STATUS_WARNING,
)
from arxiv_int.interfaces.stores import TransformationRunRef, ValidationResultRef
from arxiv_int.interfaces.tokens import require_token

GLOBAL_SCOPE = "global"
ERROR_SEVERITY = "error"


@dataclass(frozen=True, slots=True)
class QualityCheck:
    """One executed or missing quality check bound into a shard attempt."""

    rule_id: str
    status: str
    scope: str
    severity: str
    required: bool = True

    def __post_init__(self) -> None:
        require_token(self.rule_id, "rule_id")
        require_token(self.status, "status")
        require_token(self.scope, "scope")
        require_token(self.severity, "severity")


@dataclass(frozen=True, slots=True)
class ActivationDecision:
    """Whether a shard may become the active generation for its reuse key."""

    allowed: bool
    quarantined: bool
    warnings: tuple[str, ...]
    blocking: tuple[str, ...]


def activation_decision(
    checks: Sequence[QualityCheck],
    *,
    validations: Sequence[ValidationResultRef] = (),
    transformations: Sequence[TransformationRunRef] = (),
    generation_id: str,
) -> ActivationDecision:
    """Require every applicable check and successful models for this generation."""
    require_token(generation_id, "generation_id")
    warnings, blocking = _quality_findings(checks)
    blocking.extend(_validation_findings(validations, generation_id))
    blocking.extend(_transformation_findings(transformations, generation_id))
    quarantined = bool(warnings) and not blocking
    return ActivationDecision(
        allowed=not blocking,
        quarantined=quarantined,
        warnings=tuple(warnings),
        blocking=tuple(blocking),
    )


def _quality_findings(checks: Sequence[QualityCheck]) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    warnings: list[str] = []
    if not any(item.scope == GLOBAL_SCOPE for item in checks):
        blocking.append("missing global quality checks")
    for check in checks:
        if check.status == STATUS_WARNING:
            warnings.append(check.rule_id)
        if not check.required:
            continue
        if check.status in {STATUS_FAIL, STATUS_NOT_RUN} or check.status not in {
            STATUS_PASS,
            STATUS_WARNING,
        }:
            blocking.append(f"{check.rule_id}:{check.status}")
    return warnings, blocking


def _validation_findings(
    validations: Sequence[ValidationResultRef], generation_id: str
) -> list[str]:
    blocking: list[str] = []
    for validation in validations:
        if validation.generation_id != generation_id:
            blocking.append(f"validation generation {validation.generation_id} != {generation_id}")
        if not validation.publishable:
            blocking.append(f"validation {validation.contract_id} is not publishable")
    return blocking


def _transformation_findings(
    transformations: Sequence[TransformationRunRef], generation_id: str
) -> list[str]:
    blocking: list[str] = []
    for transformation in transformations:
        if transformation.generation_id != generation_id:
            blocking.append(
                f"transform generation {transformation.generation_id} != {generation_id}"
            )
        if not transformation.activatable or transformation.status != "ok":
            blocking.append(f"transform {transformation.run_id} is not activatable")
    return blocking
