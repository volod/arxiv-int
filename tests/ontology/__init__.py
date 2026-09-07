"""Shared ontology test helpers."""

from pathlib import Path

from arxiv_int.quality.project_root import discover_project_root


def ontology_root() -> Path:
    return discover_project_root(Path(__file__)) / "ontology"


def project_root() -> Path:
    return discover_project_root(Path(__file__))
