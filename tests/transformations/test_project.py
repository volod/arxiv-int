from pathlib import Path

import pytest

from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.transformations.project import ProjectAssemblyError, assemble_working_project


def test_assemble_working_project_injects_generated_sources(tmp_path: Path) -> None:
    root = discover_project_root(Path(__file__))
    destination = assemble_working_project(root, tmp_path / "run")
    assert (destination / "dbt_project.yml").is_file()
    generated = destination / "models" / "_generated_sources.yml"
    assert generated.is_file()
    text = generated.read_text(encoding="utf-8")
    assert "name: corpus" in text
    assert "name: documents" in text
    profiles = (tmp_path / "run" / "profiles" / "profiles.yml").read_text(encoding="utf-8")
    assert "env_var('ARXIV_INT_DBT_PASSWORD')" in profiles
    assert "super-secret" not in profiles


def test_assemble_working_project_fails_when_authored_project_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "arxiv_int.transformations.project.authored_project_dir",
        lambda project_root: tmp_path / "missing-dbt",
    )
    with pytest.raises(ProjectAssemblyError, match="dbt project is missing"):
        assemble_working_project(tmp_path, tmp_path / "run")
