"""Focused application-validator edge cases."""

import pytest

pytest.importorskip("rdflib")

from arxiv_int.ontology.load import load_ontology_catalog
from arxiv_int.ontology.validate import FactAssertion, validate_assertions
from tests.ontology import ontology_root

_XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
_XSD_DECIMAL = "http://www.w3.org/2001/XMLSchema#decimal"


def test_unknown_and_deprecated_predicates_are_rejected() -> None:
    catalog = load_ontology_catalog(ontology_root())
    unknown = validate_assertions(
        catalog,
        [
            FactAssertion(
                "doc-1",
                ("class.document",),
                "pred.not-real",
                object_id="obj-1",
                object_types=("class.object",),
            )
        ],
    )
    assert any("unknown predicate" in item for item in unknown)
    deprecated = validate_assertions(
        catalog,
        [
            FactAssertion(
                "obj-1",
                ("class.object",),
                "pred.same-as",
                object_id="obj-2",
                object_types=("class.object",),
            )
        ],
    )
    assert any("deprecated" in item for item in deprecated)
    allowed = validate_assertions(
        catalog,
        [
            FactAssertion(
                "obj-1",
                ("class.object",),
                "pred.same-as",
                object_id="obj-2",
                object_types=("class.object",),
            )
        ],
        allow_deprecated=True,
    )
    assert allowed == []


def test_confidence_score_bounds_and_shape() -> None:
    catalog = load_ontology_catalog(ontology_root())
    bad_shape = validate_assertions(
        catalog,
        [
            FactAssertion(
                "fact-1",
                ("class.fact",),
                "pred.confidence-score",
                object_id="obj-1",
                object_types=("class.object",),
            )
        ],
    )
    assert bad_shape
    out_of_range = validate_assertions(
        catalog,
        [
            FactAssertion(
                "fact-1",
                ("class.fact",),
                "pred.confidence-score",
                literal_value="1.5",
                literal_datatype=_XSD_DECIMAL,
            )
        ],
    )
    assert any("out of range" in item for item in out_of_range)
    ok = validate_assertions(
        catalog,
        [
            FactAssertion(
                "fact-1",
                ("class.fact",),
                "pred.confidence-score",
                literal_value="0.8",
                literal_datatype=_XSD_DECIMAL,
            )
        ],
    )
    assert ok == []


def test_missing_object_and_literal_is_rejected() -> None:
    catalog = load_ontology_catalog(ontology_root())
    findings = validate_assertions(
        catalog,
        [FactAssertion("doc-1", ("class.document",), "pred.mentions")],
    )
    assert any("exactly one" in item for item in findings)
