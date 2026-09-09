"""Packaged resource resolution and checkout overlays."""

from pathlib import Path

from arxiv_int.resources.paths import (
    configs_output_root,
    configs_root,
    contracts_root,
    dbt_project_root,
    ontology_root,
    output_root,
    resource_root,
)


def test_packaged_asset_trees_exist() -> None:
    root = resource_root()
    assert (root / "contracts" / "registry.yaml").is_file()
    assert (root / "ontology" / "manifest.yaml").is_file()
    assert (root / "configs" / "pipeline" / "investigation.json").is_file()
    assert (root / "dbt" / "dbt_project.yml").is_file()
    assert contracts_root() == (root / "contracts").resolve()
    assert ontology_root() == (root / "ontology").resolve()
    assert configs_root() == (root / "configs").resolve()
    assert dbt_project_root() == (root / "dbt").resolve()


def test_project_root_overlay_wins(tmp_path: Path) -> None:
    overlay = tmp_path / "contracts"
    overlay.mkdir()
    (overlay / "marker").write_text("ok", encoding="utf-8")
    assert contracts_root(tmp_path) == overlay.resolve()
    assert contracts_root() != overlay.resolve()


def test_output_root_keeps_disposable_trees_off_packaged_assets(tmp_path: Path) -> None:
    written = output_root(tmp_path, "configs")
    assert written == tmp_path / "configs"
    assert configs_output_root(tmp_path) == tmp_path / "configs"
    assert configs_root(tmp_path) == (resource_root() / "configs").resolve()
