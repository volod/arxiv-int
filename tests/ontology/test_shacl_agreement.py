"""SHACL and application validation must agree on fixtures."""

from pathlib import Path

import pytest

pytest.importorskip("rdflib")
pytest.importorskip("pyshacl")

from arxiv_int.ontology.load import load_ontology_catalog
from arxiv_int.ontology.shacl import validate_assertions_with_shacl
from arxiv_int.ontology.validate import FactAssertion, validate_assertions
from tests.ontology import ontology_root

_XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
_FIX = Path(__file__).parent / "fixtures"


def _load_case(name: str) -> tuple[FactAssertion, ...]:
    import json

    payload = json.loads((_FIX / f"{name}.json").read_text(encoding="utf-8"))
    return tuple(FactAssertion(**item) for item in payload["assertions"])


@pytest.mark.parametrize(
    ("case_name", "expect_ok"),
    [
        ("positive-mentions", True),
        ("positive-preferred-name", True),
        ("negative-domain", False),
        ("negative-range", False),
        ("negative-disjoint", False),
        ("negative-functional", False),
    ],
)
def test_shacl_and_application_validation_agree(case_name: str, expect_ok: bool) -> None:
    root = ontology_root()
    catalog = load_ontology_catalog(root)
    assertions = _load_case(case_name)
    app_findings = validate_assertions(catalog, assertions)
    shacl_ok, _shacl_findings = validate_assertions_with_shacl(
        assertions, ontology_root=root, catalog=catalog
    )
    assert (not app_findings) is expect_ok
    assert shacl_ok is expect_ok
