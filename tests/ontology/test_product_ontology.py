"""Product ontology parse, catalog, and gate tests."""

import pytest

pytest.importorskip("rdflib")
pytest.importorskip("pyshacl")
pytest.importorskip("owlrl")

from arxiv_int.ontology.check import check_ontology
from arxiv_int.ontology.generate import check_generation_drift, generate_ontology_bindings
from arxiv_int.ontology.load import load_ontology_catalog, load_ontology_graphs
from arxiv_int.ontology.reason import disjointness_inconsistent
from tests.ontology import ontology_root, project_root


def test_product_ontology_rdf_parses() -> None:
    core, mappings, shapes = load_ontology_graphs(ontology_root())
    assert len(core) > 0
    assert len(mappings) > 0
    assert len(shapes) > 0


def test_product_catalog_exposes_active_predicates_with_bindings() -> None:
    catalog = load_ontology_catalog(ontology_root())
    assert catalog.version == "1.0.0"
    assert catalog.classes
    active = catalog.active_predicates()
    assert active
    assert all(item.contract_binding == "fact.predicateId" for item in active)
    assert catalog.predicate_by_term_id("pred.same-as") is not None
    assert catalog.predicate_by_term_id("pred.same-as").status == "deprecated"


def test_product_ontology_check_passes() -> None:
    report = check_ontology(ontology_root(), project_root=project_root())
    assert report.ok, report.findings
    assert report.checked_classes >= 20
    assert report.checked_predicates >= 10


def test_generated_bindings_are_stable() -> None:
    root = ontology_root()
    first = generate_ontology_bindings(root)
    second = generate_ontology_bindings(root)
    assert first == second
    assert check_generation_drift(root) == []


def test_owlrl_detects_natural_person_legal_entity_clash() -> None:
    natural = "https://arxiv-int.local/ns/class/NaturalPerson"
    legal = "https://arxiv-int.local/ns/class/LegalEntity"
    assert disjointness_inconsistent((natural, legal), ontology_root=ontology_root())
    assert not disjointness_inconsistent((natural,), ontology_root=ontology_root())
