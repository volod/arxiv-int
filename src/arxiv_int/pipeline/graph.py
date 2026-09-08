"""Dependency-closure and range planning over a stage registry."""

from collections.abc import Mapping
from dataclasses import dataclass

from arxiv_int.interfaces.tokens import require_token
from arxiv_int.pipeline.errors import CyclicDependencyError, InvalidRangeError, UnknownStageError


@dataclass(frozen=True, slots=True)
class StagePlan:
    """Stages to execute, upstream artifacts that must already validate, and skips."""

    execute: tuple[str, ...]
    assumed_upstream: tuple[str, ...]
    not_selected: tuple[str, ...]


def ancestors(name: str, dependencies: Mapping[str, tuple[str, ...]]) -> frozenset[str]:
    """Return every recursive dependency of ``name``, excluding ``name`` itself."""
    _require_known(name, dependencies)
    seen: set[str] = set()
    stack = list(dependencies[name])
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        _require_known(current, dependencies)
        seen.add(current)
        stack.extend(dependencies[current])
    return frozenset(seen)


def descendants(name: str, dependencies: Mapping[str, tuple[str, ...]]) -> frozenset[str]:
    """Return every stage that transitively consumes ``name``, excluding ``name``."""
    _require_known(name, dependencies)
    children: dict[str, list[str]] = {item: [] for item in dependencies}
    for consumer, deps in dependencies.items():
        for producer in deps:
            children.setdefault(producer, []).append(consumer)
    seen: set[str] = set()
    stack = list(children.get(name, ()))
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(children.get(current, ()))
    return frozenset(seen)


def topological_order(
    names: tuple[str, ...], dependencies: Mapping[str, tuple[str, ...]]
) -> tuple[str, ...]:
    """Return ``names`` in a stable topological order, or raise on a cycle."""
    selected = set(names)
    remaining = {
        name: tuple(dep for dep in dependencies[name] if dep in selected) for name in names
    }
    emitted: list[str] = []
    while remaining:
        current = _next_ready(names, remaining)
        emitted.append(current)
        remaining = _drop_emitted(remaining, current)
    return tuple(emitted)


def _next_ready(declaration: tuple[str, ...], remaining: Mapping[str, tuple[str, ...]]) -> str:
    ready = [name for name in declaration if name in remaining and not remaining[name]]
    if not ready:
        cyclic = ", ".join(sorted(remaining))
        raise CyclicDependencyError(f"cyclic stage dependencies among: {cyclic}")
    return ready[0]


def _drop_emitted(
    remaining: Mapping[str, tuple[str, ...]], current: str
) -> dict[str, tuple[str, ...]]:
    return {
        name: tuple(dep for dep in deps if dep != current)
        for name, deps in remaining.items()
        if name != current
    }


def select_plan(
    dependencies: Mapping[str, tuple[str, ...]],
    *,
    profile_stages: tuple[str, ...],
    optional_stages: frozenset[str],
    from_stage: str | None = None,
    to_stage: str | None = None,
) -> StagePlan:
    """Resolve a ``--from`` / ``--to`` closure against a profile's required stages."""
    for name in profile_stages:
        _require_known(name, dependencies)
    if from_stage is not None:
        _require_known(from_stage, dependencies)
    if to_stage is not None:
        _require_known(to_stage, dependencies)
    required = frozenset(name for name in profile_stages if name not in optional_stages)
    execute_set, assumed = _range_sets(
        dependencies, required, optional_stages, from_stage, to_stage
    )
    execute = topological_order(
        tuple(name for name in dependencies if name in execute_set), dependencies
    )
    assumed_order = topological_order(
        tuple(name for name in dependencies if name in assumed), dependencies
    )
    skipped = tuple(
        name
        for name in dependencies
        if name in optional_stages and name not in execute_set and name not in assumed
    )
    return StagePlan(execute, assumed_order, skipped)


def _range_sets(
    dependencies: Mapping[str, tuple[str, ...]],
    required: frozenset[str],
    optional_stages: frozenset[str],
    from_stage: str | None,
    to_stage: str | None,
) -> tuple[set[str], set[str]]:
    to_closure = (
        set(required) if to_stage is None else set(ancestors(to_stage, dependencies)) | {to_stage}
    )
    if from_stage is None:
        return to_closure if to_stage is not None else set(required), set()
    if from_stage not in to_closure and to_stage is not None:
        raise InvalidRangeError(
            f"stage range --from {from_stage} --to {to_stage} is not a connected closure"
        )
    from_closure = {from_stage} | set(descendants(from_stage, dependencies))
    if to_stage is None and from_stage not in optional_stages:
        from_closure &= set(required) | {from_stage}
    execute_set = from_closure & to_closure if to_stage is not None else from_closure
    if not execute_set:
        raise InvalidRangeError(
            f"stage range --from {from_stage} --to {to_stage} is not a connected closure"
        )
    assumed = set(ancestors(from_stage, dependencies)) - execute_set
    return execute_set, assumed


def _require_known(name: str, dependencies: Mapping[str, tuple[str, ...]]) -> None:
    require_token(name, "stage")
    if name not in dependencies:
        known = ", ".join(dependencies)
        raise UnknownStageError(f"unknown stage {name!r}; registered stages are {known}")
