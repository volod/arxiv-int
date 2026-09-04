"""Portable dispatch for deterministic contract generators.

Adapted from ``fl_op.contracts.schema_gen`` and ``fl_op.contracts.gen.base`` in
https://github.com/volod/fl-op at revision
1f452ecaeded92c6bbbd4a86de9ded1ea7444e60, under the MIT License.
"""

import pathlib
from typing import Any, Protocol

from arxiv_int.contracts.registry import FileRegistry


class ContractGenerator(Protocol):
    """One focused ODCS-to-artifact generator."""

    def generate(self, odcs_document: dict[str, Any], contract_id: str) -> str:
        """Return deterministic text for one registered contract."""
        ...


def generate_registered(
    registry: FileRegistry,
    contract_id: str,
    generator: ContractGenerator,
    destination: pathlib.Path,
) -> pathlib.Path:
    """Generate one registered contract to an explicit portable path."""
    content = generator.generate(registry.load_odcs(contract_id), contract_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination
