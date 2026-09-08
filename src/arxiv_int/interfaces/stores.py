"""Seams for the normalized dataset lake and the canonical relational store."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from arxiv_int.interfaces.tokens import freeze_str_mapping, require_token


@dataclass(frozen=True, slots=True)
class DatasetRef:
    """One logical dataset partition bound to an output generation."""

    dataset: str
    contract_version: str
    generation_id: str
    partition: Mapping[str, str]

    def __post_init__(self) -> None:
        require_token(self.dataset, "dataset")
        require_token(self.contract_version, "contract_version")
        require_token(self.generation_id, "generation_id")
        object.__setattr__(self, "partition", freeze_str_mapping(self.partition))

    def logical_partition(self) -> tuple[str, str, tuple[tuple[str, str], ...]]:
        """Return identity of the partition ignoring generation."""
        items = tuple(sorted(self.partition.items()))
        return (self.dataset, self.contract_version, items)


@dataclass(frozen=True, slots=True)
class ValidationResultRef:
    """Pointer to one dataset quality run without importing Pandera."""

    contract_id: str
    generation_id: str
    catalog_fingerprint: str
    status: str
    publishable: bool

    def __post_init__(self) -> None:
        require_token(self.contract_id, "contract_id")
        require_token(self.generation_id, "generation_id")
        require_token(self.status, "status")
        if self.publishable and self.status in {"fail", "not-run"}:
            raise ValueError(f"status {self.status!r} cannot be publishable")


@dataclass(frozen=True, slots=True)
class TransformationRunRef:
    """Pointer to one dbt invocation without importing dbt."""

    run_id: str
    generation_id: str
    command: str
    status: str
    input_fingerprint: str
    model_fingerprint: str
    activatable: bool

    def __post_init__(self) -> None:
        require_token(self.run_id, "run_id")
        require_token(self.generation_id, "generation_id")
        require_token(self.command, "command")
        require_token(self.status, "status")
        if self.activatable and self.status != "ok":
            raise ValueError("only a successful transformation run can be activatable")


@dataclass(frozen=True, slots=True)
class StoreStatus:
    """Reachability report a preflight or readiness check can render directly."""

    available: bool
    detail: str


@runtime_checkable
class ArtifactStore(Protocol):
    """Locate and publish normalized dataset generations under the results root."""

    feature: str

    def locate(self, ref: DatasetRef) -> Path:
        """Return the published location of one dataset partition generation."""

    def publish(self, ref: DatasetRef, staged: Path) -> Path:
        """Activate a validated staged partition and return its published location."""


@runtime_checkable
class CanonicalStore(Protocol):
    """Access to the canonical relational schemas that hold committed state."""

    feature: str

    def status(self) -> StoreStatus:
        """Report whether the store is reachable and usable."""

    def schemas(self) -> Sequence[str]:
        """Return the canonical schema names the store currently exposes."""
