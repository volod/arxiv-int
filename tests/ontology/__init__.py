"""Shared ontology test helpers."""

from pathlib import Path

from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.resources.paths import ontology_root

__all__ = ["ontology_root", "project_root"]


def project_root() -> Path:
    return discover_project_root(Path(__file__))
