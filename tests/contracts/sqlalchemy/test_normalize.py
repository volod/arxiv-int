"""Unsupported ODCS metadata must fail instead of being silently dropped."""

import pytest

from arxiv_int.contracts.sqlalchemy.normalize import (
    PARTITION_KEY_ORIGIN,
    UnsupportedContractMappingError,
    normalize_contract,
)
from tests.contracts.sqlalchemy._builders import odcs_document, property_field


def test_partition_key_becomes_an_explicit_column() -> None:
    table = normalize_contract(odcs_document(), "documents")
    bucket = next(column for column in table.columns if column.name == "bucket")
    assert bucket.origin == PARTITION_KEY_ORIGIN
    assert table.qualified_name == "corpus.documents"
    assert table.description == "documents fixture."


def test_decimal_precision_and_scale_survive() -> None:
    document = odcs_document(
        properties=[
            property_field("row_id", primaryKey=True, primaryKeyPosition=1, required=True),
            property_field("amount", "number", logicalTypeOptions={"precision": 18, "scale": 4}),
        ]
    )
    table = normalize_contract(document, "rows")
    amount = next(column for column in table.columns if column.name == "amount")
    assert (amount.precision, amount.scale) == (18, 4)


@pytest.mark.parametrize(
    ("properties", "message"),
    [
        ([property_field("id", "geometry")], "unsupported logicalType"),
        ([property_field("id", extraKey=1)], "unsupported property keys"),
        (
            [property_field("id", logicalTypeOptions={"pattern": "x"})],
            "unsupported logicalTypeOptions keys",
        ),
        (
            [property_field("id", logicalTypeOptions={"scale": 2})],
            "scale requires an explicit precision",
        ),
        (
            [property_field("id", relationships=[{"type": "aggregate", "to": "a.b"}])],
            "unsupported relationship type",
        ),
        (
            [property_field("id", relationships=[{"type": "foreignKey", "to": "objects"}])],
            "relationship target must be",
        ),
        ([property_field("id", primaryKey=True)], "primaryKey requires primaryKeyPosition"),
        ([property_field("id"), property_field("id")], "duplicate field names"),
    ],
)
def test_unsupported_metadata_is_rejected(
    properties: list[dict[str, object]], message: str
) -> None:
    with pytest.raises(UnsupportedContractMappingError, match=message):
        normalize_contract(odcs_document(properties=properties), "documents")


def test_multiple_schema_objects_are_rejected() -> None:
    document = odcs_document()
    document["schema"].append(dict(document["schema"][0]))
    with pytest.raises(UnsupportedContractMappingError, match="exactly one ODCS schema"):
        normalize_contract(document, "documents")


def test_schema_without_fields_is_rejected() -> None:
    document = odcs_document()
    document["schema"][0]["properties"] = []
    with pytest.raises(UnsupportedContractMappingError, match="has no fields"):
        normalize_contract(document, "documents")
