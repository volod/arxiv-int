"""Product contract registry lint and loader tests."""

from pathlib import Path

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("jsonschema")

from arxiv_int.contracts.canonical import load_canonical_model
from arxiv_int.contracts.integrity import validate_registry_integrity
from arxiv_int.contracts.lint import contracts_root_for, lint_contracts
from arxiv_int.contracts.loaders import load_mapping_document, load_odcs_document
from arxiv_int.contracts.registry import FileRegistry
from arxiv_int.contracts.schema_lint import validate_dataset_files
from arxiv_int.quality.project_root import discover_project_root


def _contracts_root() -> Path:
    return discover_project_root(Path(__file__)) / "contracts"


def test_product_odcs_matches_official_json_schema() -> None:
    findings = validate_dataset_files(_contracts_root())
    assert findings == []


def test_product_registry_integrity_is_complete() -> None:
    findings = validate_registry_integrity(_contracts_root())
    assert findings == []


def test_product_registry_loads_and_verifies_fingerprints() -> None:
    registry = FileRegistry(_contracts_root())
    assert "documents" in registry.contract_ids()
    assert len(registry.contract_ids()) >= 14
    for contract_id in registry.contract_ids():
        registry.verify_semantic_fingerprint(contract_id)


def test_canonical_model_loads_x_arxiv_int_bindings() -> None:
    model = load_canonical_model(_contracts_root() / "canonical")
    assert "document" in model.entities()
    assert model.required_bindings("document")
    assert model.has_term("urn:arxiv-int:term:document-id")


def test_loaders_preserve_unknown_metadata() -> None:
    odcs = FileRegistry(_contracts_root()).load_odcs("documents")
    odcs["unexpectedTopLevel"] = {"keep": True}
    loaded = load_odcs_document(odcs)
    assert loaded.model_extra is not None
    assert loaded.model_extra["unexpectedTopLevel"] == {"keep": True}

    mapping = FileRegistry(_contracts_root()).load_mapping("documents")
    mapping["fieldMappings"][0]["reviewerNote"] = "retain"
    mapped = load_mapping_document(mapping)
    assert mapped.fieldMappings[0]["reviewerNote"] == "retain"


def test_lint_contracts_schema_and_integrity_without_datacontract() -> None:
    report = lint_contracts(
        contracts_root_for(discover_project_root(Path(__file__))),
        run_datacontract=False,
    )
    assert report.ok
    assert report.checked_datasets >= 14
    assert report.datacontract_ran is False
