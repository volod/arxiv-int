"""Loader and query model for canonical ODCS semantics."""

import pathlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from arxiv_int.contracts._yaml import load_mapping
from arxiv_int.contracts.paths import resolve_rooted_reference

_REQUIRED_BINDING_KEYS = frozenset({"binding", "semanticTerm"})


@dataclass(frozen=True)
class SemanticTerm:
    """One controlled-vocabulary term."""

    term: str
    value_type: str | None = None
    quantity_kind: str | None = None
    canonical_unit: str | None = None


@dataclass(frozen=True)
class CanonicalField:
    """One physical field bound to a canonical meaning."""

    entity: str
    name: str
    binding: str
    semantic_term: str
    required: bool = False
    canonical_unit: str | None = None
    quantity_kind: str | None = None
    uses: tuple[str, ...] = ()


@dataclass(frozen=True)
class CanonicalModel:
    """Immutable canonical entities, fields, and semantic vocabulary."""

    model_ref: str
    semantic_terms: Mapping[str, SemanticTerm]
    fields: tuple[CanonicalField, ...]
    _by_entity: Mapping[str, tuple[CanonicalField, ...]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        grouped: dict[str, list[CanonicalField]] = {}
        for item in self.fields:
            grouped.setdefault(item.entity, []).append(item)
        object.__setattr__(self, "semantic_terms", MappingProxyType(dict(self.semantic_terms)))
        object.__setattr__(
            self,
            "_by_entity",
            MappingProxyType({key: tuple(value) for key, value in grouped.items()}),
        )

    def entities(self) -> tuple[str, ...]:
        return tuple(self._by_entity)

    def fields_for(self, entity: str) -> tuple[CanonicalField, ...]:
        return self._by_entity.get(entity, ())

    def required_bindings(self, entity: str) -> frozenset[str]:
        return frozenset(item.binding for item in self.fields_for(entity) if item.required)

    def has_term(self, term: str) -> bool:
        return term in self.semantic_terms


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


def _require_binding(binding: dict[str, Any], *, entity: str, field_name: str) -> None:
    missing = sorted(
        key for key in _REQUIRED_BINDING_KEYS if key not in binding or binding[key] in (None, "")
    )
    if missing:
        raise ValueError(
            f"canonical binding for {entity}.{field_name} is missing required keys: "
            + ", ".join(missing)
        )


def _schema_property_maps(document: dict[str, Any]) -> list[dict[str, Any]]:
    schemas = document.get("schema", [])
    if not isinstance(schemas, list):
        return []
    properties: list[dict[str, Any]] = []
    for schema in schemas:
        if not isinstance(schema, dict):
            continue
        raw = schema.get("properties", [])
        if not isinstance(raw, list):
            continue
        properties.extend(item for item in raw if isinstance(item, dict))
    return properties


def _bound_field(
    entity: str,
    prop: dict[str, Any],
    binding_property: str,
    *,
    seen_bindings: set[str],
    seen_fields: set[tuple[str, str]],
) -> CanonicalField | None:
    if "name" not in prop:
        raise ValueError(f"entity '{entity}' has a property without a name")
    field_name = str(prop["name"])
    binding = custom_property(prop.get("customProperties"), binding_property)
    if binding is None:
        return None
    field_key = (entity, field_name)
    if field_key in seen_fields:
        raise ValueError(f"duplicate physical field '{entity}.{field_name}'")
    _require_binding(binding, entity=entity, field_name=field_name)
    binding_name = str(binding["binding"])
    if binding_name in seen_bindings:
        raise ValueError(f"ambiguous binding '{binding_name}' used by multiple fields")
    seen_fields.add(field_key)
    seen_bindings.add(binding_name)
    return CanonicalField(
        entity=entity,
        name=field_name,
        binding=binding_name,
        semantic_term=str(binding["semanticTerm"]),
        required=bool(prop.get("required", False)),
        canonical_unit=binding.get("canonicalUnit"),
        quantity_kind=binding.get("quantityKind"),
        uses=tuple(binding.get("planningUse") or ()),
    )


def _entity_fields(
    entity: str,
    document: dict[str, Any],
    binding_property: str,
    *,
    seen_bindings: set[str],
    seen_fields: set[tuple[str, str]],
) -> list[CanonicalField]:
    fields: list[CanonicalField] = []
    for prop in _schema_property_maps(document):
        bound = _bound_field(
            entity,
            prop,
            binding_property,
            seen_bindings=seen_bindings,
            seen_fields=seen_fields,
        )
        if bound is not None:
            fields.append(bound)
    return fields


def load_canonical_model(
    root: pathlib.Path,
    *,
    binding_property: str = "canonicalBinding",
) -> CanonicalModel:
    """Load a canonical model index and its referenced ODCS entity contracts."""
    resolved_root = root.expanduser().resolve()
    index = load_mapping(resolved_root / "model.yaml")
    metadata = index.get("metadata") or {}
    terms: dict[str, SemanticTerm] = {}
    for term, raw in (index.get("semanticTerms") or {}).items():
        spec = raw or {}
        terms[term] = SemanticTerm(
            term=term,
            value_type=spec.get("valueType"),
            quantity_kind=spec.get("quantityKind"),
            canonical_unit=spec.get("canonicalUnit"),
        )
    fields: list[CanonicalField] = []
    seen_bindings: set[str] = set()
    seen_fields: set[tuple[str, str]] = set()
    for entity, raw in (index.get("entities") or {}).items():
        contract = (raw or {}).get("contract")
        if not contract:
            continue
        path = resolve_rooted_reference(
            resolved_root,
            str(contract),
            label=f"Canonical contract reference for '{entity}'",
        )
        fields.extend(
            _entity_fields(
                entity,
                load_mapping(path),
                binding_property,
                seen_bindings=seen_bindings,
                seen_fields=seen_fields,
            )
        )
    return CanonicalModel(str(metadata.get("canonicalModelRef", "")), terms, tuple(fields))
