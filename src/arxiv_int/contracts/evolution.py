"""Pure schema-baseline and semantic-version evolution primitives.

Adapted from ``fl_op.contracts.evolution`` in https://github.com/volod/fl-op at
revision 1f452ecaeded92c6bbbd4a86de9ded1ea7444e60, under the MIT License.
"""

import json
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

CHANGE_IDENTICAL = "identical"
CHANGE_ADDITIVE = "additive"
CHANGE_BREAKING = "breaking"


@dataclass(frozen=True)
class ChangeReport:
    """Classification of a physical schema change."""

    change_class: str
    details: tuple[str, ...] = field(default_factory=tuple)


def _schema_properties(odcs_document: dict[str, Any]) -> Iterator[dict[str, Any]]:
    schemas = odcs_document.get("schema", [])
    if not isinstance(schemas, list):
        return
    for schema in schemas:
        if not isinstance(schema, dict):
            continue
        properties = schema.get("properties", [])
        if not isinstance(properties, list):
            continue
        for prop in properties:
            if isinstance(prop, dict) and "name" in prop:
                yield prop


def schema_snapshot(
    odcs_document: dict[str, Any],
    contract_id: str,
    *,
    fingerprints: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Extract fields that participate in physical compatibility."""
    fields: dict[str, dict[str, Any]] = {}
    for prop in _schema_properties(odcs_document):
        fields[str(prop["name"])] = {
            "logicalType": prop.get("logicalType", ""),
            "physicalType": prop.get("physicalType", ""),
            "required": bool(prop.get("required", False)),
        }
    snapshot: dict[str, Any] = {
        "contractId": contract_id,
        "odcsId": str(odcs_document.get("id", contract_id)),
        "version": str(odcs_document.get("version", "")),
        "fields": fields,
    }
    if fingerprints:
        snapshot["fingerprints"] = {
            key: value for key, value in sorted(fingerprints.items()) if value
        }
    return snapshot


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
    """Enforce minor bumps for additive and major bumps for breaking changes."""
    baseline = _semver(baseline_version)
    current = _semver(current_version)
    if current < baseline:
        return (f"{contract_id}: version moved backward",)
    if change.change_class == CHANGE_ADDITIVE and current[:2] <= baseline[:2]:
        return (f"{contract_id}: additive change requires a minor version bump",)
    if change.change_class == CHANGE_BREAKING and current[0] <= baseline[0]:
        return (f"{contract_id}: breaking change requires a major version bump",)
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
