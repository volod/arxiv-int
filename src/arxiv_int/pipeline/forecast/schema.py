"""Committed JSON Schema for forecast decision documents."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.pipeline.forecast.capacity import (
    CAPACITY_DIR,
    ENVELOPE_NAME,
    SCHEMA_NAME,
    envelope_payload,
)
from arxiv_int.pipeline.forecast.model import SCHEMA_ID

_SCHEMA_META = "https://json-schema.org/draft/2020-12/schema"
_TIME = {
    "additionalProperties": False,
    "properties": {
        "lower_seconds": {"minimum": 0, "type": "number"},
        "upper_seconds": {"minimum": 0, "type": "number"},
    },
    "required": ["lower_seconds", "upper_seconds"],
    "type": "object",
}

FORECAST_SCHEMA: dict[str, Any] = {
    "$id": "https://arxiv-int.local/capacity/forecast.schema.json",
    "$schema": _SCHEMA_META,
    "additionalProperties": False,
    "properties": {
        "actions": {"items": {"type": "string"}, "type": "array"},
        "coefficients": {
            "items": {
                "additionalProperties": False,
                "properties": {
                    "evidence_id": {"minLength": 1, "type": "string"},
                    "name": {"minLength": 1, "type": "string"},
                    "source": {
                        "enum": ["envelope", "telemetry", "sample", "declared"],
                        "type": "string",
                    },
                    "value": {"type": "number"},
                },
                "required": ["name", "value", "source", "evidence_id"],
                "type": "object",
            },
            "type": "array",
        },
        "confidence": {"enum": ["low", "medium", "high"], "type": "string"},
        "config_fingerprint": {"minLength": 1, "type": "string"},
        "critical_path": {"items": {"type": "string"}, "type": "array"},
        "decision": {"enum": ["ready", "degraded", "blocked", "unknown"], "type": "string"},
        "devices": {"items": {"type": "object"}, "type": "array"},
        "envelope_fingerprint": {"minLength": 1, "type": "string"},
        "excluded": {"items": {"type": "string"}, "type": "array"},
        "fingerprint": {"minLength": 1, "type": "string"},
        "forecast_id": {"minLength": 1, "type": "string"},
        "host": {"type": "object"},
        "inventory_source": {"enum": ["sample", "inventory", "delta"], "type": "string"},
        "not_selected": {"items": {"type": "string"}, "type": "array"},
        "outputs": {"type": "object"},
        "plan": {"items": {"minLength": 1, "type": "string"}, "type": "array"},
        "production": {"type": "boolean"},
        "profile": {"minLength": 1, "type": "string"},
        "run_id": {"type": ["string", "null"]},
        "schema": {"const": SCHEMA_ID},
        "source_snapshot": {"minLength": 1, "type": "string"},
        "stages": {"items": {"type": "object"}, "type": "array"},
        "time": _TIME,
    },
    "required": [
        "schema",
        "forecast_id",
        "run_id",
        "production",
        "profile",
        "plan",
        "decision",
        "confidence",
        "fingerprint",
        "config_fingerprint",
        "source_snapshot",
        "envelope_fingerprint",
        "inventory_source",
        "stages",
        "devices",
        "outputs",
        "time",
        "critical_path",
        "host",
        "coefficients",
        "actions",
        "excluded",
        "not_selected",
    ],
    "title": "PipelineForecast",
    "type": "object",
}


def dump_schema(schema: Mapping[str, Any] = FORECAST_SCHEMA) -> str:
    """Serialize the forecast schema with stable ordering."""
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def write_forecast_schema(project_root: Path) -> Path:
    """Write ``configs/capacity/forecast.schema.json``."""
    directory = project_root / CAPACITY_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / SCHEMA_NAME
    path.write_text(dump_schema(), encoding="utf-8")
    return path


def check_schema_drift(project_root: Path) -> tuple[str, ...]:
    """Return drift findings for the committed forecast schema and envelope."""
    findings: list[str] = []
    directory = project_root / CAPACITY_DIR
    schema_path = directory / SCHEMA_NAME
    if not schema_path.is_file():
        findings.append(f"missing generated schema {SCHEMA_NAME}")
    elif schema_path.read_text(encoding="utf-8") != dump_schema():
        findings.append(f"generated schema drifted: {SCHEMA_NAME}")
    envelope_path = directory / ENVELOPE_NAME
    expected = normalize_json(envelope_payload())
    if not envelope_path.is_file():
        findings.append(f"missing capacity envelope {ENVELOPE_NAME}")
    elif envelope_path.read_text(encoding="utf-8") != expected:
        findings.append(f"capacity envelope drifted: {ENVELOPE_NAME}")
    return tuple(findings)
