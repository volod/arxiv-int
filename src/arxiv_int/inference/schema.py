"""Generated structured-output JSON Schema, validation, and bounded repair."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path("configs") / "models" / "schemas"
MAX_REPAIR_ATTEMPTS = 2
REPAIR_INSTRUCTION = (
    "Return JSON that satisfies the supplied schema. Previous output failed validation."
)
_SCHEMA_META = "https://json-schema.org/draft/2020-12/schema"

CITED_SPAN_SCHEMA: dict[str, Any] = {
    "$schema": _SCHEMA_META,
    "$id": "https://arxiv-int.local/inference/cited-span.schema.json",
    "title": "CitedSpan",
    "type": "object",
    "additionalProperties": False,
    "required": ["value", "evidence"],
    "properties": {
        "value": {"type": "string", "minLength": 1},
        "evidence": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["quote", "start", "end"],
                "properties": {
                    "quote": {"type": "string", "minLength": 1},
                    "start": {"type": "integer", "minimum": 0},
                    "end": {"type": "integer", "minimum": 0},
                },
            },
        },
    },
}
REFUSAL_SCHEMA: dict[str, Any] = {
    "$schema": _SCHEMA_META,
    "$id": "https://arxiv-int.local/inference/refusal.schema.json",
    "title": "Refusal",
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "reason"],
    "properties": {
        "status": {"const": "refused"},
        "reason": {"type": "string", "minLength": 1},
    },
}
GENERATED_SCHEMAS: dict[str, dict[str, Any]] = {
    "cited-span": CITED_SPAN_SCHEMA,
    "refusal": REFUSAL_SCHEMA,
}


def schema_root(project_root: Path) -> Path:
    """Return the committed structured-output schema directory."""
    return project_root / SCHEMA_DIR


def dump_schema(schema: Mapping[str, Any]) -> str:
    """Serialize one schema with stable ordering."""
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def generate_schemas(project_root: Path) -> tuple[Path, ...]:
    """Write committed structured-output schemas and return their paths."""
    root = schema_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, schema in GENERATED_SCHEMAS.items():
        path = root / f"{name}.schema.json"
        path.write_text(dump_schema(schema), encoding="utf-8")
        written.append(path)
    return tuple(written)


def check_schema_drift(project_root: Path) -> tuple[str, ...]:
    """Return drift findings; an empty tuple means the committed schemas match."""
    findings: list[str] = []
    root = schema_root(project_root)
    expected = {
        f"{name}.schema.json": dump_schema(schema) for name, schema in GENERATED_SCHEMAS.items()
    }
    if not root.is_dir():
        return ("structured-output schema directory is missing",)
    actual = {
        path.name: path.read_text(encoding="utf-8") for path in sorted(root.glob("*.schema.json"))
    }
    for name, body in expected.items():
        if name not in actual:
            findings.append(f"missing generated schema {name}")
        elif actual[name] != body:
            findings.append(f"generated schema drifted: {name}")
    extra = sorted(set(actual) - set(expected))
    findings.extend(f"unexpected schema file {name}" for name in extra)
    return tuple(findings)


def extract_json_text(text: str) -> str:
    """Strip optional Markdown fences around a JSON payload."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


def parse_json_object(text: str) -> object:
    """Parse JSON after fence stripping."""
    return json.loads(extract_json_text(text))


def validate_instance(schema: Mapping[str, Any], instance: object) -> tuple[str, ...]:
    """Return validation errors for a focused JSON Schema subset."""
    errors: list[str] = []
    _validate(schema, instance, "$", errors)
    return tuple(errors)


def is_refusal_payload(instance: object) -> bool:
    """Report whether parsed JSON matches the refusal envelope."""
    return not validate_instance(REFUSAL_SCHEMA, instance)


def repair_user_message(errors: Sequence[str]) -> str:
    """Build a repair instruction that does not repeat the original prompt."""
    detail = "; ".join(errors[:8]) or "output was not valid JSON"
    return f"{REPAIR_INSTRUCTION} Errors: {detail}"


def _validate(schema: Mapping[str, Any], instance: object, path: str, errors: list[str]) -> None:
    if not _matches_const_enum(schema, instance, path, errors):
        return
    expected = schema.get("type")
    if expected is not None and not _type_matches(expected, instance):
        errors.append(f"{path}: expected type {expected}")
        return
    if expected == "object" or "properties" in schema or "required" in schema:
        _validate_object(schema, instance, path, errors)
    if expected == "array" or "items" in schema:
        _validate_array(schema, instance, path, errors)
    _validate_bounds(schema, instance, path, errors)


def _matches_const_enum(
    schema: Mapping[str, Any], instance: object, path: str, errors: list[str]
) -> bool:
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const")
        return False
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value not in enum")
        return False
    return True


def _validate_bounds(
    schema: Mapping[str, Any], instance: object, path: str, errors: list[str]
) -> None:
    expected = schema.get("type")
    if expected == "string" and isinstance(instance, str):
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(instance) < minimum:
            errors.append(f"{path}: shorter than minLength")
            return
    if expected not in {"integer", "number"} or isinstance(instance, bool):
        return
    if not isinstance(instance, (int, float)):
        return
    minimum = schema.get("minimum")
    if isinstance(minimum, (int, float)) and instance < minimum:
        errors.append(f"{path}: below minimum")


def _validate_object(
    schema: Mapping[str, Any], instance: object, path: str, errors: list[str]
) -> None:
    if not isinstance(instance, dict):
        if schema.get("type") == "object":
            errors.append(f"{path}: expected object")
        return
    required = schema.get("required", [])
    if isinstance(required, list):
        for name in required:
            if name not in instance:
                errors.append(f"{path}.{name}: missing required property")
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return
    additional = schema.get("additionalProperties", True)
    for name, value in instance.items():
        if name in properties and isinstance(properties[name], dict):
            _validate(properties[name], value, f"{path}.{name}", errors)
        elif additional is False:
            errors.append(f"{path}.{name}: additional property")


def _validate_array(
    schema: Mapping[str, Any], instance: object, path: str, errors: list[str]
) -> None:
    if not isinstance(instance, list):
        if schema.get("type") == "array":
            errors.append(f"{path}: expected array")
        return
    minimum = schema.get("minItems")
    if isinstance(minimum, int) and len(instance) < minimum:
        errors.append(f"{path}: fewer than minItems")
    items = schema.get("items")
    if isinstance(items, dict):
        for index, value in enumerate(instance):
            _validate(items, value, f"{path}[{index}]", errors)


def _type_matches(expected: object, instance: object) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    return True
