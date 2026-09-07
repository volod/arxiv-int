"""Pure schema-baseline and semantic-version evolution primitives."""

import json
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

CHANGE_IDENTICAL = "identical"
CHANGE_ADDITIVE = "additive"
CHANGE_BREAKING = "breaking"
CHANGE_REINDEX = "reindex"
CHANGE_VECTOR_DIMENSION = "vector-dimension"
CHANGE_SEMANTIC_RETARGET = "semantic-retarget"
CHANGE_GRAPH_PROJECTION = "graph-projection"
FIELD_IDENTITY_SCHEMA_QUALIFIED = "schema-qualified"
_SCHEMA_FIELD_SEP = "."

_MAJOR_CLASSES = frozenset(
    {
        CHANGE_BREAKING,
        CHANGE_VECTOR_DIMENSION,
        CHANGE_SEMANTIC_RETARGET,
    }
)
_MINOR_CLASSES = frozenset({CHANGE_ADDITIVE, CHANGE_REINDEX, CHANGE_GRAPH_PROJECTION})


@dataclass(frozen=True)
class ChangeReport:
    """Classification of a physical schema change."""

    change_class: str
    details: tuple[str, ...] = field(default_factory=tuple)


def schema_field_id(schema_id: str, field_name: str) -> str:
    """Return the stable schema-qualified identity for one physical field."""
    if not schema_id or not field_name:
        raise ValueError("schema id and field name are required")
    if _SCHEMA_FIELD_SEP in schema_id:
        raise ValueError(f"schema id must not contain {_SCHEMA_FIELD_SEP!r}: {schema_id!r}")
    return f"{schema_id}{_SCHEMA_FIELD_SEP}{field_name}"


def schema_identity(schema: dict[str, Any], index: int) -> str:
    """Return the declared schema name or a stable positional id."""
    name = schema.get("name")
    if name is None or name == "":
        return f"#{index}"
    text = str(name)
    if _SCHEMA_FIELD_SEP in text:
        raise ValueError(f"schema name must not contain {_SCHEMA_FIELD_SEP!r}: {text!r}")
    return text


def _schema_properties(
    odcs_document: dict[str, Any],
) -> Iterator[tuple[str, dict[str, Any]]]:
    schemas = odcs_document.get("schema", [])
    if not isinstance(schemas, list):
        return
    seen_schemas: set[str] = set()
    for index, schema in enumerate(schemas):
        if not isinstance(schema, dict):
            continue
        schema_id = schema_identity(schema, index)
        if schema_id in seen_schemas:
            raise ValueError(f"duplicate schema identity '{schema_id}'")
        seen_schemas.add(schema_id)
        properties = schema.get("properties", [])
        if not isinstance(properties, list):
            continue
        for prop in properties:
            if isinstance(prop, dict):
                yield schema_id, prop


