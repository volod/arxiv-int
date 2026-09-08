"""Cross-document integrity checks for the product contract registry."""

import pathlib
import re
from typing import Any

from arxiv_int.contracts.catalog.canonical import load_canonical_model
from arxiv_int.contracts.catalog.fingerprint import semantic_metadata_hash
from arxiv_int.contracts.catalog.loaders import load_mapping_document, load_odcs_document
from arxiv_int.contracts.catalog.odcs_ext import canonical_binding, project_extension
from arxiv_int.contracts.catalog.registry import FileRegistry

_SHORTHAND = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def _iter_schema_dicts(odcs: dict[str, Any]) -> list[dict[str, Any]]:
    schemas = odcs.get("schema") or []
    return [schema for schema in schemas if isinstance(schema, dict)]


def _iter_property_dicts(schema: dict[str, Any]) -> list[dict[str, Any]]:
    properties = schema.get("properties") or []
    return [prop for prop in properties if isinstance(prop, dict)]


def _relationship_tos(container: dict[str, Any]) -> list[str]:
    return [
        str(rel["to"])
        for rel in (container.get("relationships") or [])
        if isinstance(rel, dict) and "to" in rel
    ]


def _schema_index(odcs: dict[str, Any]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for schema in _iter_schema_dicts(odcs):
        if "name" not in schema:
            continue
        names = {str(prop["name"]) for prop in _iter_property_dicts(schema) if "name" in prop}
        index[str(schema["name"])] = names
    return index


def _relationship_targets(odcs: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    for schema in _iter_schema_dicts(odcs):
        targets.extend(_relationship_tos(schema))
        for prop in _iter_property_dicts(schema):
            targets.extend(_relationship_tos(prop))
    return targets


def _primary_key_props(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return [prop for prop in _iter_property_dicts(schema) if prop.get("primaryKey")]


def _required_identity_findings(contract_id: str, odcs: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    for schema in _iter_schema_dicts(odcs):
        schema_name = str(schema.get("name", "<unnamed>"))
        primary = _primary_key_props(schema)
        if not primary:
            findings.append(f"{contract_id}: schema '{schema_name}' has no primaryKey identity")
            continue
        for prop in primary:
            if prop.get("required", False):
                continue
            findings.append(
                f"{contract_id}: schema '{schema_name}' primaryKey "
                f"'{prop.get('name')}' must be required"
            )
    return findings


def _binding_for_source(odcs: dict[str, Any], source: str) -> dict[str, Any] | None:
    for schema in _iter_schema_dicts(odcs):
        for prop in _iter_property_dicts(schema):
            if str(prop.get("name")) == source:
                return canonical_binding(prop.get("customProperties"))
    return None


def _record_binding(bindings: dict[str, str], contract_id: str, binding: str) -> str | None:
    if not binding:
        return None
    owner = bindings.get(binding)
    if owner and owner != contract_id:
        return f"{contract_id}: binding '{binding}' already used by {owner}"
    bindings[binding] = contract_id
    return None


def _check_mapping(
    contract_id: str,
    odcs: dict[str, Any],
    mapping: dict[str, Any],
    bindings: dict[str, str],
) -> list[str]:
    findings: list[str] = []
    source_fields = {
        name for schema_fields in _schema_index(odcs).values() for name in schema_fields
    }
    for item in mapping.get("fieldMappings") or []:
        if not isinstance(item, dict):
            continue
        source = str(item.get("sourceField", ""))
        binding = str(item.get("binding", ""))
        if source and source not in source_fields:
            findings.append(f"{contract_id}: mapping sourceField '{source}' missing from ODCS")
        conflict = _record_binding(bindings, contract_id, binding)
        if conflict:
            findings.append(conflict)
        if source and _binding_for_source(odcs, source) is None:
            findings.append(f"{contract_id}: ODCS field '{source}' lacks canonicalBinding")
    return findings


def _check_odcs_document(
    contract_id: str,
    odcs: dict[str, Any],
    *,
    odcs_ids: set[str],
) -> list[str]:
    findings: list[str] = []
    odcs_id = str(odcs.get("id", ""))
    if not odcs_id:
        findings.append(f"{contract_id}: ODCS id is missing")
    elif odcs_id in odcs_ids:
        findings.append(f"{contract_id}: duplicate ODCS id '{odcs_id}'")
    else:
        odcs_ids.add(odcs_id)
    if not str(odcs.get("version", "")):
        findings.append(f"{contract_id}: ODCS version is missing")
    if str(odcs.get("apiVersion", "")) != "v3.1.0":
        findings.append(f"{contract_id}: apiVersion must be v3.1.0")
    findings.extend(_required_identity_findings(contract_id, odcs))
    extension = project_extension(odcs.get("customProperties"))
    if extension is None or not extension.get("schema") or not extension.get("table"):
        findings.append(f"{contract_id}: x-arxiv-int postgres schema/table hints are required")
    return findings


def _check_relationships(
    odcs_by_contract: dict[str, dict[str, Any]],
    field_index: dict[str, set[str]],
) -> list[str]:
    findings: list[str] = []
    for contract_id, odcs in odcs_by_contract.items():
        for target in _relationship_targets(odcs):
            if not _SHORTHAND.match(target):
                findings.append(f"{contract_id}: relationship target '{target}' is malformed")
                continue
            schema_name, field_name = target.split(".", 1)
            if schema_name not in field_index or field_name not in field_index[schema_name]:
                findings.append(
                    f"{contract_id}: relationship target '{target}' is not a registered field"
                )
    return findings


def _check_canonical_model(contracts_root: pathlib.Path, entities: dict[str, str]) -> list[str]:
    model_path = contracts_root / "canonical"
    if not model_path.is_dir():
        return ["canonical model directory is missing"]
    try:
        model = load_canonical_model(model_path)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [f"canonical model failed to load: {error}"]
    findings: list[str] = []
    for entity, contract_id in entities.items():
        if entity not in model.entities():
            findings.append(f"canonical model missing entity '{entity}' from {contract_id}")
        elif not model.required_bindings(entity):
            findings.append(f"canonical entity '{entity}' has no required bindings")
    for entity in model.entities():
        if entity not in entities:
            findings.append(f"canonical model entity '{entity}' is not registered")
    return findings


def _register_entity(
    entities: dict[str, str], contract_id: str, canonical_entity: str | None
) -> list[str]:
    if not canonical_entity:
        return []
    prior = entities.get(canonical_entity)
    if prior:
        return [
            f"canonical entity '{canonical_entity}' registered twice ({prior} and {contract_id})"
        ]
    entities[canonical_entity] = contract_id
    return []


def validate_registry_integrity(contracts_root: pathlib.Path) -> list[str]:
    """Check ids, versions, refs, bindings, relationships, and required identities."""
    findings: list[str] = []
    registry = FileRegistry(contracts_root)
    odcs_by_contract: dict[str, dict[str, Any]] = {}
    field_index: dict[str, set[str]] = {}
    bindings: dict[str, str] = {}
    entities: dict[str, str] = {}
    odcs_ids: set[str] = set()

    for contract_id in registry.contract_ids():
        entry = registry.get_entry(contract_id)
        findings.extend(_register_entity(entities, contract_id, entry.canonical_entity))
        try:
            odcs = registry.load_odcs(contract_id)
            load_odcs_document(odcs)
        except (OSError, ValueError, KeyError, TypeError) as error:
            findings.append(f"{contract_id}: ODCS load failed: {error}")
            continue
        odcs_by_contract[contract_id] = odcs
        findings.extend(_check_odcs_document(contract_id, odcs, odcs_ids=odcs_ids))
        for schema_name, fields in _schema_index(odcs).items():
            field_index[schema_name] = fields
        try:
            mapping = registry.load_mapping(contract_id)
            load_mapping_document(mapping)
            registry.verify_semantic_fingerprint(contract_id)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            findings.append(f"{contract_id}: mapping load/fingerprint failed: {error}")
            continue
        findings.extend(_check_mapping(contract_id, odcs, mapping, bindings))

    findings.extend(_check_relationships(odcs_by_contract, field_index))
    findings.extend(_check_canonical_model(contracts_root, entities))
    return findings


def reviewed_semantic_hashes(contracts_root: pathlib.Path) -> dict[str, str]:
    """Compute semantic metadata hashes for every mapped registry contract."""
    registry = FileRegistry(contracts_root)
    return {
        contract_id: semantic_metadata_hash(registry.load_mapping(contract_id))
        for contract_id in registry.contract_ids()
        if registry.get_entry(contract_id).mapping_ref is not None
    }
