"""Attach producer-owned ontology and domain rule results without reimplementing them."""

from collections.abc import Sequence
from typing import Any

from arxiv_int.data_quality.engine.model import (
    BACKEND_ONTOLOGY,
    KIND_SEMANTIC,
    SCOPE_SNAPSHOT,
    SEVERITY_ERROR,
    STATUS_FAIL,
    STATUS_NOT_RUN,
    STATUS_PASS,
    CheckResult,
    FailureSample,
    QualityRule,
)
from arxiv_int.data_quality.engine.results import not_run_result

FACTS_ONTOLOGY_RULE = "facts.ontology.assertions"
DOMAIN_RULE_SUFFIX = ".ontology.domain-rules"
SHACL_RULE_SUFFIX = ".ontology.shacl"


def semantic_rule(rule_id: str, description: str) -> QualityRule:
    """Return a producer-attached semantic rule identity."""
    return QualityRule(
        rule_id=rule_id,
        kind=KIND_SEMANTIC,
        scope=SCOPE_SNAPSHOT,
        backend=BACKEND_ONTOLOGY,
        severity=SEVERITY_ERROR,
        required=True,
        description=description,
        dbt_test=None,
        disk_backend=None,
    )


def missing_semantic_result(rule: QualityRule) -> CheckResult:
    """Mark a required semantic check that a producer did not attach."""
    return not_run_result(
        rule,
        "producer did not attach this semantic check; unexecuted required checks cannot pass",
        tool=BACKEND_ONTOLOGY,
    )


def from_ontology_findings(
    rule: QualityRule,
    findings: Sequence[str],
    *,
    checked_count: int,
    sample_limit: int = 5,
) -> CheckResult:
    """Adapt existing ontology/domain validator findings into a typed check result."""
    failed = len(findings)
    samples = tuple(
        FailureSample(row_ref="ontology", column=None, value="<redacted>", reason=finding)
        for finding in findings[:sample_limit]
    )
    return CheckResult(
        rule_id=rule.rule_id,
        status=STATUS_FAIL if failed else STATUS_PASS,
        scope=rule.scope,
        severity=rule.severity,
        checked_count=checked_count,
        failed_count=failed,
        description=rule.description,
        backend=BACKEND_ONTOLOGY,
        tool=BACKEND_ONTOLOGY,
        reason=None if failed == 0 else f"{failed} ontology/domain finding(s)",
        samples=samples,
    )


def fact_assertion_result(
    assertions: Sequence[Any],
    catalog: Any,
    *,
    rule_id: str = FACTS_ONTOLOGY_RULE,
) -> CheckResult:
    """Reuse application ontology validation for fact-shaped rows."""
    from arxiv_int.ontology.validate import validate_assertions

    rule = semantic_rule(rule_id, "Fact assertions must satisfy ontology domain and range rules.")
    findings = validate_assertions(catalog, tuple(assertions))
    return from_ontology_findings(rule, findings, checked_count=len(tuple(assertions)))


def domain_rule_result(
    assertions: Sequence[Any],
    catalog: Any,
    *,
    contract_id: str,
    bom_lines: Sequence[Any] = (),
    allocations: Sequence[Any] = (),
    registry_rows: Sequence[Any] = (),
) -> CheckResult:
    """Reuse domain investigation rules for artifact-shaped rows."""
    from arxiv_int.ontology.domain_rules import validate_domain_assertions

    rule = semantic_rule(
        f"{contract_id}{DOMAIN_RULE_SUFFIX}",
        "Domain artifact rows must satisfy reviewed domain investigation rules.",
    )
    findings = validate_domain_assertions(
        catalog,
        tuple(assertions),
        bom_lines=tuple(bom_lines),
        allocations=tuple(allocations),
        registry_rows=tuple(registry_rows),
    )
    return from_ontology_findings(rule, findings, checked_count=len(tuple(assertions)))


def shacl_not_run(contract_id: str) -> CheckResult:
    """SHACL remains producer-attached; absence is an explicit not-run result."""
    rule = semantic_rule(
        f"{contract_id}{SHACL_RULE_SUFFIX}",
        "SHACL graph validation is owned by ontology producers and must be attached.",
    )
    return CheckResult(
        rule_id=rule.rule_id,
        status=STATUS_NOT_RUN,
        scope=rule.scope,
        severity=rule.severity,
        checked_count=0,
        failed_count=0,
        description=rule.description,
        backend=BACKEND_ONTOLOGY,
        tool=BACKEND_ONTOLOGY,
        reason="SHACL validation was not attached by the producer",
    )