def schema_snapshot(
    odcs_document: dict[str, Any],
    contract_id: str,
    *,
    fingerprints: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Extract schema-qualified fields that participate in physical compatibility."""
    fields: dict[str, dict[str, Any]] = {}
    for schema_id, prop in _schema_properties(odcs_document):
        if "name" not in prop:
            raise ValueError(f"schema '{schema_id}' has a property without a name")
        identity = schema_field_id(schema_id, str(prop["name"]))
        if identity in fields:
            raise ValueError(f"duplicate field identity '{identity}'")
        fields[identity] = {
            "logicalType": prop.get("logicalType", ""),
            "physicalType": prop.get("physicalType", ""),
            "required": bool(prop.get("required", False)),
        }
    snapshot: dict[str, Any] = {
        "contractId": contract_id,
        "fieldIdentity": FIELD_IDENTITY_SCHEMA_QUALIFIED,
        "odcsId": str(odcs_document.get("id", contract_id)),
        "version": str(odcs_document.get("version", "")),
        "fields": fields,
    }
    if fingerprints:
        snapshot["fingerprints"] = {
            key: value for key, value in sorted(fingerprints.items()) if value
        }
    return snapshot


def migrate_schema_snapshot(snapshot: dict[str, Any], *, schema_id: str) -> dict[str, Any]:
    """Upgrade a legacy bare-field snapshot under one reviewed schema identity.

    Unmigrated legacy snapshots compared to schema-qualified snapshots report every
    field as removed and re-added, which classifies as breaking. Operators must run
    this migration (or re-freeze) before compatibility checks. Stored semantic
    metadata hashes are unchanged by this structural upgrade.
    """
    if snapshot.get("fieldIdentity") == FIELD_IDENTITY_SCHEMA_QUALIFIED:
        return dict(snapshot)
    raw_fields = snapshot.get("fields")
    if not isinstance(raw_fields, dict):
        raise ValueError("legacy schema snapshot fields must be a mapping")
    if not schema_id or _SCHEMA_FIELD_SEP in schema_id:
        raise ValueError(f"migration schema id is invalid: {schema_id!r}")
    migrated: dict[str, Any] = {}
    for name, spec in raw_fields.items():
        text = str(name)
        if _SCHEMA_FIELD_SEP in text:
            raise ValueError(
                f"legacy snapshot field '{text}' already looks schema-qualified; "
                "refuse an ambiguous migration"
            )
        identity = schema_field_id(schema_id, text)
        if identity in migrated:
            raise ValueError(f"duplicate field identity '{identity}' during migration")
        migrated[identity] = spec
    upgraded = dict(snapshot)
    upgraded["fieldIdentity"] = FIELD_IDENTITY_SCHEMA_QUALIFIED
    upgraded["fields"] = migrated
    return upgraded


def classify_change(
    baseline_fields: dict[str, Any], current_fields: dict[str, Any]
) -> ChangeReport:
    """Classify identical, optional-additive, and breaking field changes."""
    details: list[str] = []
    breaking = False
    for name in sorted(baseline_fields.keys() - current_fields.keys()):
        breaking = True
        details.append(f"removed field '{name}'")
    for name in sorted(current_fields.keys() - baseline_fields.keys()):
        if bool(current_fields[name].get("required", False)):
            breaking = True
            details.append(f"added required field '{name}'")
        else:
            details.append(f"added optional field '{name}'")
    for name in sorted(baseline_fields.keys() & current_fields.keys()):
        if baseline_fields[name] != current_fields[name]:
            breaking = True
            details.append(f"changed field '{name}'")
    if breaking:
        return ChangeReport(CHANGE_BREAKING, tuple(details))
    if details:
        return ChangeReport(CHANGE_ADDITIVE, tuple(details))
    return ChangeReport(CHANGE_IDENTICAL)


def _semver(version: str) -> tuple[int, int, int]:
    try:
        major, minor, patch = version.split(".")
        return int(major), int(minor), int(patch)
    except (AttributeError, ValueError) as error:
        raise ValueError(f"Invalid semantic version: {version}") from error


def version_policy_errors(
    contract_id: str,
    baseline_version: str,
    current_version: str,
    change: ChangeReport,
) -> tuple[str, ...]:
    """Enforce version bumps for classified physical and projection changes."""
    baseline = _semver(baseline_version)
    current = _semver(current_version)
    if current < baseline:
        return (f"{contract_id}: version moved backward",)
    klass = change.change_class
    if klass in _MINOR_CLASSES and current[:2] <= baseline[:2]:
        return (f"{contract_id}: {klass} change requires a minor version bump",)
    if klass in _MAJOR_CLASSES and current[0] <= baseline[0]:
        return (f"{contract_id}: {klass} change requires a major version bump",)
    return ()


def baseline_history(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Read history, accepting an older single-snapshot baseline."""
    history = document.get("history")
    if isinstance(history, list):
        return [item for item in history if isinstance(item, dict)]
    if document.get("version"):
        return [{key: value for key, value in document.items() if key != "history"}]
    return []


def freeze_baseline(destination: pathlib.Path, snapshot: dict[str, Any]) -> pathlib.Path:
    """Append a changed reviewed snapshot and write deterministic JSON."""
    existing: dict[str, Any] = {}
    if destination.exists():
        loaded = json.loads(destination.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Evolution baseline is not an object: {destination}")
        existing = loaded
    history = baseline_history(existing)
    if not history or history[-1] != snapshot:
        history.append(snapshot)
    payload = {**snapshot, "history": history}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination
