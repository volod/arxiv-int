"""Assemble an isolated working dbt project that consumes generated sources."""

import shutil
from pathlib import Path

from arxiv_int.transformations.paths import (
    authored_project_dir,
    generated_sources_path,
    profiles_dir,
    working_project_dir,
)

_IGNORE = shutil.ignore_patterns("target", "dbt_packages", "logs", "__pycache__")


class ProjectAssemblyError(RuntimeError):
    """Raised when the committed dbt project or generated sources are missing."""


def assemble_working_project(project_root: Path, artifact_dir: Path) -> Path:
    """Copy authored models and inject generated source YAML into the run dir."""
    source = authored_project_dir(project_root)
    if not (source / "dbt_project.yml").is_file():
        raise ProjectAssemblyError(f"dbt project is missing at {source}")
    generated = generated_sources_path(project_root)
    if not generated.is_file():
        raise ProjectAssemblyError(f"generated dbt sources are missing at {generated}")
    destination = working_project_dir(artifact_dir)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=_IGNORE)
    (destination / "models" / "_generated_sources.yml").write_bytes(generated.read_bytes())
    _copy_profiles(source, artifact_dir)
    return destination


def _copy_profiles(source: Path, artifact_dir: Path) -> None:
    profiles = source / "profiles.yml"
    if not profiles.is_file():
        raise ProjectAssemblyError(f"dbt profiles template is missing at {profiles}")
    target = profiles_dir(artifact_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "profiles.yml").write_text(profiles.read_text(encoding="utf-8"), encoding="utf-8")
