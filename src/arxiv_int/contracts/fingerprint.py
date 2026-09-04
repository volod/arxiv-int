"""Deterministic semantic fingerprints for contract metadata.

Adapted from ``fl_op.contracts.fingerprint`` in
https://github.com/volod/fl-op at revision
1f452ecaeded92c6bbbd4a86de9ded1ea7444e60, under the MIT License.
"""

import hashlib
import json
from typing import Any, cast


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


def _field_metadata(item: Any) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(item, dict) or "sourceField" not in item:
        return None
    key = f"field:{item['sourceField']}"
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
    for item in items:
        block = _field_metadata(item)
        if block is not None:
            blocks[block[0]] = block[1]
    return cast(dict[str, Any], _normalize(blocks))


def semantic_metadata_hash(document: dict[str, Any]) -> str:
    """Return SHA-256 over normalized semantic mapping metadata."""
    canonical = json.dumps(semantic_metadata(document), separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
