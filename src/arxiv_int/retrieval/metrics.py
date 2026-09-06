"""Retrieval metrics based on stable source-span overlap."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """A half-open character range in one source document."""

    document_id: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class RetrievedChunk(SourceSpan):
    """A retrieved chunk and other source locations collapsed into it."""

    text: str = ""
    occurrences: tuple[SourceSpan, ...] = ()


@dataclass(frozen=True, slots=True)
class RetrievalCase:
    """One ranked retrieval result and its reviewed evidence spans."""

    chunks: tuple[RetrievedChunk, ...]
    spans: tuple[SourceSpan, ...]


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    """Aggregate rank, evidence-intactness, and served-context readings."""

    count: int
    k: int
    recall_at_k: float
    mean_reciprocal_rank: float
    span_character_coverage_at_k: float
    span_intact_at_k: float
    mean_served_characters_at_k: float


def _locations(chunk: RetrievedChunk) -> tuple[SourceSpan, ...]:
    return (SourceSpan(chunk.document_id, chunk.start, chunk.end), *chunk.occurrences)


def spans_overlap(first: SourceSpan, second: SourceSpan) -> bool:
    """Return whether two half-open ranges overlap in the same document."""
    return (
        first.document_id == second.document_id
        and first.start < second.end
        and second.start < first.end
    )


def chunk_hits_span(chunk: RetrievedChunk, span: SourceSpan) -> bool:
    """Match a chunk at its retained or duplicate-collapsed source locations."""
    return any(spans_overlap(location, span) for location in _locations(chunk))


def first_hit_rank(chunks: tuple[RetrievedChunk, ...], spans: tuple[SourceSpan, ...]) -> int | None:
    """Return the one-based rank of the first chunk overlapping any evidence span."""
    for rank, chunk in enumerate(chunks, 1):
        if any(chunk_hits_span(chunk, span) for span in spans):
            return rank
    return None


def _overlap_ranges(chunks: tuple[RetrievedChunk, ...], span: SourceSpan) -> list[tuple[int, int]]:
    overlaps: list[tuple[int, int]] = []
    for chunk in chunks:
        for location in _locations(chunk):
            if location.document_id != span.document_id:
                continue
            start, end = max(location.start, span.start), min(location.end, span.end)
            if start < end:
                overlaps.append((start, end))
    return overlaps


def _union_length(ranges: list[tuple[int, int]]) -> int:
    total = 0
    reach: int | None = None
    for start, end in sorted(ranges):
        lower = start if reach is None else max(start, reach)
        if end > lower:
            total += end - lower
        reach = end if reach is None else max(reach, end)
    return total


def _span_coverage(chunks: tuple[RetrievedChunk, ...], span: SourceSpan) -> float:
    length = span.end - span.start
    return _union_length(_overlap_ranges(chunks, span)) / length if length > 0 else 0.0


def _span_is_intact(chunks: tuple[RetrievedChunk, ...], span: SourceSpan) -> bool:
    if span.end <= span.start:
        return False
    return any(
        location.document_id == span.document_id
        and location.start <= span.start
        and location.end >= span.end
        for chunk in chunks
        for location in _locations(chunk)
    )


def _case_metrics(case: RetrievalCase, k: int) -> tuple[float, float, float, float, int]:
    top = case.chunks[:k]
    rank = first_hit_rank(case.chunks, case.spans)
    recall = float(first_hit_rank(top, case.spans) is not None)
    reciprocal_rank = 1.0 / rank if rank is not None else 0.0
    if case.spans:
        character_coverage = sum(_span_coverage(top, span) for span in case.spans) / len(case.spans)
        intact = sum(_span_is_intact(top, span) for span in case.spans) / len(case.spans)
    else:
        character_coverage = intact = 1.0
    served = sum(len(chunk.text) for chunk in top)
    return recall, reciprocal_rank, character_coverage, intact, served


def evaluate_retrieval(cases: tuple[RetrievalCase, ...], *, k: int) -> RetrievalMetrics:
    """Aggregate top-k retrieval quality over reviewed cases."""
    if k <= 0:
        raise ValueError("k must be positive")
    if not cases:
        return RetrievalMetrics(0, k, 0.0, 0.0, 0.0, 0.0, 0.0)
    readings = [_case_metrics(case, k) for case in cases]
    count = len(readings)
    columns = tuple(sum(row[index] for row in readings) / count for index in range(5))
    return RetrievalMetrics(count, k, *columns)
