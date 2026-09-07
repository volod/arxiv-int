"""Rule compilation, unknown rules, and description retention."""

import pytest

from arxiv_int.contracts.sqlalchemy.normalize import normalize_contract
from arxiv_int.data_quality.model import KIND_DECIMAL, KIND_RELATIONSHIP, KIND_UNIQUE, KIND_UNIT
from arxiv_int.data_quality.rules import UnsupportedQualityMappingError, compile_rule_catalog
from tests.contracts.sqlalchemy._builders import odcs_document
from tests.data_quality._builders import compile_rows_catalog, documents_odcs, rows_odcs


def test_compiled_rules_use_stable_ids() -> None:
    catalog = compile_rows_catalog(amount_options={"precision": 18, "scale": 4})
    ids = [rule.rule_id for rule in catalog.rules]
    assert "invoice-rows.row_id.unique" in ids
    assert "invoice-rows.amount.decimal" in ids
    assert "invoice-rows.amount.unit" in ids
    assert "invoice-rows.document_id.relationship" in ids


def test_compiled_rules_retain_scope_and_descriptions() -> None:
    catalog = compile_rows_catalog(amount_options={"precision": 18, "scale": 4})
    unique = next(rule for rule in catalog.rules if rule.kind == KIND_UNIQUE)
    assert unique.scope == "snapshot"
    assert unique.disk_backend == "disk"
    assert unique.dbt_test == "unique"
    decimal = next(rule for rule in catalog.rules if rule.kind == KIND_DECIMAL)
    assert (decimal.precision, decimal.scale) == (18, 4)
    unit = next(rule for rule in catalog.rules if rule.kind == KIND_UNIT)
    assert unit.unit_column == "currency"
    relationship = next(rule for rule in catalog.rules if rule.kind == KIND_RELATIONSHIP)
    assert relationship.target_contract_id == "documents"
    assert "must reference" in relationship.description


def test_unknown_quality_engine_is_rejected() -> None:
    document = rows_odcs(
        quality=[
            {
                "type": "library",
                "engine": "great-expectations",
                "rule": "accepted_values",
                "field": "currency",
                "validValues": ["USD"],
            }
        ]
    )
    tables = (
        normalize_contract(documents_odcs(), "documents"),
        normalize_contract(document, "invoice-rows"),
    )
    with pytest.raises(UnsupportedQualityMappingError, match="unknown quality engine"):
        compile_rule_catalog(tables[1], tables, document)


def test_unknown_quality_rule_is_rejected() -> None:
    document = rows_odcs(
        quality=[
            {
                "type": "library",
                "engine": "pandera",
                "rule": "expect_foo",
                "field": "currency",
                "validValues": ["USD"],
            }
        ]
    )
    tables = (
        normalize_contract(documents_odcs(), "documents"),
        normalize_contract(document, "invoice-rows"),
    )
    with pytest.raises(UnsupportedQualityMappingError, match="unknown quality rule"):
        compile_rule_catalog(tables[1], tables, document)


def test_accepted_values_quality_is_compiled() -> None:
    catalog = compile_rows_catalog(
        quality=[
            {
                "type": "library",
                "engine": "pandera",
                "rule": "accepted_values",
                "field": "currency",
                "validValues": ["USD", "EUR"],
                "description": "ISO currency codes only.",
            }
        ]
    )
    rule = next(item for item in catalog.rules if item.kind == "accepted_values")
    assert rule.accepted_values == ("USD", "EUR")
    assert rule.description == "ISO currency codes only."


def test_unknown_quality_type_is_rejected() -> None:
    document = rows_odcs(
        quality=[
            {
                "type": "sql",
                "engine": "pandera",
                "rule": "accepted_values",
                "field": "currency",
                "validValues": ["USD"],
            }
        ]
    )
    tables = (
        normalize_contract(documents_odcs(), "documents"),
        normalize_contract(document, "invoice-rows"),
    )
    with pytest.raises(UnsupportedQualityMappingError, match="unknown quality type"):
        compile_rule_catalog(tables[1], tables, document)


def test_unknown_quality_field_and_empty_values_are_rejected() -> None:
    document = rows_odcs(
        quality=[
            {
                "type": "library",
                "engine": "pandera",
                "rule": "accepted_values",
                "field": "nope",
                "validValues": ["USD"],
            }
        ]
    )
    tables = (
        normalize_contract(documents_odcs(), "documents"),
        normalize_contract(document, "invoice-rows"),
    )
    with pytest.raises(UnsupportedQualityMappingError, match="not a contract column"):
        compile_rule_catalog(tables[1], tables, document)
    document = rows_odcs(
        quality=[
            {
                "type": "library",
                "engine": "pandera",
                "rule": "accepted_values",
                "field": "currency",
                "validValues": [],
            }
        ]
    )
    tables = (
        normalize_contract(documents_odcs(), "documents"),
        normalize_contract(document, "invoice-rows"),
    )
    with pytest.raises(UnsupportedQualityMappingError, match="non-empty list"):
        compile_rule_catalog(tables[1], tables, document)


def test_partition_key_is_not_a_global_unique_rule() -> None:
    table = normalize_contract(odcs_document(), "documents")
    catalog = compile_rule_catalog(table, (table,), odcs_document())
    unique_columns = {rule.column for rule in catalog.rules if rule.kind == KIND_UNIQUE}
    assert "document_id" in unique_columns
    assert "bucket" not in unique_columns
