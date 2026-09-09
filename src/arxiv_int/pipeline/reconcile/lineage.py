"""Compare dbt source/ref edges with artifact lineage."""

from collections.abc import Mapping, Sequence


def dbt_edges(parent_map: Mapping[str, Sequence[str]]) -> frozenset[tuple[str, str]]:
    """Return producer-consumer pairs from a dbt manifest parent_map."""
    edges: set[tuple[str, str]] = set()
    for consumer, parents in parent_map.items():
        for producer in parents:
            if producer and consumer:
                edges.add((str(producer), str(consumer)))
    return frozenset(edges)


def artifact_model_edges(
    edges: Sequence[tuple[str, str]],
    aliases: Mapping[str, str],
) -> frozenset[tuple[str, str]]:
    """Map reuse-key lineage onto dbt unique ids using an alias table."""
    mapped: set[tuple[str, str]] = set()
    for producer, consumer in edges:
        left = aliases.get(producer, producer)
        right = aliases.get(consumer, consumer)
        mapped.add((left, right))
    return frozenset(mapped)


def lineage_matches(
    artifact_edges: Sequence[tuple[str, str]],
    parent_map: Mapping[str, Sequence[str]],
    aliases: Mapping[str, str],
) -> bool:
    """Return whether artifact edges cover the declared dbt source/ref graph."""
    expected = dbt_edges(parent_map)
    observed = artifact_model_edges(artifact_edges, aliases)
    return expected <= observed
