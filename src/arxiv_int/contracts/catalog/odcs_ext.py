"""Project-specific ODCS extension helpers under ``x-arxiv-int``."""

from typing import Any

PROJECT_EXTENSION = "x-arxiv-int"


def custom_property(properties: Any, name: str) -> dict[str, Any] | None:
    """Return a mapping-valued ODCS custom property."""
    if not isinstance(properties, list):
        return None
    for item in properties:
        if isinstance(item, dict) and item.get("property") == name:
            value = item.get("value")
            if value is None:
                return None
            if not isinstance(value, dict):
                raise ValueError(f"custom property '{name}' must be a mapping")
            return value
    return None


def project_extension(properties: Any) -> dict[str, Any] | None:
    """Return the namespaced project extension mapping, if present."""
    return custom_property(properties, PROJECT_EXTENSION)


def canonical_binding(
    properties: Any,
    *,
    legacy_property: str = "canonicalBinding",
) -> dict[str, Any] | None:
    """Return a field binding from ``x-arxiv-int`` or a legacy top-level property.

    Unknown keys inside the binding mapping are preserved for callers that need
    them; required ``binding`` and ``semanticTerm`` keys are enforced by the
    canonical loader.
    """
    extension = project_extension(properties)
    if extension is not None:
        nested = extension.get("canonicalBinding")
        if nested is None:
            return None
        if not isinstance(nested, dict):
            raise ValueError("x-arxiv-int.canonicalBinding must be a mapping")
        return nested
    return custom_property(properties, legacy_property)
