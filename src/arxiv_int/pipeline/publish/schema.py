"""Committed JSON Schema and profile overlays for knowledge-base publication."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.pipeline.publish.model import PROFILE_SCHEMA, SCHEMA_ID
from arxiv_int.pipeline.publish.profiles import (
    DEFAULT_PROFILES,
    check_profile_alignment,
    profile_payload,
)
from arxiv_int.resources.paths import configs_output_root, configs_root

_SCHEMA_META = "https://json-schema.org/draft/2020-12/schema"
PROFILE_SCHEMA_NAME = "profile.schema.json"
KNOWLEDGE_BASE_SCHEMA_NAME = "knowledge-base.schema.json"

PROFILE_JSON_SCHEMA: dict[str, Any] = {
    "$id": "https://arxiv-int.local/pipeline/profile.schema.json",
    "$schema": _SCHEMA_META,
    "additionalProperties": False,
    "properties": {
        "families": {"items": {"type": "object"}, "type": "array"},
        "name": {"minLength": 1, "type": "string"},
        "optional_stages": {"items": {"type": "string"}, "type": "array"},
        "report_family": {"minLength": 1, "type": "string"},
        "required_stages": {"items": {"minLength": 1, "type": "string"}, "type": "array"},
        "schema": {"const": PROFILE_SCHEMA},
    },
    "required": ["schema", "name", "required_stages", "optional_stages", "families"],
    "type": "object",
}

KNOWLEDGE_BASE_SCHEMA: dict[str, Any] = {
    "$id": "https://arxiv-int.local/pipeline/knowledge-base.schema.json",
    "$schema": _SCHEMA_META,
    "additionalProperties": False,
    "properties": {
        "active": {"type": "boolean"},
        "catalog_path": {"type": "string"},
        "config_fingerprint": {"minLength": 1, "type": "string"},
        "coverage": {"type": "object"},
        "fingerprint": {"minLength": 1, "type": "string"},
        "generation_id": {"minLength": 1, "type": "string"},
        "limitations": {"items": {"type": "string"}, "type": "array"},
        "not_selected": {"items": {"type": "string"}, "type": "array"},
        "outputs": {"items": {"type": "object"}, "type": "array"},
        "profile": {"minLength": 1, "type": "string"},
        "report_path": {"type": "string"},
        "resume_command": {"minLength": 1, "type": "string"},
        "run_id": {"minLength": 1, "type": "string"},
        "schema": {"const": SCHEMA_ID},
        "source_snapshot": {"minLength": 1, "type": "string"},
        "status": {
            "enum": ["succeeded", "partial", "failed", "blocked", "interrupted"],
            "type": "string",
        },
        "status_command": {"minLength": 1, "type": "string"},
    },
    "required": [
        "schema",
        "run_id",
        "generation_id",
        "profile",
        "status",
        "active",
        "outputs",
        "coverage",
        "fingerprint",
    ],
    "type": "object",
}


def dump_schema(schema: Mapping[str, Any]) -> str:
    """Serialize one schema with stable ordering."""
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def write_pipeline_assets(project_root: Path) -> None:
    """Write committed profile JSON and knowledge-base schema files."""
    directory = configs_output_root(project_root) / "pipeline"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / PROFILE_SCHEMA_NAME).write_text(dump_schema(PROFILE_JSON_SCHEMA), encoding="utf-8")
    (directory / KNOWLEDGE_BASE_SCHEMA_NAME).write_text(
        dump_schema(KNOWLEDGE_BASE_SCHEMA), encoding="utf-8"
    )
    for profile in DEFAULT_PROFILES.values():
        path = directory / f"{profile.name}.json"
        path.write_text(normalize_json(profile_payload(profile)), encoding="utf-8")


def check_schema_drift(project_root: Path) -> tuple[str, ...]:
    """Return drift findings for committed profiles and schemas."""
    findings = list(check_profile_alignment())
    directory = configs_root(project_root) / "pipeline"
    expected = {
        PROFILE_SCHEMA_NAME: dump_schema(PROFILE_JSON_SCHEMA),
        KNOWLEDGE_BASE_SCHEMA_NAME: dump_schema(KNOWLEDGE_BASE_SCHEMA),
        **{
            f"{name}.json": normalize_json(profile_payload(profile))
            for name, profile in DEFAULT_PROFILES.items()
        },
    }
    for name, text in expected.items():
        path = directory / name
        if not path.is_file():
            findings.append(f"missing pipeline asset {name}")
        elif path.read_text(encoding="utf-8") != text:
            findings.append(f"pipeline asset drifted: {name}")
    return tuple(findings)
