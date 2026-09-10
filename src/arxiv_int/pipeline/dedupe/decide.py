"""Turn scratch sketch tables into one bounded, reversible grouping decision."""

from dataclasses import dataclass, field
from pathlib import Path

from arxiv_int.pipeline.dedupe.group import (
    DUPLICATE_FAMILY,
    EDITION_FAMILY,
    Edge,
    assemble,
    band_candidates,
    duplicate_membership,
    key_edges,
    load_signatures,
    load_sizes,
)
from arxiv_int.pipeline.dedupe.minhash import similarity
from arxiv_int.pipeline.dedupe.model import (
    EDITION,
    EXACT,
    LEXICAL,
    NORMALIZED,
    DedupePolicy,
    GroupMember,
)


@dataclass(slots=True)
class GroupingPlan:
    """Every proposed relation and membership produced by one grouping pass."""

    duplicates: list[GroupMember] = field(default_factory=list)
    editions: list[GroupMember] = field(default_factory=list)
    pairs: list[tuple[Edge, str]] = field(default_factory=list)
    candidates: int = 0
    truncated: bool = False

    @property
    def members(self) -> list[GroupMember]:
        """Return duplicate and edition memberships in publication order."""
        return [*self.duplicates, *self.editions]


def plan_groups(sketch_path: Path, band_path: Path, policy: DedupePolicy) -> GroupingPlan:
    """Group documents by exact key, normalized key, and verified lexical similarity."""
    plan = GroupingPlan()
    duplicate_edges = [
        *key_edges(sketch_path, "exact_key", EXACT),
        *key_edges(sketch_path, "normalized_key", NORMALIZED),
    ]
    candidates = band_candidates(band_path, policy)
    plan.candidates = len(candidates)
    plan.truncated = len(candidates) >= policy.max_candidate_pairs
    edition_edges: list[Edge] = []
    signatures = load_signatures(
        sketch_path, sorted({item for pair in candidates for item in pair})
    )
    for left, right in candidates:
        first, second = signatures.get(left), signatures.get(right)
        if first is None or second is None:
            continue
        score = similarity(first, second)
        if score >= policy.duplicate_similarity:
            duplicate_edges.append(Edge(left, right, LEXICAL, score))
        elif score >= policy.edition_similarity:
            edition_edges.append(Edge(left, right, EDITION, score))
    sizes = load_sizes(sketch_path, _endpoints(duplicate_edges, edition_edges))
    plan.duplicates = assemble(duplicate_edges, sizes, DUPLICATE_FAMILY, suppress_members=True)
    grouped = duplicate_membership(plan.duplicates)
    retained = [
        edge
        for edge in edition_edges
        if grouped.get(edge.left, edge.left) != grouped.get(edge.right, edge.right)
    ]
    plan.editions = assemble(retained, sizes, EDITION_FAMILY, suppress_members=False)
    plan.pairs = [
        *((edge, DUPLICATE_FAMILY) for edge in duplicate_edges),
        *((edge, EDITION_FAMILY) for edge in retained),
    ]
    return plan


def _endpoints(*groups: list[Edge]) -> list[str]:
    seen: set[str] = set()
    for edges in groups:
        for edge in edges:
            seen.add(edge.left)
            seen.add(edge.right)
    return sorted(seen)
