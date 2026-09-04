"""Loader and query model for canonical ODCS semantics.

Adapted from ``fl_op.contracts.canonical_model`` in
https://github.com/volod/fl-op at revision
1f452ecaeded92c6bbbd4a86de9ded1ea7444e60, under the MIT License.
"""

import pathlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from arxiv_int.contracts._yaml import load_mapping


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
            if isinstance(value, dict):
                return value
    return None


def _entity_fields(
    entity: str, document: dict[str, Any], binding_property: str
) -> list[CanonicalField]:
    fields: list[CanonicalField] = []
    schemas = document.get("schema", [])
    if not isinstance(schemas, list):
        return fields
    for schema in schemas:
        if not isinstance(schema, dict):
            continue
        properties = schema.get("properties", [])
        if not isinstance(properties, list):
            continue
        for prop in properties:
            if not isinstance(prop, dict):
                continue
            binding = custom_property(prop.get("customProperties"), binding_property)
            if binding is None:
                continue
            fields.append(
                CanonicalField(
                    entity=entity,
                    name=str(prop["name"]),
                    binding=str(binding["binding"]),
                    semantic_term=str(binding["semanticTerm"]),
                    required=bool(prop.get("required", False)),
                    canonical_unit=binding.get("canonicalUnit"),
                    quantity_kind=binding.get("quantityKind"),
                    uses=tuple(binding.get("planningUse") or ()),
                )
            )
    return fields


def load_canonical_model(
    root: pathlib.Path,
    *,
    binding_property: str = "canonicalBinding",
) -> CanonicalModel:
    """Load a canonical model index and its referenced ODCS entity contracts."""
    index = load_mapping(root / "model.yaml")
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
    for entity, raw in (index.get("entities") or {}).items():
        contract = (raw or {}).get("contract")
        if contract:
            fields.extend(_entity_fields(entity, load_mapping(root / contract), binding_property))
    return CanonicalModel(str(metadata.get("canonicalModelRef", "")), terms, tuple(fields))
