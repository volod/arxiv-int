"""Deterministic, structure-aware chunking over normalized documents."""

from arxiv_int.pipeline.chunk.model import DEFAULT_POLICY, ChunkingError, ChunkPolicy

__all__ = ["DEFAULT_POLICY", "ChunkPolicy", "ChunkingError"]
