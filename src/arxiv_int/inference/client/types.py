"""Typed values for local inference health, identity, embeddings, and stream chunks."""

from dataclasses import dataclass

from arxiv_int.interfaces.inference import GenerationStatus

CAPABILITY_CHAT = "chat"
CAPABILITY_EMBEDDINGS = "embeddings"
CAPABILITY_STRUCTURED = "structured_output"
KNOWN_CAPABILITIES = frozenset({CAPABILITY_CHAT, CAPABILITY_EMBEDDINGS, CAPABILITY_STRUCTURED})


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    """Served model id, digest, and discovered capabilities."""

    model_id: str
    digest: str
    backend: str
    capabilities: frozenset[str]
    detail: str = ""


@dataclass(frozen=True, slots=True)
class LoadedModel:
    """One model currently resident in GPU memory."""

    model_id: str
    vram_gib: float = 0.0


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """Reachability of one local inference endpoint."""

    ready: bool
    backend: str
    detail: str
    models: tuple[ModelIdentity, ...] = ()


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    """One local embedding call. Input text is never a log field."""

    texts: tuple[str, ...]
    model_id: str = ""
    timeout_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """Vectors produced under one model identity, or a typed failure."""

    vectors: tuple[tuple[float, ...], ...]
    status: GenerationStatus
    model_id: str
    model_digest: str
    dimensions: int = 0


@dataclass(frozen=True, slots=True)
class StreamChunk:
    """One assembled stream delta from a local provider."""

    text: str
    done: bool
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = ""
