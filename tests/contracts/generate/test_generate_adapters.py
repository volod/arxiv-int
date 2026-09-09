"""Unit tests for focused generation adapters without Data Contract CLI."""

from arxiv_int.contracts.generate.adapters import (
    graph_extension_sql,
    parquet_descriptor,
    postgres_extension_sql,
    provenance_sidecar,
    search_extension_sql,
    vector_extension_sql,
)
from arxiv_int.contracts.generate.normalize import sha256_text


def _odcs(**extension: object) -> dict:
    return {
        "id": "urn:test:contract",
        "version": "1.0.0",
        "apiVersion": "v3.1.0",
        "customProperties": [{"property": "x-arxiv-int", "value": extension}],
        "schema": [
            {
                "name": "items",
                "properties": [
                    {
                        "name": "id",
                        "logicalType": "string",
                        "primaryKey": True,
                        "required": True,
                    },
                    {"name": "body", "logicalType": "string"},
                ],
            }
        ],
    }


def test_parquet_descriptor_is_byte_stable() -> None:
    first = parquet_descriptor(
        _odcs(schema="corpus", table="items", partitionKey="bucket"), "items"
    )
    second = parquet_descriptor(
        _odcs(schema="corpus", table="items", partitionKey="bucket"), "items"
    )
    assert first == second
    assert '"arrowType": "string"' in first
    assert sha256_text(first) == sha256_text(second)


def test_search_vector_and_graph_adapters_emit_extension_ddl() -> None:
    search = search_extension_sql(
        _odcs(
            schema="corpus",
            table="documents",
            search={"textFields": ["title"], "tokenizer": "russian_stem"},
        ),
        "documents",
    )
    assert search is not None
    assert "bm25" in search
    assert "russian_stem" in search

    vector = vector_extension_sql(
        _odcs(
            schema="knowledge",
            table="embeddings",
            vector={"defaultDimensions": 1024, "index": "ivfflat"},
        ),
        "embeddings",
    )
    assert vector is not None
    assert "vector(1024)" in vector

    graph = graph_extension_sql(
        _odcs(
            schema="knowledge", table="objects", graph={"vertexLabel": "Object", "idField": "id"}
        ),
        "objects",
    )
    assert graph is not None
    assert "Object" in graph


def test_postgres_extensions_and_provenance_retain_source_metadata() -> None:
    odcs = _odcs(
        schema="corpus", table="items", partitionKey="bucket", search={"textFields": ["body"]}
    )
    sql = postgres_extension_sql(odcs, "items")
    assert "partition" in sql.lower() or "PARTITION" in sql
    assert "bucket" in sql

    sidecar = provenance_sidecar(
        odcs,
        "items",
        semantic_hash="abc",
        artifact_fingerprints={"avro/items.avsc": "deadbeef"},
    )
    assert '"semanticMetadataHash": "abc"' in sidecar
    assert "search" in sidecar
