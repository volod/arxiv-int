"""Resolve the repository ontology root."""

import importlib
from pathlib import Path

from arxiv_int.runtime.project_root import find_project_root


def ontology_root_for(project_root: Path | None = None) -> Path:
    """Return ``<project>/ontology`` for the declared project root."""
    root = find_project_root(project_root) if project_root is not None else find_project_root()
    return (root / "ontology").resolve()


def require_graph_dependencies() -> None:
    """Fail closed when the optional graph extra is not installed."""
    try:
        importlib.import_module("rdflib")
        importlib.import_module("pyshacl")
    except ImportError as error:
        raise RuntimeError(
            "ontology validation requires the graph extra "
            "(uv sync --extra graph); missing dependency: "
            f"{error}"
        ) from error
