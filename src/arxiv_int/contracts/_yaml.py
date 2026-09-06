"""Typed YAML loading for contract documents."""

import pathlib
from typing import Any, cast

import yaml


def load_mapping(path: pathlib.Path) -> dict[str, Any]:
    """Load one YAML mapping or fail with its path in the error."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"Contract document is not a mapping: {path}")
    return cast(dict[str, Any], document)
