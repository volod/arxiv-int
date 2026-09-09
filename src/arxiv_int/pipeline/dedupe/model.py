"""Typed policy, records, and identities for duplicate and edition grouping."""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass

ALGORITHM_VERSION = "2"
EXACT = "exact"
NORMALIZED = "normalized"
LEXICAL = "lexical"
EDITION = "edition"
DUPLICATE_METHODS: tuple[str, ...] = (EXACT, NORMALIZED, LEXICAL)
METHOD_RANK: dict[str, int] = {EXACT: 0, NORMALIZED: 1, LEXICAL: 2, EDITION: 3}
REPRESENTATIVE = "representative"
MEMBER = "member"


@dataclass(frozen=True, slots=True)
class DedupePolicy:
    """Explicit bounds and thresholds for one duplicate-grouping producer."""

    batch_rows: int = 256
    shingle_words: int = 2
    sketch_bins: int = 128
    band_rows: int = 2
    max_shingle_tokens: int = 400_000
    max_bucket_documents: int = 256
    max_candidate_pairs: int = 200_000
    duplicate_similarity: float = 0.90
    edition_similarity: float = 0.45
    min_sketch_shingles: int = 5

    def __post_init__(self) -> None:
        if self.sketch_bins % self.band_rows:
            raise ValueError("sketch_bins must be a multiple of band_rows")
        if not 0.0 < self.edition_similarity < self.duplicate_similarity <= 1.0:
            raise ValueError("edition_similarity must be below duplicate_similarity")


DEFAULT_POLICY = DedupePolicy()


@dataclass(frozen=True, slots=True)
class DocumentSketch:
    """One normalized document reduced to grouping keys and a lexical sketch."""

    document_id: str
    normalized_document_id: str
    exact_key: str
    normalized_key: str
    text_chars: int
    signature: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class GroupMember:
    """One proposed, reversible membership of a document in a group."""

    group_id: str
    document_id: str
    method: str
    role: str
    score: float
    suppressed: bool


def dedupe_id(policy: DedupePolicy) -> str:
    """Return the stable identity of one grouping algorithm and policy."""
    payload = json.dumps(
        {"algorithm": ALGORITHM_VERSION, "policy": asdict(policy)},
        ensure_ascii=True,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()[:32]


def group_id(family: str, members: Sequence[str]) -> str:
    """Derive a stable group identity from its family and sorted membership."""
    value = json.dumps([family, sorted(members)], ensure_ascii=True)
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def membership_id(group: str, document_id: str) -> str:
    """Derive a stable membership identity inside one group."""
    value = f"duplicate-membership:{group}:{document_id}"
    return hashlib.sha256(value.encode("ascii")).hexdigest()
