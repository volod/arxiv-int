"""Project-root discovery without machine-specific paths."""

from pathlib import Path

from arxiv_int.runtime.project_root import ascend_to_root

ROOT_MARKERS = ("pyproject.toml", "AGENTS.md")


def discover_project_root(start: Path | None = None) -> Path:
    """Find the nearest ancestor carrying the project markers."""
    candidate = (start or Path.cwd()).resolve()
    found = ascend_to_root(candidate, ROOT_MARKERS)
    if found is not None:
        return found
    markers = ", ".join(ROOT_MARKERS)
    raise FileNotFoundError(f"no project root containing {markers} above {candidate}")
