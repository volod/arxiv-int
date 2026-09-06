"""Seam between the embedding stage and one local embedding backend."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class EmbeddingProfile:
    """Identity that decides whether two embedding sets may be compared.

    Any change of model, revision, pooling, normalization, dimensions, or backend is a new
    profile; vectors from different profiles are never mixed.
    """

    model_id: str
    revision: str
    dimensions: int
    pooling: str
    normalized: bool
    backend: str


@runtime_checkable
class TextEmbedder(Protocol):
    """Produce vectors for already chunked text under one declared profile."""

    profile: EmbeddingProfile
    feature: str

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Return one vector per input text, in input order."""
