"""Seams for the normalized dataset lake and the canonical relational store."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class DatasetRef:
    """One logical dataset partition, independent of the checkout location."""

    dataset: str
    contract_version: str
    partition: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class StoreStatus:
    """Reachability report a preflight or doctor check can render directly."""

    available: bool
    detail: str


@runtime_checkable
class ArtifactStore(Protocol):
    """Locate and publish normalized dataset generations under the results root."""

    feature: str

    def locate(self, ref: DatasetRef) -> Path:
        """Return the published location of one dataset partition."""

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
