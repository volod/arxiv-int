"""Small ODCS documents used to exercise normalization and metadata building."""

from typing import Any


def odcs_document(
    *,
    contract_id: str = "documents",
    schema_name: str = "documents",
    pg_schema: str = "corpus",
    table: str = "documents",
    properties: list[dict[str, Any]] | None = None,
    partition_key: str | None = "bucket",
) -> dict[str, Any]:
    """Return one minimal ODCS document with a project physical binding."""
    extension: dict[str, Any] = {"schema": pg_schema, "table": table}
    if partition_key:
        extension["partitionKey"] = partition_key
    return {
        "id": f"urn:arxiv-int:contract:{contract_id}:1.0.0",
        "version": "1.0.0",
        "description": {"purpose": f"{contract_id} fixture."},
        "customProperties": [{"property": "x-arxiv-int", "value": extension}],
        "schema": [
            {
                "name": schema_name,
                "physicalName": table,
                "logicalType": "object",
                "properties": properties
                or [
                    {
                        "name": "document_id",
                        "logicalType": "string",
                        "primaryKey": True,
                        "primaryKeyPosition": 1,
                        "required": True,
                    }
                ],
            }
        ],
    }


def property_field(name: str, logical_type: str = "string", **extra: Any) -> dict[str, Any]:
    """Return one ODCS property definition."""
    return {"name": name, "logicalType": logical_type, **extra}
