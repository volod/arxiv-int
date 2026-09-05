"""Backend-neutral retrieval records and quality metrics."""

from arxiv_int.retrieval.metrics import (
    RetrievalCase,
    RetrievalMetrics,
    RetrievedChunk,
    SourceSpan,
    evaluate_retrieval,
)

__all__ = [
    "RetrievalCase",
    "RetrievalMetrics",
    "RetrievedChunk",
    "SourceSpan",
    "evaluate_retrieval",
]
