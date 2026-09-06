"""Structured catalog extracted from ontology RDF assets."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class OntologyClass:
    """One OWL/RDFS class with stable term identity."""

    uri: str
    term_id: str
    status: str
    labels: Mapping[str, str]
    parents: tuple[str, ...]
    disjoint_with: tuple[str, ...]


@dataclass(frozen=True)
class OntologyPredicate:
    """One object or datatype property usable as a fact predicate."""

    uri: str
    term_id: str
    status: str
    kind: str
    contract_binding: str
    labels: Mapping[str, str]
    domains: tuple[str, ...]
    ranges: tuple[str, ...]
    functional: bool
    deprecated: bool
    successor: str | None
    quantity_kind: str | None
    canonical_unit: str | None


@dataclass(frozen=True)
class OntologyCatalog:
    """Immutable view of versioned ontology assets."""

    ontology_id: str
    version: str
    classes: Mapping[str, OntologyClass]
    predicates: Mapping[str, OntologyPredicate]
    semantic_matches: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "classes", MappingProxyType(dict(self.classes)))
        object.__setattr__(self, "predicates", MappingProxyType(dict(self.predicates)))
        object.__setattr__(
            self,
            "semantic_matches",
            MappingProxyType({key: tuple(value) for key, value in self.semantic_matches.items()}),
        )

    def active_predicates(self) -> tuple[OntologyPredicate, ...]:
        return tuple(item for item in self.predicates.values() if item.status == "active")

    def predicate_by_term_id(self, term_id: str) -> OntologyPredicate | None:
        for item in self.predicates.values():
            if item.term_id == term_id:
                return item
        return None

    def predicate_by_uri_or_term(self, key: str) -> OntologyPredicate | None:
        if key in self.predicates:
            return self.predicates[key]
        return self.predicate_by_term_id(key)

    def class_by_uri_or_term(self, key: str) -> OntologyClass | None:
        if key in self.classes:
            return self.classes[key]
        for item in self.classes.values():
            if item.term_id == key:
                return item
        return None

    def subclass_closure(self, class_uri: str) -> frozenset[str]:
        """Return ``class_uri`` and all ancestor class URIs."""
        found: set[str] = set()
        stack = [class_uri]
        while stack:
            current = stack.pop()
            if current in found:
                continue
            found.add(current)
            item = self.classes.get(current)
            if item is None:
                continue
            stack.extend(item.parents)
        return frozenset(found)
