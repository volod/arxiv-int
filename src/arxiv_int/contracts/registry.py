"""File-backed registry for ODCS contracts and canonical mappings."""

import pathlib
from dataclasses import dataclass
from typing import Any

from arxiv_int.contracts._yaml import load_mapping
from arxiv_int.contracts.fingerprint import semantic_metadata_hash
from arxiv_int.contracts.paths import resolve_rooted_reference


class MetadataDriftError(RuntimeError):
    """Raised when reviewed and computed semantic fingerprints differ."""


@dataclass(frozen=True)
class ContractEntry:
    """Paths and reviewed identity for one registered contract."""

    contract_id: str
    odcs_ref: str
    mapping_ref: str | None = None
    canonical_entity: str | None = None
    stored_semantic_hash: str | None = None


class FileRegistry:
    """Read a portable registry whose references stay below its root."""

    def __init__(self, root: pathlib.Path) -> None:
        self.root = root.resolve()
        index = load_mapping(self.root / "registry.yaml")
        raw_entries = index.get("contracts")
        if not isinstance(raw_entries, dict):
            raise ValueError("Registry must contain a 'contracts' mapping")
        self._entries = {
            str(contract_id): self._entry(str(contract_id), spec)
            for contract_id, spec in raw_entries.items()
        }

    @staticmethod
    def _entry(contract_id: str, spec: Any) -> ContractEntry:
        if not isinstance(spec, dict) or not spec.get("odcs"):
            raise ValueError(f"Registry contract '{contract_id}' has no ODCS reference")
        fingerprints = spec.get("fingerprints") or {}
        return ContractEntry(
            contract_id=contract_id,
            odcs_ref=str(spec["odcs"]),
            mapping_ref=str(spec["mapping"]) if spec.get("mapping") else None,
            canonical_entity=spec.get("canonicalEntity"),
            stored_semantic_hash=fingerprints.get("semanticMetadataHash")
            or fingerprints.get("optimizationMetadataHash"),
        )

    def contract_ids(self) -> tuple[str, ...]:
        return tuple(self._entries)

    def get_entry(self, contract_id: str) -> ContractEntry:
        try:
            return self._entries[contract_id]
        except KeyError as error:
            raise KeyError(f"Unknown contract id: {contract_id}") from error

    def _path(self, reference: str, *, label: str) -> pathlib.Path:
        return resolve_rooted_reference(self.root, reference, label=label)

    def load_odcs(self, contract_id: str) -> dict[str, Any]:
        entry = self.get_entry(contract_id)
        return load_mapping(
            self._path(entry.odcs_ref, label=f"Registry ODCS reference for '{contract_id}'")
        )

    def load_mapping(self, contract_id: str) -> dict[str, Any]:
        reference = self.get_entry(contract_id).mapping_ref
        if reference is None:
            raise KeyError(f"Contract has no canonical mapping: {contract_id}")
        return load_mapping(
            self._path(reference, label=f"Registry mapping reference for '{contract_id}'")
        )

    def semantic_fingerprint(self, contract_id: str) -> str:
        return semantic_metadata_hash(self.load_mapping(contract_id))

    def verify_semantic_fingerprint(self, contract_id: str) -> str:
        entry = self.get_entry(contract_id)
        computed = self.semantic_fingerprint(contract_id)
        if entry.stored_semantic_hash and entry.stored_semantic_hash != computed:
            raise MetadataDriftError(
                f"semanticMetadataHash changed for '{contract_id}': "
                f"stored {entry.stored_semantic_hash}, computed {computed}"
            )
        return computed
