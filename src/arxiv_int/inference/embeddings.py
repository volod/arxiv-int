"""Embedding and Ollama unload operations for the local inference client."""

from threading import Event
from time import monotonic
from typing import Any

from arxiv_int.inference import ollama, vllm
from arxiv_int.inference.policy import log_outcome
from arxiv_int.inference.transport import TransportError
from arxiv_int.inference.types import (
    CAPABILITY_EMBEDDINGS,
    EmbeddingRequest,
    EmbeddingResult,
    ModelIdentity,
)


class EmbeddingMixin:
    """Embedding and unload methods mixed into LocalInferenceClient."""

    name: str
    embedding_model: str

    def _json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        cancel: Event | None = None,
    ) -> tuple[int, object]:
        raise NotImplementedError

    def identify(self, model_id: str, *, cancel: Event | None = None) -> ModelIdentity:
        raise NotImplementedError

    def embed(self, request: EmbeddingRequest, cancel: Event | None = None) -> EmbeddingResult:
        """Embed texts on a model that advertises embedding capability."""
        model_id = request.model_id or self.embedding_model
        start = monotonic()
        try:
            identity = self.identify(model_id, cancel=cancel)
            if CAPABILITY_EMBEDDINGS not in identity.capabilities:
                raise TransportError(
                    "architecture_unsupported", f"model {model_id} does not support embeddings"
                )
            path, payload = (
                (ollama.EMBED_PATH, ollama.embed_payload(model_id, request.texts))
                if self.name == "ollama"
                else (vllm.EMBED_PATH, vllm.embed_payload(model_id, request.texts))
            )
            status, body = self._json(
                "POST", path, payload, timeout=request.timeout_seconds, cancel=cancel
            )
            if status != 200:
                raise TransportError(_embed_failure(self.name, body, status), f"HTTP {status}")
            vectors = (
                ollama.parse_embeddings(body)
                if self.name == "ollama"
                else vllm.parse_embeddings(body)
            )
            dimensions = len(vectors[0]) if vectors else 0
            result = EmbeddingResult(vectors, "ok", model_id, identity.digest, dimensions)
        except TransportError as error:
            result = EmbeddingResult((), error.status, model_id, "", 0)  # type: ignore[arg-type]
        log_outcome(
            "embed",
            backend=self.name,
            model_id=model_id,
            status=result.status,
            latency_seconds=monotonic() - start,
        )
        return result

    def unload(self, model_id: str, *, cancel: Event | None = None) -> None:
        """Drop an Ollama model from VRAM. vLLM unload is owned by the scheduler task."""
        if self.name != "ollama":
            raise TransportError(
                "architecture_unsupported", "vLLM unload is not an inference request"
            )
        self._json("POST", ollama.GENERATE_PATH, ollama.unload_payload(model_id), cancel=cancel)


def _embed_failure(backend: str, payload: object, status: int) -> str:
    missing = (
        ollama.is_missing_model(payload, status)
        if backend == "ollama"
        else vllm.is_missing_model(payload, status) or vllm.is_unsupported(payload, status)
    )
    return "architecture_unsupported" if missing else "backend_error"
