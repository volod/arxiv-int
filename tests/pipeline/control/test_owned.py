"""Owned asset provenance, portability, immutability, and fail-closed boundaries."""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.pipeline.control import owned
from arxiv_int.pipeline.control.asset_hashes import file_hashes
from arxiv_int.pipeline.control.fingerprints import OWNED_FINGERPRINT_FIELDS
from arxiv_int.pipeline.control.owned import owned_fingerprints
from arxiv_int.pipeline.run.fixtures import fixture_registry
from arxiv_int.resources.paths import contracts_root


def test_all_fields_are_sourced_and_empty_sets_are_stage_specific(tmp_path: Path) -> None:
    registry, _ = fixture_registry()
    alpha = owned_fingerprints(registry.get("alpha"), tmp_path, "frozen-config")
    beta = owned_fingerprints(registry.get("beta"), tmp_path, "frozen-config")
    assert set(alpha) == set(OWNED_FINGERPRINT_FIELDS)
    assert (
        alpha["configuration_fingerprint"] == beta["configuration_fingerprint"] == "frozen-config"
    )
    for field in set(alpha) - {"configuration_fingerprint"}:
        assert len(alpha[field]) == 64
        assert alpha[field] != beta[field]
    assert len(set(alpha.values())) == len(alpha)


def test_maps_are_frozen_and_runner_rebinding_preserves_declarations(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    tools = {"tool-a": "1", "tool-b": "2"}
    spec = replace(registry.get("beta"), tools=tools, contracts=("documents",))
    before = owned_fingerprints(spec, tmp_path, "config")
    tools["tool-a"] = "changed"
    assert owned_fingerprints(spec, tmp_path, "config") == before
    reordered = replace(spec, tools={"tool-b": "2", "tool-a": "1"})
    assert owned_fingerprints(reordered, tmp_path, "config") == before
    bound = type(registry)((registry.get("alpha"), spec)).with_runner("beta", runners["beta"])
    assert bound.get("beta").tools == spec.tools
    assert bound.get("beta").contracts == spec.contracts


def test_assets_are_portable_and_documentation_is_unowned(tmp_path: Path) -> None:
    registry, _ = fixture_registry(validators=("documents",))
    spec = registry.get("beta")
    original = owned_fingerprints(spec, tmp_path, "config")
    shutil.copytree(contracts_root(), tmp_path / "contracts")
    assert owned_fingerprints(spec, tmp_path, "config") == original
    (tmp_path / "README.md").write_text("Unrelated documentation edit.\n")
    (tmp_path / "contracts/datasets/chunks.odcs.yaml").write_text("unrelated contract change")
    assert owned_fingerprints(spec, tmp_path, "config") == original
    schema = tmp_path / "contracts/generated/jsonschema/documents.schema.json"
    schema.write_text(schema.read_text() + "\n")
    changed = owned_fingerprints(spec, tmp_path, "config")
    assert {key for key in original if original[key] != changed[key]} == {"schema_fingerprint"}


def test_owned_code_edit_does_not_change_another_stage(tmp_path: Path, monkeypatch) -> None:
    registry, _ = fixture_registry()
    for reference in owned._SHARED_CODE:
        source = owned.PACKAGE_ROOT / reference
        target = tmp_path / reference
        if source.is_dir():
            shutil.copytree(source, target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (tmp_path / "worker.py").write_text("VALUE = 1\n")
    monkeypatch.setattr(owned, "PACKAGE_ROOT", tmp_path)
    alpha = registry.get("alpha")
    beta = replace(registry.get("beta"), code_paths=("worker.py",))
    before = owned_fingerprints(beta, tmp_path, "config")
    unrelated = owned_fingerprints(alpha, tmp_path, "config")
    (tmp_path / "worker.py").write_text("VALUE = 2\n")
    assert owned_fingerprints(alpha, tmp_path, "config") == unrelated
    after = owned_fingerprints(beta, tmp_path, "config")
    assert {key for key in before if before[key] != after[key]} == {"code_fingerprint"}


@pytest.mark.parametrize("reference", ("missing.sql", "../outside.sql", "/outside.sql"))
def test_missing_or_escaped_asset_is_refused(tmp_path: Path, reference: str) -> None:
    with pytest.raises(ValueError):
        file_hashes(tmp_path, (reference,))


def test_symlink_escape_and_unknown_contract_are_refused(tmp_path: Path) -> None:
    root = tmp_path / "assets"
    root.mkdir()
    outside = tmp_path / "outside.sql"
    outside.write_text("select 1")
    (root / "model.sql").symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        file_hashes(root, ("model.sql",))
    registry, _ = fixture_registry()
    with pytest.raises(ValueError, match="unknown stage contract"):
        owned_fingerprints(replace(registry.get("alpha"), contracts=("typo",)), tmp_path, "config")


def test_combined_dbt_sources_bind_only_consumed_tables(tmp_path: Path) -> None:
    import json

    from arxiv_int.contracts.catalog._yaml import load_mapping

    registry, _ = fixture_registry()
    spec = replace(
        registry.get("beta"),
        contracts=("documents",),
        dbt_models=("models/staging/stg_documents.sql",),
    )
    shutil.copytree(contracts_root(), tmp_path / "contracts")
    source = tmp_path / "contracts/generated/dbt/sources.yml"
    original = owned_fingerprints(spec, tmp_path, "config")
    data = load_mapping(source)
    tables = {table["name"]: table for item in data["sources"] for table in item["tables"]}
    tables["chunks"]["description"] = "unrelated table edit"
    source.write_text(json.dumps(data))
    assert owned_fingerprints(spec, tmp_path, "config") == original
    tables["documents"]["description"] = "changed consumed source"
    source.write_text(json.dumps(data))
    changed = owned_fingerprints(spec, tmp_path, "config")
    assert {key for key in original if changed[key] != original[key]} == {
        "dbt_input_fingerprint",
        "dbt_rule_fingerprint",
    }
