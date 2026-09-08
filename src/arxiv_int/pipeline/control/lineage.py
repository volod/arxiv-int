"""Transitive artifact edges and the stale closure of an owned fingerprint change."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from arxiv_int.interfaces.tokens import require_token
from arxiv_int.pipeline.control.fingerprints import OWNED_FINGERPRINT_FIELDS, ReuseIdentity


@dataclass(frozen=True, slots=True)
class LineageEdge:
    """One producer-to-consumer reuse-key edge."""

    producer_reuse_key: str
    consumer_reuse_key: str

    def __post_init__(self) -> None:
        require_token(self.producer_reuse_key, "producer_reuse_key")
        require_token(self.consumer_reuse_key, "consumer_reuse_key")
        if self.producer_reuse_key == self.consumer_reuse_key:
            raise ValueError("lineage edge cannot be reflexive")


def stale_closure(
    changed_keys: Iterable[str],
    edges: Sequence[LineageEdge],
) -> frozenset[str]:
    """Return changed reuse keys plus every reachable consumer."""
    remaining = {require_and_copy(key) for key in changed_keys}
    by_producer: dict[str, list[str]] = {}
    for edge in edges:
        by_producer.setdefault(edge.producer_reuse_key, []).append(edge.consumer_reuse_key)
    seen: set[str] = set()
    stack = list(remaining)
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(by_producer.get(current, ()))
    return frozenset(seen)


def keys_matching_owned_change(
    identities: Mapping[str, ReuseIdentity],
    field: str,
    previous: str,
) -> frozenset[str]:
    """Select reuse keys whose owned fingerprint still names the replaced value."""
    if field not in OWNED_FINGERPRINT_FIELDS:
        raise ValueError(f"unknown owned fingerprint field {field!r}")
    require_token(previous, "previous")
    matched = [key for key, identity in identities.items() if identity.owned[field] == previous]
    return frozenset(matched)


def require_and_copy(key: str) -> str:
    """Validate a reuse key token."""
    require_token(key, "reuse_key")
    return key
