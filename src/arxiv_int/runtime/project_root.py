"""One checkout-root discovery shared by every runtime entry point."""

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

RUNTIME_MARKERS = ("pyproject.toml",)
ROOT_VARIABLE = "PROJECT_ROOT"


class ProjectRootError(ValueError):
    """A project root cannot be identified or is not a checkout."""


def ascend_to_root(start: Path, markers: Sequence[str]) -> Path | None:
    """Return the nearest ancestor of ``start`` that carries every marker file."""
    candidate = start.resolve()
    for directory in (candidate, *candidate.parents):
        if all((directory / marker).is_file() for marker in markers):
            return directory
    return None


def _declared_root(value: str, source: str) -> Path:
    candidate = Path(value).expanduser().resolve()
    if all((candidate / marker).is_file() for marker in RUNTIME_MARKERS):
        return candidate
    raise ProjectRootError(f"{source} is not a checkout: {candidate}")


def find_project_root(
    explicit: Path | None = None, environment: Mapping[str, str] | None = None
) -> Path:
    """Resolve the checkout an entry point configures: option, PROJECT_ROOT, module, directory."""
    if explicit is not None:
        return _declared_root(str(explicit), "project root")
    declared = (os.environ if environment is None else environment).get(ROOT_VARIABLE, "").strip()
    if declared:
        return _declared_root(declared, ROOT_VARIABLE)
    for start in (Path(__file__).resolve().parent, Path.cwd()):
        found = ascend_to_root(start, RUNTIME_MARKERS)
        if found is not None:
            return found
    raise ProjectRootError(
        f"cannot find a checkout above this module or {Path.cwd()}; set {ROOT_VARIABLE}"
    )
