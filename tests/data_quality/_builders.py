"""Shared ODCS and frame fixtures for data-quality tests."""

from decimal import Decimal
from pathlib import Path
from typing import Any

from arxiv_int.contracts.sqlalchemy.normalize import normalize_contract
from arxiv_int.data_quality.rules import compile_rule_catalog
from tests.contracts.sqlalchemy._builders import odcs_document, property_field


def rows_odcs(
    *,
    amount_options: dict[str, int] | None = None,
    with_currency: bool = True,
    with_parent: bool = True,
    quality: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a small invoice-like ODCS document for quality fixtures."""
    amount: dict[str, Any] = property_field("amount", "number")
    if amount_options is not None:
        amount["logicalTypeOptions"] = amount_options
    properties = [
        property_field("row_id", primaryKey=True, primaryKeyPosition=1, required=True),
        amount,
    ]
    if with_currency:
        properties.append(property_field("currency"))
    if with_parent:
        properties.append(
            property_field(
                "document_id",
                relationships=[{"type": "foreignKey", "to": "documents.document_id"}],
            )
        )
    document = odcs_document(
        contract_id="invoice-rows",
        schema_name="invoice_rows",
        pg_schema="kg",
        table="invoice_rows",
        properties=properties,
        partition_key=None,
    )
    if quality is not None:
        document["quality"] = quality
    return document


def documents_odcs() -> dict[str, Any]:
    """Return a parent documents contract used by relationship fixtures."""
    return odcs_document(partition_key=None)


def compile_rows_catalog(
    *,
    amount_options: dict[str, int] | None = None,
    quality: list[dict[str, Any]] | None = None,
) -> Any:
    """Compile the invoice-rows catalog against a documents parent."""
    rows = rows_odcs(amount_options=amount_options, quality=quality)
    documents = documents_odcs()
    tables = (
        normalize_contract(documents, "documents"),
        normalize_contract(rows, "invoice-rows"),
    )
    return compile_rule_catalog(tables[1], tables, rows)


def write_json_table(path: Path, rows: list[dict[str, Any]]) -> Path:
    """Write a JSON-array table for IO tests."""
    import json

    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def decimal_frame(rows: list[tuple[str, Decimal, str | None, str | None]]) -> Any:
    """Return an eager Polars frame with a decimal amount column."""
    import polars as pl

    return pl.DataFrame(
        {
            "row_id": [row[0] for row in rows],
            "amount": [row[1] for row in rows],
            "currency": [row[2] for row in rows],
            "document_id": [row[3] for row in rows],
        },
        schema={
            "row_id": pl.Utf8,
            "amount": pl.Decimal(precision=18, scale=4),
            "currency": pl.Utf8,
            "document_id": pl.Utf8,
        },
    )
