"""Versioned ontology assets: RDF vocabulary, SHACL, bindings, and evolution."""

from arxiv_int.ontology.catalog import OntologyCatalog, OntologyClass, OntologyPredicate
from arxiv_int.ontology.check import OntologyCheckReport, check_ontology
from arxiv_int.ontology.evolution import (
    ONTOLOGY_ADDITIVE,
    ONTOLOGY_BREAKING,
    ONTOLOGY_IDENTICAL,
    classify_ontology_evolution,
)
from arxiv_int.ontology.generate import generate_ontology_bindings
from arxiv_int.ontology.load import load_ontology_catalog
from arxiv_int.ontology.paths import ontology_root_for
from arxiv_int.ontology.validate import FactAssertion, validate_assertions

__all__ = [
    "ONTOLOGY_ADDITIVE",
    "ONTOLOGY_BREAKING",
    "ONTOLOGY_IDENTICAL",
    "FactAssertion",
    "OntologyCatalog",
    "OntologyCheckReport",
    "OntologyClass",
    "OntologyPredicate",
    "check_ontology",
    "classify_ontology_evolution",
    "generate_ontology_bindings",
    "load_ontology_catalog",
    "ontology_root_for",
    "validate_assertions",
]
