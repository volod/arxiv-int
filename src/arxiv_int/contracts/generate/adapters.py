"""Focused adapters for generation gaps beyond Data Contract CLI exporters."""

from typing import Any

from arxiv_int.contracts.catalog.normalize import is_floating
from arxiv_int.contracts.catalog.odcs_ext import project_extension
from arxiv_int.contracts.generate.normalize import normalize_json, normalize_text


def _logical_to_arrow(logical: str, physical: str | None = None) -> str:
    if logical == "number":
        return "float64" if is_floating(physical) else "decimal128(38, 9)"
    mapping = {
        "string": "string",
        "integer": "int64",
        "boolean": "bool",
        "timestamp": "timestamp[us, tz=UTC]",
        "date": "date32",
        "time": "time64[us]",
        "object": "string",
        "array": "string",
    }
    return mapping.get(logical, "string")


def _schema_properties(odcs: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for schema in odcs.get("schema") or []:
        if not isinstance(schema, dict) or "name" not in schema:
            continue
        schema_name = str(schema["name"])
        for prop in schema.get("properties") or []:
            if isinstance(prop, dict) and "name" in prop:
                rows.append((schema_name, prop))
    return rows


def parquet_descriptor(odcs: dict[str, Any], contract_id: str) -> str:
    """Emit a deterministic Arrow/Parquet field descriptor JSON document."""
    extension = project_extension(odcs.get("customProperties")) or {}
    fields = []
    for _schema_name, prop in _schema_properties(odcs):
        fields.append(
            {
                "name": str(prop["name"]),
                "arrowType": _logical_to_arrow(
                    str(prop.get("logicalType", "string")),
                    None if prop.get("physicalType") is None else str(prop["physicalType"]),
                ),
                "nullable": not bool(prop.get("required", False)),
                "primaryKey": bool(prop.get("primaryKey", False)),
            }
        )
    document = {
        "contractId": contract_id,
        "format": "parquet",
        "partitionKey": extension.get("partitionKey"),
        "fields": fields,
        "sourceOdcsId": odcs.get("id"),
        "sourceVersion": odcs.get("version"),
    }
    return normalize_json(document)


def postgres_extension_sql(odcs: dict[str, Any], contract_id: str) -> str:
    """Emit partition templates that SQLAlchemy metadata cannot express.

    Columns, types, keys, and constraints belong to the contract-derived metadata and
    its Alembic revisions; this adapter only carries engine features beyond them.
    """
    extension = project_extension(odcs.get("customProperties")) or {}
    schema = str(extension.get("schema") or "public")
    table = str(extension.get("table") or contract_id.replace("-", "_"))
    lines = [
        f"-- arxiv-int postgres extensions for {contract_id}",
        f"-- source: {odcs.get('id')}@{odcs.get('version')}",
        f"-- table columns and constraints are owned by {schema}.{table} metadata revisions",
    ]
    partition_key = extension.get("partitionKey")
    if partition_key:
        lines.extend(
            [
                f"-- HASH partition template for {schema}.{table} USING ({partition_key})",
                f"-- CREATE TABLE {schema}.{table}_p0 PARTITION OF {schema}.{table} "
                f"FOR VALUES WITH (MODULUS 16, REMAINDER 0);",
            ]
        )
    return normalize_text("\n".join(lines))


def search_extension_sql(odcs: dict[str, Any], contract_id: str) -> str | None:
    """Emit ParadeDB/BM25 tokenizer index DDL when search hints exist."""
    extension = project_extension(odcs.get("customProperties")) or {}
    search = extension.get("search")
    if not isinstance(search, dict):
        return None
    schema = str(extension.get("schema") or "public")
    table = str(extension.get("table") or contract_id.replace("-", "_"))
    fields = search.get("textFields") or []
    tokenizer = str(search.get("tokenizer") or "unicode_words")
    if not isinstance(fields, list) or not fields:
        return None
    lines = [
        f"-- arxiv-int search extensions for {contract_id}",
        f"-- tokenizer: {tokenizer}",
    ]
    for field in fields:
        index_name = f"{table}_{field}_bm25"
        lines.append(
            f"CREATE INDEX IF NOT EXISTS {index_name} ON {schema}.{table} "
            f"USING bm25 ({field}) WITH (key_field='{field}', text_config='{tokenizer}');"
        )
    return normalize_text("\n".join(lines))


def vector_extension_sql(odcs: dict[str, Any], contract_id: str) -> str | None:
    """Emit pgvector dimension and index DDL when vector hints exist."""
    extension = project_extension(odcs.get("customProperties")) or {}
    vector = extension.get("vector")
    if not isinstance(vector, dict):
        return None
    schema = str(extension.get("schema") or "public")
    table = str(extension.get("table") or contract_id.replace("-", "_"))
    dimensions = int(vector.get("defaultDimensions") or 0)
    index = str(vector.get("index") or "ivfflat")
    if dimensions <= 0:
        return None
    lines = [
        f"-- arxiv-int vector extensions for {contract_id}",
        "CREATE EXTENSION IF NOT EXISTS vector;",
        f"ALTER TABLE {schema}.{table} ADD COLUMN IF NOT EXISTS embedding vector({dimensions});",
        f"CREATE INDEX IF NOT EXISTS {table}_embedding_{index} ON {schema}.{table} "
        f"USING {index} (embedding vector_cosine_ops);",
    ]
    return normalize_text("\n".join(lines))


def graph_extension_sql(odcs: dict[str, Any], contract_id: str) -> str | None:
    """Emit AGE projection SQL stubs from graph hints."""
    extension = project_extension(odcs.get("customProperties")) or {}
    graph = extension.get("graph")
    if not isinstance(graph, dict):
        return None
    schema = str(extension.get("schema") or "public")
    table = str(extension.get("table") or contract_id.replace("-", "_"))
    lines = [
        f"-- arxiv-int AGE projection for {contract_id}",
        "LOAD 'age';",
        "SET search_path = ag_catalog, '$user', public;",
    ]
    if graph.get("vertexLabel"):
        label = str(graph["vertexLabel"])
        id_field = str(graph.get("idField") or "id")
        lines.append(
            f"-- SELECT * FROM cypher('arxiv_int', $$ "
            f"CREATE (:{label} {{id: row.{id_field}}}) $$) AS (v agtype);"
        )
        lines.append(f"-- source table: {schema}.{table}")
    if graph.get("edgeLabel"):
        label = str(graph["edgeLabel"])
        frm = str(graph.get("fromField") or "from_id")
        to = str(graph.get("toField") or "to_id")
        lines.append(
            f"-- SELECT * FROM cypher('arxiv_int', $$ "
            f"MATCH (a {{id: row.{frm}}}), (b {{id: row.{to}}}) "
            f"CREATE (a)-[:{label}]->(b) $$) AS (e agtype);"
        )
    return normalize_text("\n".join(lines))


def provenance_sidecar(
    odcs: dict[str, Any],
    contract_id: str,
    *,
    semantic_hash: str | None,
    artifact_fingerprints: dict[str, str],
) -> str:
    """Emit provenance metadata so source contract identity is not lost."""
    extension = project_extension(odcs.get("customProperties")) or {}
    document = {
        "contractId": contract_id,
        "odcsId": odcs.get("id"),
        "odcsVersion": odcs.get("version"),
        "apiVersion": odcs.get("apiVersion"),
        "canonicalEntity": extension.get("canonicalEntity"),
        "postgres": {
            "schema": extension.get("schema"),
            "table": extension.get("table"),
            "partitionKey": extension.get("partitionKey"),
        },
        "semanticMetadataHash": semantic_hash,
        "artifacts": dict(sorted(artifact_fingerprints.items())),
        "customExtensionKeys": sorted(extension),
    }
    return normalize_json(document)
