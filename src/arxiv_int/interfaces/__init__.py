"""Typed seams between pipeline policy and the backends that feature groups provide.

Every protocol carries a `feature` attribute naming the feature group an implementation needs,
so an adapter can be declared without importing its optional dependency.
"""

from arxiv_int.interfaces.embedding import EmbeddingProfile, TextEmbedder
from arxiv_int.interfaces.extraction import DocumentExtractor, ExtractedDocument
from arxiv_int.interfaces.inference import (
    ChatMessage,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
    InferenceProvider,
)
from arxiv_int.interfaces.pipeline import StageContext, StageOutcome, StageResult, StageRunner
from arxiv_int.interfaces.stores import ArtifactStore, CanonicalStore, DatasetRef, StoreStatus

__all__ = [
    "ArtifactStore",
    "CanonicalStore",
    "ChatMessage",
    "DatasetRef",
    "DocumentExtractor",
    "EmbeddingProfile",
    "ExtractedDocument",
    "GenerationRequest",
    "GenerationResult",
    "GenerationStatus",
    "InferenceProvider",
    "StageContext",
    "StageOutcome",
    "StageResult",
    "StageRunner",
    "StoreStatus",
    "TextEmbedder",
]
