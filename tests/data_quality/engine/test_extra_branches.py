"""Additional rule, YAML, result, and adapter branches."""

from decimal import Decimal

import polars as pl
import pytest

from arxiv_int.contracts.sqlalchemy.normalize import normalize_contract
from arxiv_int.data_quality.engine import ValidationRequest, validate_catalogs, validate_dataset
from arxiv_int.data_quality.engine.model import (
    KIND_MAX_LENGTH,
    STATUS_NOT_APPLICABLE,
    STATUS_PASS,
    STATUS_WARNING,
    CheckResult,
    DbtEvidence,
    QualityRule,
    ValidationLimits,
    redact_value,
)
from arxiv_int.data_quality.generate import catalog_version
from arxiv_int.data_quality.generate.dbt_yaml import emit_yaml
from arxiv_int.data_quality.rules import UnsupportedQualityMappingError, compile_rule_catalog
from arxiv_int.data_quality.rules.pandera_checks import check_batch_rule, merge_batch_results
from arxiv_int.data_quality.rules.semantic import domain_rule_result
from arxiv_int.resources.paths import ontology_root
from tests.contracts.sqlalchemy._builders import odcs_document, property_field
from tests.data_quality._builders import compile_rows_catalog, decimal_frame, rows_odcs


def test_max_length_and_missing_column_batch_rules() -> None:
    catalog = compile_rows_catalog(amount_options={"precision": 18, "scale": 4})
    rule = QualityRule(
        rule_id="invoice-rows.row_id.max_length",
        kind=KIND_MAX_LENGTH,
        scope="batch",
        backend="pandera",
        severity="error",
        required=True,
        description="short ids",
        column="row_id",
        max_length=1,
    )
    frame = decimal_frame([("too-long", Decimal("1.0000"), "USD", "d1")])
    outcome = check_batch_rule(rule, frame, ValidationLimits())
    assert outcome.status == "fail"
    missing = check_batch_rule(catalog.rules[0], frame.drop("row_id"), ValidationLimits())
    assert missing.status == "fail"


def test_merge_not_applicable_and_warning_status() -> None:
    left = CheckResult(
        rule_id="r",
        status=STATUS_NOT_APPLICABLE,
        scope="batch",
        severity="error",
        checked_count=0,
        failed_count=0,
        description="d",
        backend="pandera",
        tool="pandera",
    )
    right = CheckResult(
        rule_id="r",
        status=STATUS_PASS,
        scope="batch",
        severity="error",
        checked_count=1,
        failed_count=0,
        description="d",
        backend="pandera",
        tool="pandera",
    )
    assert merge_batch_results(left, right).status == STATUS_PASS
    assert merge_batch_results(right, left).status == STATUS_PASS
    warn = CheckResult(
        rule_id="r",
        status=STATUS_WARNING,
        scope="batch",
        severity="warning",
        checked_count=1,
        failed_count=0,
        description="d",
        backend="pandera",
        tool="pandera",
    )
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")]),
            related={"documents": pl.DataFrame({"document_id": ["d1"]})},
            attached=(warn,),
            run_id="warn",
        )
    )
    assert result.status in {"pass", "warning"}
    assert warn.executed is True


def test_declared_quality_shape_errors() -> None:
    document = rows_odcs()
    document["quality"] = {"not": "a-list"}
    tables = (
        normalize_contract(odcs_document(partition_key=None), "documents"),
        normalize_contract(document, "invoice-rows"),
    )
    with pytest.raises(UnsupportedQualityMappingError, match="quality must be a list"):
        compile_rule_catalog(tables[1], tables, document)
    document["quality"] = ["not-a-mapping"]
    with pytest.raises(UnsupportedQualityMappingError, match="must be a mapping"):
        compile_rule_catalog(tables[1], tables, document)


def test_unknown_relationship_target_is_rejected() -> None:
    document = odcs_document(
        contract_id="orphan",
        schema_name="orphan",
        properties=[
            property_field("row_id", primaryKey=True, primaryKeyPosition=1, required=True),
            property_field(
                "missing_id",
                relationships=[{"type": "foreignKey", "to": "no-such-contract.x"}],
            ),
        ],
        partition_key=None,
    )
    table = normalize_contract(document, "orphan")
    with pytest.raises(UnsupportedQualityMappingError, match="not a registered contract"):
        compile_rule_catalog(table, (table,), document)


def test_yaml_empty_nodes_and_catalog_version() -> None:
    assert emit_yaml({}) == "{}\n"
    assert emit_yaml([]) == "[]\n"
    assert catalog_version() == "1.0.0"
    assert redact_value("note", "abcdefghijklmnopqrstuvwxyz", limit=4).endswith("...")


def test_dbt_evidence_and_validate_catalogs() -> None:
    catalog = compile_rows_catalog(amount_options={"precision": 18, "scale": 4})
    unique = next(rule for rule in catalog.rules if rule.kind == "unique")
    evidence = DbtEvidence(
        rule_results={
            unique.rule_id: CheckResult(
                rule_id=unique.rule_id,
                status=STATUS_PASS,
                scope=unique.scope,
                severity=unique.severity,
                checked_count=1,
                failed_count=0,
                description=unique.description,
                backend="dbt",
                tool="dbt",
            )
        },
        executed=True,
    )
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")])
    results = validate_catalogs(
        (
            ValidationRequest(
                catalog=catalog,
                source=frame,
                related={"documents": pl.DataFrame({"document_id": ["d1"]}).lazy()},
                dbt_evidence=evidence,
                run_id="dbt-ev",
            ),
        )
    )
    assert results[0].checks


def test_domain_adapter_returns_a_typed_result() -> None:
    from arxiv_int.ontology.load import load_ontology_catalog

    catalog = load_ontology_catalog(ontology_root())
    outcome = domain_rule_result((), catalog, contract_id="facts")
    assert outcome.status in {"pass", "fail"}
    assert outcome.rule_id.endswith(".ontology.domain-rules")
