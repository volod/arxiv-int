"""Metadata building, collision refusal, and deterministic review DDL."""

from pathlib import Path

import pytest

from arxiv_int.contracts.sqlalchemy import (
    baseline_ddl,
    build_metadata,
    contract_ddl,
    load_schema_model_from_root,
)
from arxiv_int.contracts.sqlalchemy.normalize import (
    UnsupportedContractMappingError,
    normalize_contract,
)
from arxiv_int.quality.project_root import discover_project_root
from tests.contracts.sqlalchemy._builders import odcs_document, property_field


def _contracts_root() -> Path:
    return discover_project_root(Path(__file__)) / "contracts"


def test_product_metadata_is_schema_qualified_with_named_constraints() -> None:
    model = load_schema_model_from_root(_contracts_root())
    table = model.metadata.tables["kg.transactions"]
    assert table.schema == "kg"
    assert table.primary_key.name == "pk_transactions"
    targets = {
        constraint.name: constraint.elements[0].target_fullname
        for constraint in table.foreign_key_constraints
    }
    assert targets["fk_transactions_document_id"] == "corpus.documents.document_id"


def test_schema_qualified_collisions_are_refused() -> None:
    left = normalize_contract(odcs_document(contract_id="left"), "left")
    right = normalize_contract(odcs_document(contract_id="right"), "right")
    with pytest.raises(UnsupportedContractMappingError, match="duplicate ODCS schema identity"):
        build_metadata([left, right])


def test_duplicate_physical_binding_is_refused() -> None:
    left = normalize_contract(odcs_document(contract_id="left", schema_name="left"), "left")
    right = normalize_contract(odcs_document(contract_id="right", schema_name="right"), "right")
    with pytest.raises(UnsupportedContractMappingError, match="duplicate physical binding"):
        build_metadata([left, right])


def test_unknown_relationship_target_is_refused() -> None:
    document = odcs_document(
        properties=[
            property_field("document_id", primaryKey=True, primaryKeyPosition=1, required=True),
            property_field(
                "object_id", relationships=[{"type": "foreignKey", "to": "objects.object_id"}]
            ),
        ]
    )
    table = normalize_contract(document, "documents")
    with pytest.raises(UnsupportedContractMappingError, match="is not a registered contract"):
        build_metadata([table])


def test_missing_primary_key_is_refused() -> None:
    document = odcs_document(properties=[property_field("document_id")])
    table = normalize_contract(document, "documents")
    with pytest.raises(UnsupportedContractMappingError, match="no primary key is declared"):
        build_metadata([table])


def test_review_ddl_is_deterministic_and_carries_descriptions() -> None:
    model = load_schema_model_from_root(_contracts_root())
    first = contract_ddl(model.metadata, model.by_contract("documents"))
    second = contract_ddl(
        load_schema_model_from_root(_contracts_root()).metadata,
        model.by_contract("documents"),
    )
    assert first == second
    assert "COMMENT ON TABLE corpus.documents IS" in first
    assert baseline_ddl(model.metadata) == baseline_ddl(
        load_schema_model_from_root(_contracts_root()).metadata
    )


def test_baseline_ddl_orders_referenced_tables_first() -> None:
    model = load_schema_model_from_root(_contracts_root())
    baseline = baseline_ddl(model.metadata)
    assert baseline.index("CREATE TABLE corpus.documents (") < baseline.index(
        "CREATE TABLE kg.transactions ("
    )


def test_every_supported_logical_type_compiles() -> None:
    document = odcs_document(
        partition_key=None,
        properties=[
            property_field("row_id", primaryKey=True, primaryKeyPosition=1, required=True),
            property_field("flag", "boolean"),
            property_field("observed_at", "timestamp"),
            property_field("observed_on", "date"),
            property_field("observed_time", "time"),
            property_field("payload", "object"),
            property_field("tags", "array"),
            property_field("code", logicalTypeOptions={"maxLength": 12}, unique=True),
            property_field("total", "number", logicalTypeOptions={"precision": 18, "scale": 4}),
        ],
    )
    table = normalize_contract(document, "documents")
    metadata = build_metadata([table])
    ddl = contract_ddl(metadata, table)
    for fragment in (
        "flag BOOLEAN",
        "observed_at TIMESTAMP WITH TIME ZONE",
        "observed_on DATE",
        "observed_time TIME",
        "payload JSONB",
        "tags JSONB",
        "code VARCHAR(12)",
        "total NUMERIC(18, 4)",
        "CONSTRAINT uq_documents_code UNIQUE (code)",
    ):
        assert fragment in ddl


def test_duplicate_primary_key_positions_are_refused() -> None:
    document = odcs_document(
        properties=[
            property_field("a", primaryKey=True, primaryKeyPosition=1, required=True),
            property_field("b", primaryKey=True, primaryKeyPosition=1, required=True),
        ]
    )
    table = normalize_contract(document, "documents")
    with pytest.raises(UnsupportedContractMappingError, match="duplicate primaryKeyPosition"):
        build_metadata([table])


def test_relationship_to_a_missing_column_is_refused() -> None:
    target = normalize_contract(
        odcs_document(contract_id="objects", schema_name="objects", table="objects"), "objects"
    )
    document = odcs_document(
        properties=[
            property_field("document_id", primaryKey=True, primaryKeyPosition=1, required=True),
            property_field(
                "object_id", relationships=[{"type": "foreignKey", "to": "objects.absent"}]
            ),
        ]
    )
    source = normalize_contract(document, "documents")
    with pytest.raises(UnsupportedContractMappingError, match="does not exist"):
        build_metadata([source, target])
