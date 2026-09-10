"""Typed lexical requests, hits, and results shared by the search entry points."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from arxiv_int.retrieval.projection import LexicalTarget
from arxiv_int.retrieval.query_normalization import (
    SELECTED_QUERY_PROFILE,
    query_policy_fingerprint,
)
from arxiv_int.stores.projections.adapters.lexical_search import SEARCH_FIELDS, LexicalFieldError

DEFAULT_LIMIT = 10
DEFAULT_SNIPPET_CHARS = 200
DEFAULT_FACET_LIMIT = 10
MAX_LIMIT = 1000
STAGE_PRIMARY = "primary"


@dataclass(frozen=True, slots=True)
class LexicalRequest:
    """One bounded lexical query with its filters and result shaping."""

    query: str
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    fields: tuple[str, ...] = SEARCH_FIELDS
    language: str | None = None
    document_id: str | None = None
    snippets: bool = True
    snippet_chars: int = DEFAULT_SNIPPET_CHARS
    facets: tuple[str, ...] = ()
    facet_limit: int = DEFAULT_FACET_LIMIT
    lenient: bool = False
    query_profile: str = SELECTED_QUERY_PROFILE

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise LexicalFieldError("a lexical query must contain at least one term")
        if not 0 < self.limit <= MAX_LIMIT:
            raise LexicalFieldError(f"limit must be between 1 and {MAX_LIMIT}")
        if self.offset < 0:
            raise LexicalFieldError("offset must not be negative")
        if self.snippet_chars <= 0:
            raise LexicalFieldError("snippet_chars must be positive")
        if not 0 < self.facet_limit <= MAX_LIMIT:
            raise LexicalFieldError(f"facet_limit must be between 1 and {MAX_LIMIT}")

    def filters(self) -> dict[str, str]:
        """Return the applied equality filters keyed by indexed field."""
        applied = {"language": self.language or "", "document_id": self.document_id or ""}
        return {name: value for name, value in applied.items() if value}


@dataclass(frozen=True, slots=True)
class LexicalHit:
    """One ranked chunk with the evidence needed to resolve its citation."""

    rank: int
    chunk_id: str
    document_id: str
    title: str
    language: str
    score: float
    snippet: str = ""

    def as_json_dict(self) -> dict[str, object]:
        """Return a secret-free result row."""
        return {
            "chunkId": self.chunk_id,
            "documentId": self.document_id,
            "language": self.language,
            "rank": self.rank,
            "score": self.score,
            "snippet": self.snippet,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class LexicalResult:
    """Ranked hits with total matches, facets, and the projection they came from.

    ``query_stage`` names the plan stage that produced the hits: ``primary``, or
    ``fallback``/``fuzzy`` when an earlier stage matched nothing.
    """

    target: LexicalTarget
    hits: tuple[LexicalHit, ...]
    total: int
    facets: Mapping[str, tuple[tuple[str, int], ...]] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    query_profile: str = SELECTED_QUERY_PROFILE
    query_stage: str = STAGE_PRIMARY

    def as_json_dict(self) -> dict[str, object]:
        """Return a secret-free JSON view of one search."""
        return {
            "elapsedMs": self.elapsed_ms,
            "facets": {
                name: [{"matched": count, "value": value} for value, count in values]
                for name, values in sorted(self.facets.items())
            },
            "hits": [hit.as_json_dict() for hit in self.hits],
            "projection": self.target.as_json_dict(),
            "queryPolicyFingerprint": query_policy_fingerprint(),
            "queryProfile": self.query_profile,
            "queryStage": self.query_stage,
            "total": self.total,
        }
