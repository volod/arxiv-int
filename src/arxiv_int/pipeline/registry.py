"""Typed stage specifications and the dependency-aware registry."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from arxiv_int.interfaces.pipeline import StageRunner
from arxiv_int.interfaces.tokens import require_token
from arxiv_int.pipeline.errors import CyclicDependencyError, UnknownStageError
from arxiv_int.pipeline.graph import topological_order


@dataclass(frozen=True, slots=True)
class ResourceEstimate:
    """Declared resource envelope used later by forecast; not a measurement."""

    cpu_seconds: float = 1.0
    ram_bytes: int = 67_108_864
    disk_bytes: int = 1_048_576
    gpu_required: bool = False


@dataclass(frozen=True, slots=True)
class StageSpec:
    """One registry entry: contracts, estimates, validators, and optional runner."""

    name: str
    version: str
    depends_on: tuple[str, ...]
    required_inputs: tuple[str, ...]
    conditional_inputs: tuple[str, ...]
    resource_estimate: ResourceEstimate
    validators: tuple[str, ...]
    dbt_select: tuple[str, ...]
    runner: StageRunner | None
    optional: bool = False

    def __post_init__(self) -> None:
        require_token(self.name, "name")
        require_token(self.version, "version")
        for index, item in enumerate(self.depends_on):
            require_token(item, f"depends_on[{index}]")


class StageRegistry:
    """Immutable map of stage specs with acyclic, resolvable dependencies."""

    def __init__(self, specs: Sequence[StageSpec]) -> None:
        names = [spec.name for spec in specs]
        if len(names) != len(set(names)):
            raise ValueError("stage registry names must be unique")
        self._specs: dict[str, StageSpec] = {spec.name: spec for spec in specs}
        for spec in specs:
            missing = [name for name in spec.depends_on if name not in self._specs]
            if missing:
                listed = ", ".join(missing)
                raise UnknownStageError(
                    f"stage {spec.name!r} depends on unregistered stage(s): {listed}"
                )
        try:
            topological_order(tuple(self._specs), self.dependencies())
        except CyclicDependencyError:
            raise

    def get(self, name: str) -> StageSpec:
        """Return one spec or name the registered stages."""
        try:
            return self._specs[name]
        except KeyError as error:
            known = ", ".join(self.names())
            raise UnknownStageError(
                f"unknown stage {name!r}; registered stages are {known}"
            ) from error

    def names(self) -> tuple[str, ...]:
        """Return registered stage names in declaration order."""
        return tuple(self._specs)

    def specs(self) -> tuple[StageSpec, ...]:
        """Return every spec in declaration order."""
        return tuple(self._specs.values())

    def dependencies(self) -> Mapping[str, tuple[str, ...]]:
        """Return the dependency adjacency list."""
        return {spec.name: spec.depends_on for spec in self._specs.values()}

    def with_runner(self, name: str, runner: StageRunner) -> "StageRegistry":
        """Return a copy that binds one runner without changing other specs."""
        updated: list[StageSpec] = []
        for spec in self._specs.values():
            if spec.name != name:
                updated.append(spec)
                continue
            updated.append(
                StageSpec(
                    spec.name,
                    spec.version,
                    spec.depends_on,
                    spec.required_inputs,
                    spec.conditional_inputs,
                    spec.resource_estimate,
                    spec.validators,
                    spec.dbt_select,
                    runner,
                    spec.optional,
                )
            )
        return StageRegistry(updated)
