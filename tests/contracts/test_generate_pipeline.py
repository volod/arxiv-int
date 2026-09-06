"""Generation pipeline, drift, provenance, and golden fingerprint tests."""

import json
from pathlib import Path

import pytest

from arxiv_int.contracts.datacontract_lint import datacontract_command
from arxiv_int.contracts.generate import check_generation_drift
from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.contracts.odcs_ext import project_extension
from arxiv_int.contracts.registry import FileRegistry
from arxiv_int.quality.project_root import discover_project_root


def _contracts_root() -> Path:
    return discover_project_root(Path(__file__)) / "contracts"


def _generated_root() -> Path:
    return _contracts_root() / "generated"


def _golden_fingerprints() -> dict[str, str]:
    path = Path(__file__).parent / "golden" / "artifact-fingerprints.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_generated_tree_matches_golden_fingerprints() -> None:
    root = _generated_root()
    assert (root / "manifest.json").is_file()
    for relative, digest in _golden_fingerprints().items():
        text = (root / relative).read_text(encoding="utf-8")
        assert sha256_text(text) == digest, relative


def test_provenance_retains_source_contract_metadata() -> None:
    registry = FileRegistry(_contracts_root())
    for contract_id in registry.contract_ids():
        odcs = registry.load_odcs(contract_id)
        extension = project_extension(odcs.get("customProperties")) or {}
        field_names = {
            str(prop["name"])
            for schema in odcs.get("schema") or []
            if isinstance(schema, dict)
            for prop in schema.get("properties") or []
            if isinstance(prop, dict) and "name" in prop
        }
        avro = json.loads((_generated_root() / "avro" / f"{contract_id}.avsc").read_text())
        avro_fields = {field["name"] for field in avro["fields"]}
        assert field_names <= avro_fields

        provenance = json.loads(
            (_generated_root() / "provenance" / f"{contract_id}.json").read_text()
        )
        assert provenance["contractId"] == contract_id
        assert provenance["odcsId"] == odcs.get("id")
        assert provenance["odcsVersion"] == odcs.get("version")
        for key in extension:
            assert key in provenance["customExtensionKeys"]


@pytest.mark.skipif(datacontract_command() is None, reason="Data Contract CLI unavailable")
def test_generation_drift_check_passes_for_committed_tree() -> None:
    assert check_generation_drift(_contracts_root()) == []
