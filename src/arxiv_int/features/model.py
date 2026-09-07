"""Typed description of one optional install group and its declared distributions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Requirement:
    """One declared distribution, the import name that proves it, and its licence."""

    distribution: str
    module: str
    license_id: str
    purpose: str


@dataclass(frozen=True, slots=True)
class FeatureGroup:
    """One optional dependency group that keeps a heavy stack out of the core install."""

    name: str
    summary: str
    owner: str
    requirements: tuple[Requirement, ...] = ()
    system_dependencies: tuple[str, ...] = ()

    @property
    def reserved(self) -> bool:
        """Report whether the group is declared but not populated by a capability yet."""
        return not self.requirements

    @property
    def modules(self) -> tuple[str, ...]:
        """Return the import names that prove the group is installed."""
        return tuple(requirement.module for requirement in self.requirements)


@dataclass(frozen=True, slots=True)
class StageFeatureSet:
    """Required and conditional feature groups one pipeline stage may activate."""

    required: tuple[str, ...] = ()
    conditional: tuple[str, ...] = ()

    def all_names(self) -> tuple[str, ...]:
        """Return unique group names with required names first, then conditional."""
        seen = set(self.required)
        extra = tuple(name for name in self.conditional if name not in seen)
        return (*self.required, *extra)

    def includes(self, name: str) -> bool:
        """Report whether the stage lists the group as required or conditional."""
        return name in self.required or name in self.conditional
