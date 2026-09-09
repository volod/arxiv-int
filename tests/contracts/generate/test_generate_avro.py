"""Avro parse and round-trip tests against committed generated schemas."""

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from arxiv_int.resources.paths import contracts_root

pytest.importorskip("fastavro")

import fastavro
from fastavro import parse_schema

_PRIMITIVES: dict[str, Any] = {
    "null": None,
    "boolean": True,
    "int": 1,
    "long": 1,
    "float": 1.0,
    "double": 1.0,
    "bytes": b"x",
    "string": "x",
}


def _avro_dir() -> Path:
    return contracts_root() / "generated" / "avro"


def _sample_named(avro_type: dict[str, Any]) -> Any:
    kind = avro_type.get("type")
    if kind == "record":
        return {field["name"]: _sample_value(field["type"]) for field in avro_type["fields"]}
    if kind == "array":
        return [_sample_value(avro_type["items"])]
    if kind == "map":
        return {"k": _sample_value(avro_type["values"])}
    if kind == "enum":
        return avro_type["symbols"][0]
    if kind == "fixed":
        return b"\x00" * int(avro_type["size"])
    if kind == "bytes":
        return b"x"
    return _sample_value(kind)


def _sample_value(avro_type: Any) -> Any:
    if isinstance(avro_type, list):
        non_null = [item for item in avro_type if item != "null"]
        return _sample_value(non_null[0] if non_null else "null")
    if isinstance(avro_type, dict):
        return _sample_named(avro_type)
    return _PRIMITIVES.get(avro_type, "x")


def test_committed_avro_schemas_parse_and_round_trip() -> None:
    paths = sorted(_avro_dir().glob("*.avsc"))
    assert len(paths) >= 14
    for path in paths:
        schema = parse_schema(json.loads(path.read_text(encoding="utf-8")))
        record = {field["name"]: _sample_value(field["type"]) for field in schema["fields"]}
        buffer = BytesIO()
        fastavro.writer(buffer, schema, [record])
        buffer.seek(0)
        rows = list(fastavro.reader(buffer))
        assert len(rows) == 1
        assert set(rows[0]) == set(record)
