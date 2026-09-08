"""Portable dispatch for one focused contract generator."""

import pathlib
from typing import Any, Protocol

from arxiv_int.contracts.catalog.registry import FileRegistry


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
