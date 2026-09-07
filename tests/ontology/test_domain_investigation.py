"""Domain investigation fixture and rule tests."""

import json
from pathlib import Path

import pytest

pytest.importorskip("rdflib")
pytest.importorskip("pyshacl")

from arxiv_int.ontology.domain_rules import (
    AllocationRow,
    ArtifactRegistryRow,
    BomLine,
    supply_stage_findings,
    validate_anchor_kind,
    validate_direction,
    validate_domain_assertions,
)
from arxiv_int.ontology.load import load_ontology_catalog
from arxiv_int.ontology.shacl import validate_assertions_with_shacl
from arxiv_int.ontology.validate import FactAssertion
from tests.ontology import ontology_root

_FIX = Path(__file__).parent / "domain_fixtures"
_OBJ = "class.object"
_PERSON = "class.natural-person"
_LEGAL = "class.legal-entity"
_PAY = "class.payment"
_INV = "class.invoice"
_SHIP = "class.shipment"


def _load(name: str) -> dict:
    return json.loads((_FIX / f"{name}.json").read_text(encoding="utf-8"))


def _assertions(payload: dict) -> tuple[FactAssertion, ...]:
    return tuple(FactAssertion(**item) for item in payload.get("assertions", []))


def _bom(payload: dict) -> tuple[BomLine, ...]:
    return tuple(BomLine(**item) for item in payload.get("bom_lines", []))


def _alloc(payload: dict) -> tuple[AllocationRow, ...]:
    return tuple(AllocationRow(**item) for item in payload.get("allocations", []))


def _registry(payload: dict) -> tuple[ArtifactRegistryRow, ...]:
    return tuple(ArtifactRegistryRow(**item) for item in payload.get("registry", []))


@pytest.mark.parametrize(
    ("case_name", "expect_ok"),
    [
        ("positive-part-of", True),
        ("negative-reference-as-part-of", False),
        ("negative-owns-candidate-as-explicit", False),
        ("negative-amount-date-as-payment", False),
        ("negative-same-name-as-identity", False),
        ("negative-bom-cycle", False),
        ("negative-bom-alternatives-summed", False),
        ("negative-invoice-claims-delivery", False),
        ("negative-currency-mismatch", False),
        ("positive-registry-empty", True),
        ("negative-registry-failed-without-reason", False),
        ("positive-employee-of", True),
    ],
)
def test_domain_rule_fixtures(case_name: str, expect_ok: bool) -> None:
    catalog = load_ontology_catalog(ontology_root())
    payload = _load(case_name)
    findings = validate_domain_assertions(
        catalog,
        _assertions(payload),
        bom_lines=_bom(payload),
        allocations=_alloc(payload),
        registry_rows=_registry(payload),
    )
    if payload.get("supply_stage"):
        findings.extend(
            supply_stage_findings(
                payload["supply_stage"],
                claims_delivery=bool(payload.get("claims_delivery")),
            )
        )
    if payload.get("anchor_kind"):
        findings.extend(validate_anchor_kind(payload["anchor_kind"]))
    if payload.get("direction"):
        findings.extend(validate_direction(payload["direction"]))
    assert (not findings) is expect_ok, findings


@pytest.mark.parametrize(
    ("case_name", "expect_ok"),
    [
        ("positive-part-of", True),
        ("negative-reference-as-part-of", False),
        ("negative-owns-candidate-as-explicit", False),
        ("negative-amount-date-as-payment", False),
        ("positive-employee-of", True),
    ],
)
def test_domain_shacl_agrees_on_structural_cases(case_name: str, expect_ok: bool) -> None:
    root = ontology_root()
    catalog = load_ontology_catalog(root)
    assertions = _assertions(_load(case_name))
    app = validate_domain_assertions(catalog, assertions)
    shacl_ok, _ = validate_assertions_with_shacl(assertions, ontology_root=root, catalog=catalog)
    assert (not app) is expect_ok
    assert shacl_ok is expect_ok


def test_anchor_and_direction_enums() -> None:
    assert validate_anchor_kind("table") == []
    assert validate_anchor_kind("worksheet")
    assert validate_direction("forward") == []
    assert validate_direction("sideways")
