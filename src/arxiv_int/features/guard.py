"""Actionable guards for the optional imports declared by the feature catalog."""

from importlib import import_module
from importlib.util import find_spec
from types import ModuleType

from arxiv_int.features.catalog import providing_group
from arxiv_int.features.model import FeatureGroup
from arxiv_int.metadata import DISTRIBUTION_NAME

INSTALLED = "installed"
MISSING = "missing"
RESERVED = "reserved"


def install_command(group: FeatureGroup) -> str:
    """Return the command that installs one populated feature group."""
    return f"uv pip install '{DISTRIBUTION_NAME}[{group.name}]'"


class MissingFeatureError(ImportError):
    """Raised when code needs an optional group that the environment does not carry."""

    def __init__(self, group: FeatureGroup, module: str) -> None:
        super().__init__(
            f"'{module}' is not installed; it belongs to the '{group.name}' feature group "
            f"({group.summary}). Install it with: {install_command(group)}"
        )
        self.group = group.name
        self.module = module


def module_available(module: str) -> bool:
    """Report whether one module can be imported without importing it."""
    try:
        return find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def group_status(group: FeatureGroup) -> str:
    """Return `reserved`, `installed`, or `missing` for one declared group."""
    if group.reserved:
        return RESERVED
    return INSTALLED if all(module_available(name) for name in group.modules) else MISSING


def require_module(module: str) -> ModuleType:
    """Import one declared optional module or explain how to install its group."""
    group = providing_group(module)
    try:
        return import_module(module)
    except ImportError as error:
        raise MissingFeatureError(group, module) from error
