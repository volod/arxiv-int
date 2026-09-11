"""Declared lexical integration metrics that do not embed source text."""

import re
import unicodedata
from collections.abc import Sequence

from arxiv_int.retrieval.citations import ChunkCitation
from arxiv_int.retrieval.lexical_model import LexicalHit
from arxiv_int.retrieval.metrics import RetrievedChunk, SourceSpan

KNOWN_ITEM_K = 10
KNOWN_ITEM_MIN_CASES = 8
MAX_COMMON_HITS = 80
PAGE_LIMIT = 3
LATENCY_P95_MS_MAX = 2000.0
MISSING_IDENTIFIER = "missing-lexical-probe-000000000000"
DECLARED_QUERY_KINDS = (
    "known-item",
    "identifier",
    "document-filter",
    "language-facet",
    "limit",
    "offset",
    "explain",
    "missing-identifier",
)
_WORD = re.compile(r"[A-Za-z\u0400-\u04ff]{6,}")


def probe_terms(body: str, *, limit: int = 4) -> tuple[str, ...]:
    """Return the longest distinct letter tokens from one chunk body."""
    seen: list[str] = []
    for match in _WORD.finditer(body):
        token = unicodedata.normalize("NFC", match.group(0).casefold())
        if token not in seen:
            seen.append(token)
    return tuple(sorted(seen, key=len, reverse=True)[:limit])


def retrieved_chunks(
    hits: Sequence[LexicalHit], citations: Sequence[ChunkCitation]
) -> tuple[RetrievedChunk, ...]:
    """Map ranked hits onto citation spans without retaining source text."""
    by_id = {item.chunk_id: item for item in citations}
    chunks: list[RetrievedChunk] = []
    for hit in hits:
        citation = by_id.get(hit.chunk_id)
        if citation is None:
            continue
        chunks.append(
            RetrievedChunk(citation.span.document_id, citation.span.start, citation.span.end, "")
        )
    return tuple(chunks)


def identifier_exactness(hits: Sequence[LexicalHit], chunk_id: str, document_id: str) -> float:
    """Return 1.0 when lookup recovered the requested chunk and document ids."""
    if not hits:
        return 0.0
    hit = hits[0]
    return float(hit.chunk_id == chunk_id and hit.document_id == document_id)


def filter_matches(hits: Sequence[LexicalHit], *, document_id: str) -> bool:
    """Return whether every hit belongs to the requested document."""
    return bool(hits) and all(hit.document_id == document_id for hit in hits)


def limit_honored(hit_count: int, total: int, limit: int) -> bool:
    """Return whether the engine respected the requested page size."""
    if hit_count > limit:
        return False
    if total >= limit:
        return hit_count == limit
    return hit_count == total


def offset_matches(first: Sequence[LexicalHit], paged: Sequence[LexicalHit]) -> bool:
    """Return whether offset 1 selected the second hit of the first page."""
    return len(first) >= 2 and len(paged) == 1 and paged[0].chunk_id == first[1].chunk_id


def gold_span(document_id: str, start: int, end: int) -> SourceSpan:
    """Return the sampled chunk's own source span as known-item gold."""
    return SourceSpan(document_id, start, end)
