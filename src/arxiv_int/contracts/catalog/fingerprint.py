"""Deterministic semantic fingerprints for contract metadata."""

import hashlib
import json
from typing import Any, cast

_KNOWN_FIELD_KEYS = frozenset(
    {
        "sourceField",
        "binding",
        "semanticTerm",
        "canonicalUnit",
        "quantityKind",
        "planningUse",
    }
)


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _contract_metadata(document: dict[str, Any]) -> dict[str, Any] | None:
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        return None
    return {key: value for key, value in metadata.items() if key != "domain"}


def _field_metadata(item: Any, *, index: int) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(item, dict):
        return None
    known = _KNOWN_FIELD_KEYS.intersection(item)
    if not known:
        return None
    if "sourceField" not in item:
        raise ValueError(f"fieldMappings[{index}] is missing required sourceField")
    source = item["sourceField"]
    if source is None or str(source).strip() == "":
        raise ValueError(f"fieldMappings[{index}] has an empty sourceField")
    key = f"field:{source}"
    value = {name: raw for name, raw in item.items() if name != "sourceField"}
    return key, value


def semantic_metadata(document: dict[str, Any]) -> dict[str, Any]:
    """Select mapping metadata whose change can alter canonical meaning."""
    blocks: dict[str, Any] = {}
    metadata = _contract_metadata(document)
    if metadata is not None:
        blocks["contract"] = metadata
    field_mappings = document.get("fieldMappings", [])
    items = field_mappings if isinstance(field_mappings, list) else []
    seen_sources: set[str] = set()
    seen_bindings: set[str] = set()
    for index, item in enumerate(items):
        block = _field_metadata(item, index=index)
        if block is None:
            continue
        key, value = block
        if key in seen_sources:
            raise ValueError(f"duplicate field mapping sourceField for {key}")
        seen_sources.add(key)
        binding = value.get("binding")
        if isinstance(binding, str) and binding:
            if binding in seen_bindings:
                raise ValueError(f"ambiguous binding '{binding}' used by multiple fields")
            seen_bindings.add(binding)
        if key in blocks:
            raise ValueError(f"duplicate semantic metadata block '{key}'")
        blocks[key] = value
    return cast(dict[str, Any], _normalize(blocks))


def semantic_metadata_hash(document: dict[str, Any]) -> str:
    """Return SHA-256 over normalized semantic mapping metadata."""
    canonical = json.dumps(semantic_metadata(document), separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
