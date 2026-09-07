"""Avro reader/writer compatibility checks in both directions."""

import json
from io import BytesIO
from pathlib import Path
from typing import Any

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


def _load_schema(path: Path) -> dict[str, Any]:
    loaded = parse_schema(json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(loaded, dict):
        raise ValueError(f"Avro schema must be a record mapping: {path}")
    return loaded


def _round_trip(writer_schema: dict[str, Any], reader_schema: dict[str, Any]) -> None:
    record = {field["name"]: _sample_value(field["type"]) for field in writer_schema["fields"]}
    buffer = BytesIO()
    fastavro.writer(buffer, writer_schema, [record])
    buffer.seek(0)
    rows = list(fastavro.reader(buffer, reader_schema=reader_schema))
    if len(rows) != 1:
        raise ValueError("Avro compatibility round-trip produced no rows")


def avro_compatibility_findings(writer_path: Path, reader_path: Path) -> list[str]:
    """Return findings when writer->reader or reader->writer round-trips fail."""
    findings: list[str] = []
    try:
        writer = _load_schema(writer_path)
        reader = _load_schema(reader_path)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return [f"Avro schema load failed: {error}"]
    for label, left, right in (
        ("writer-to-reader", writer, reader),
        ("reader-to-writer", reader, writer),
    ):
        try:
            _round_trip(left, right)
        except Exception as error:
            findings.append(f"Avro {label} incompatible: {error}")
    return findings


def generated_avro_self_compatibility(avro_path: Path) -> list[str]:
    """Verify a generated Avro schema is compatible with itself both ways."""
    return avro_compatibility_findings(avro_path, avro_path)
