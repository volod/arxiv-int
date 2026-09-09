"""Out-of-core candidate generation and reversible group assembly."""

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from arxiv_int.features import require_module
from arxiv_int.pipeline.dedupe.model import (
    EDITION,
    EXACT,
    LEXICAL,
    MEMBER,
    METHOD_RANK,
    NORMALIZED,
    REPRESENTATIVE,
    DedupePolicy,
    GroupMember,
    group_id,
)

DUPLICATE_FAMILY = "duplicate"
EDITION_FAMILY = "edition"


@dataclass(frozen=True, slots=True)
class Edge:
    """One proposed similarity relation between two documents."""

    left: str
    right: str
    method: str
    score: float


class UnionFind:
    """Disjoint-set forest over document ids."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        """Return the representative id of one item's component."""
        self._parent.setdefault(item, item)
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[item] != root:
            self._parent[item], item = root, self._parent[item]
        return root

    def union(self, left: str, right: str) -> None:
        """Merge the components holding two items."""
        first, second = self.find(left), self.find(right)
        if first != second:
            self._parent[max(first, second)] = min(first, second)

    def components(self) -> dict[str, list[str]]:
        """Return every component keyed by its representative id."""
        grouped: dict[str, list[str]] = {}
        for item in self._parent:
            grouped.setdefault(self.find(item), []).append(item)
        return {root: sorted(members) for root, members in grouped.items()}


def key_edges(path: Path, column: str, method: str) -> Iterator[Edge]:
    """Stream exact-key edges by grouping one scratch column out of core."""
    polars = require_module("polars")
    frame = (
        polars.scan_parquet(path)
        .filter(polars.col(column).is_not_null())
        .group_by(column)
        .agg(polars.col("document_id"))
        .filter(polars.col("document_id").list.len() > 1)
        .collect(engine="streaming")
    )
    for row in frame.iter_rows(named=True):
        members = sorted(row["document_id"])
        for other in members[1:]:
            yield Edge(members[0], other, method, 1.0)


def band_candidates(path: Path, policy: DedupePolicy) -> list[tuple[str, str]]:
    """Return bounded locality-sensitive candidate pairs from banded sketches."""
    polars = require_module("polars")
    frame = (
        polars.scan_parquet(path)
        .group_by(["band_index", "band_key"])
        .agg(polars.col("document_id"))
        .with_columns(polars.col("document_id").list.len().alias("size"))
        .filter((polars.col("size") > 1) & (polars.col("size") <= policy.max_bucket_documents))
        .select("document_id")
        .collect(engine="streaming")
    )
    pairs: set[tuple[str, str]] = set()
    for row in frame.iter_rows(named=True):
        for left, right in combinations(sorted(row["document_id"]), 2):
            pairs.add((left, right))
            if len(pairs) >= policy.max_candidate_pairs:
                return sorted(pairs)
    return sorted(pairs)


def load_signatures(path: Path, document_ids: Sequence[str]) -> dict[str, tuple[int, ...]]:
    """Load only the sketches needed to verify the bounded candidate set."""
    return {
        document_id: tuple(int(item) for item in values)
        for document_id, values in _load(path, document_ids, "signature").items()
    }


def load_sizes(path: Path, document_ids: Sequence[str]) -> dict[str, int]:
    """Load the character counts used to elect one representative per group."""
    return {
        document_id: int(value)
        for document_id, value in _load(path, document_ids, "text_chars").items()
    }


def _load(path: Path, document_ids: Sequence[str], column: str) -> dict[str, Any]:
    if not document_ids:
        return {}
    polars = require_module("polars")
    frame = (
        polars.scan_parquet(path)
        .filter(polars.col("document_id").is_in(list(document_ids)))
        .select("document_id", column)
        .collect(engine="streaming")
    )
    return {str(row["document_id"]): row[column] for row in frame.iter_rows(named=True)}


def assemble(
    edges: Iterable[Edge],
    sizes: Mapping[str, int],
    family: str,
    *,
    suppress_members: bool,
) -> list[GroupMember]:
    """Turn similarity edges into reversible group memberships with one representative."""
    forest = UnionFind()
    incident: dict[str, tuple[str, float]] = {}
    for edge in edges:
        forest.union(edge.left, edge.right)
        _note_method(incident, edge)
    members: list[GroupMember] = []
    for component in forest.components().values():
        members.extend(_component_members(component, sizes, family, incident, suppress_members))
    return members


def _note_method(incident: dict[str, tuple[str, float]], edge: Edge) -> None:
    strength = (METHOD_RANK[edge.method], -edge.score)
    for item in (edge.left, edge.right):
        current = incident.get(item)
        if current is None or strength < (METHOD_RANK[current[0]], -current[1]):
            incident[item] = (edge.method, edge.score)


def _component_members(
    component: list[str],
    sizes: Mapping[str, int],
    family: str,
    incident: Mapping[str, tuple[str, float]],
    suppress_members: bool,
) -> list[GroupMember]:
    if len(component) < 2:
        return []
    identity = group_id(family, component)
    leader = max(component, key=lambda item: (sizes.get(item, 0), _reverse(item)))
    members: list[GroupMember] = []
    for document_id in component:
        method, score = incident.get(document_id, (family, 1.0))
        is_leader = document_id == leader
        members.append(
            GroupMember(
                identity,
                document_id,
                method,
                REPRESENTATIVE if is_leader else MEMBER,
                round(score, 6),
                suppress_members and not is_leader,
            )
        )
    return members


def duplicate_membership(members: Sequence[GroupMember]) -> dict[str, str]:
    """Map each grouped document to its duplicate group id."""
    return {member.document_id: member.group_id for member in members}


def _reverse(value: str) -> tuple[int, ...]:
    return tuple(-ord(char) for char in value)


def method_counts(members: Sequence[GroupMember]) -> dict[str, int]:
    """Count memberships by proposing method for manifest evidence."""
    counts = {method: 0 for method in (EXACT, NORMALIZED, LEXICAL, EDITION)}
    for member in members:
        counts[member.method] = counts.get(member.method, 0) + 1
    return counts
