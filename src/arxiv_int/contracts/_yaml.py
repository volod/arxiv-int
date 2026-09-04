"""Typed YAML loading for contract documents.

Adapted from ``fl_op.contracts.odcs_loader`` and registry loading in
https://github.com/volod/fl-op at revision
1f452ecaeded92c6bbbd4a86de9ded1ea7444e60, under the MIT License.
"""

import pathlib
from typing import Any, cast

import yaml


def load_mapping(path: pathlib.Path) -> dict[str, Any]:
    """Load one YAML mapping or fail with its path in the error."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"Contract document is not a mapping: {path}")
    return cast(dict[str, Any], document)
