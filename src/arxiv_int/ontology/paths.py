"""Resolve packaged ontology assets, with optional checkout overlays."""

import importlib
from pathlib import Path

from arxiv_int.resources.paths import ontology_root


def ontology_root_for(project_root: Path | None = None) -> Path:
    """Return packaged ``ontology/`` or an overlay under ``project_root``."""
    return ontology_root(project_root)


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
