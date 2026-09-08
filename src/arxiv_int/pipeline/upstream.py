"""Resolve assumed upstream by the frozen run's transitive identity."""

from collections.abc import Mapping

from arxiv_int.pipeline.context import RunContext
from arxiv_int.pipeline.control.fingerprints import reuse_key
from arxiv_int.pipeline.errors import StaleUpstreamError
from arxiv_int.pipeline.execute import stage_identity, try_reuse
from arxiv_int.pipeline.registry import StageRegistry
from arxiv_int.pipeline.reuse_index import ReuseEntry


def resolve_upstream(
    context: RunContext,
    names: tuple[str, ...],
    registry: StageRegistry,
    index: Mapping[str, ReuseEntry],
) -> dict[str, str]:
    """Refuse missing, partial, stale or unrelated ancestors at an atomic boundary."""
    keys: dict[str, str] = {}

    def resolve(name: str) -> str:
        if name in keys:
            return keys[name]
        spec = registry.get(name)
        upstream = tuple(resolve(dependency) for dependency in spec.depends_on)
        key = reuse_key(stage_identity(spec, context, upstream))
        if try_reuse(index.get(key), force=False) is None:
            raise StaleUpstreamError(f"stale or missing upstream stage {name}")
        keys[name] = key
        return key

    for name in names:
        resolve(name)
    return keys
