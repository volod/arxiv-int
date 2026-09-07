"""Ontology evolution classification fixtures."""

import copy

import pytest

pytest.importorskip("rdflib")

from arxiv_int.ontology.evolution import (
    ONTOLOGY_ADDITIVE,
    ONTOLOGY_BREAKING,
    ONTOLOGY_IDENTICAL,
    classify_ontology_evolution,
    ontology_snapshot,
    version_policy_errors,
)
from arxiv_int.ontology.load import load_ontology_catalog
from tests.ontology import ontology_root


def test_identical_snapshot_is_identical() -> None:
    snapshot = ontology_snapshot(load_ontology_catalog(ontology_root()))
    change, details = classify_ontology_evolution(snapshot, snapshot)
    assert change == ONTOLOGY_IDENTICAL
    assert details == ()
    assert version_policy_errors(change, "1.0.0", "1.0.0") == []


def test_added_predicate_is_additive_and_needs_minor_bump() -> None:
    baseline = ontology_snapshot(load_ontology_catalog(ontology_root()))
    current = copy.deepcopy(baseline)
    current["catalog"]["predicates"].append(
        {
            "termId": "pred.example-new",
            "uri": "https://arxiv-int.local/ns/pred/exampleNew",
            "kind": "object",
            "status": "active",
            "contractBinding": "fact.predicateId",
            "labels": {"en": "example"},
            "domains": [],
            "ranges": [],
            "functional": False,
            "deprecated": False,
            "successor": None,
            "quantityKind": None,
            "canonicalUnit": None,
        }
    )
    current["version"] = "1.1.0"
    change, details = classify_ontology_evolution(baseline, current)
    assert change == ONTOLOGY_ADDITIVE
    assert any("pred.example-new" in item for item in details)
    assert version_policy_errors(change, "1.0.0", "1.1.0") == []
    assert version_policy_errors(change, "1.0.0", "1.0.0")


def test_removed_active_predicate_is_breaking_and_needs_major_bump() -> None:
    baseline = ontology_snapshot(load_ontology_catalog(ontology_root()))
    current = copy.deepcopy(baseline)
    current["catalog"]["predicates"] = [
        item for item in current["catalog"]["predicates"] if item["termId"] != "pred.mentions"
    ]
    current["version"] = "1.0.0"
    change, details = classify_ontology_evolution(baseline, current)
    assert change == ONTOLOGY_BREAKING
    assert any("pred.mentions" in item for item in details)
    assert version_policy_errors(change, "1.0.0", "1.0.0")
    assert version_policy_errors(change, "1.0.0", "2.0.0") == []
