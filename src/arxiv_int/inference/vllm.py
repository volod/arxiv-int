"""vLLM OpenAI-compatible local HTTP payload builders and response parsers."""

from collections.abc import Mapping, Sequence
from typing import Any

from arxiv_int.inference.types import (
    CAPABILITY_CHAT,
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_STRUCTURED,
    ModelIdentity,
    StreamChunk,
)
from arxiv_int.interfaces.inference import ChatMessage, GenerationRequest

HEALTH_PATH = "/health"
MODELS_PATH = "/v1/models"
CHAT_PATH = "/v1/chat/completions"
EMBED_PATH = "/v1/embeddings"


def chat_payload(
    request: GenerationRequest, model_id: str, messages: Sequence[ChatMessage]
) -> dict[str, Any]:
    """Build a streaming vLLM chat-completions body."""
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": message.role, "content": message.content} for message in messages],
        "stream": True,
        "temperature": request.temperature,
    }
    if request.max_output_tokens is not None:
        payload["max_tokens"] = request.max_output_tokens
    if request.json_schema is not None:
        name = request.schema_version or "structured_output"
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": name.replace(".", "_"),
                "schema": dict(request.json_schema),
                "strict": True,
            },
        }
    return payload


def embed_payload(model_id: str, texts: Sequence[str]) -> dict[str, Any]:
    """Build a vLLM /v1/embeddings body."""
    return {"model": model_id, "input": list(texts)}


def parse_models(payload: object, default_revision: str) -> tuple[ModelIdentity, ...]:
    """Parse /v1/models into identities."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("invalid vLLM model list")
    models: list[ModelIdentity] = []
    for item in payload["data"]:
        models.append(_model_identity(item, default_revision))
    return tuple(models)


def _model_identity(item: object, default_revision: str) -> ModelIdentity:
    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
        raise ValueError("invalid vLLM model list")
    digest = item.get("root") or item.get("parent") or default_revision
    capabilities = {CAPABILITY_CHAT, CAPABILITY_STRUCTURED}
    owned = item.get("owned_by")
    if isinstance(owned, str) and "embed" in owned.lower():
        capabilities = {CAPABILITY_EMBEDDINGS}
    if "embed" in item["id"].lower():
        capabilities = {CAPABILITY_EMBEDDINGS}
    return ModelIdentity(
        model_id=item["id"],
        digest=digest if isinstance(digest, str) else default_revision,
        backend="vllm",
        capabilities=frozenset(capabilities),
    )


def parse_stream_line(payload: Mapping[str, Any]) -> StreamChunk:
    """Parse one OpenAI-style SSE JSON chunk."""
    choices = payload.get("choices")
    text = ""
    finish = ""
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        choice = choices[0]
        delta = choice.get("delta")
        message = choice.get("message")
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            text = delta["content"]
        elif isinstance(message, dict) and isinstance(message.get("content"), str):
            text = message["content"]
        reason = choice.get("finish_reason")
        finish = reason if isinstance(reason, str) else ""
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return StreamChunk(
        text=text,
        done=bool(finish) or payload.get("done") is True,
        prompt_tokens=_usage(usage, "prompt_tokens"),
        completion_tokens=_usage(usage, "completion_tokens"),
        finish_reason=finish,
    )


def parse_embeddings(payload: object) -> tuple[tuple[float, ...], ...]:
    """Parse /v1/embeddings vectors in input order."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("invalid vLLM embeddings")
    ordered = sorted(
        (item for item in payload["data"] if isinstance(item, dict)),
        key=lambda item: item.get("index", 0) if isinstance(item.get("index"), int) else 0,
    )
    vectors: list[tuple[float, ...]] = []
    for item in ordered:
        embedding = item.get("embedding")
        if not isinstance(embedding, list) or not all(
            isinstance(number, (int, float)) for number in embedding
        ):
            raise ValueError("invalid vLLM embeddings")
        vectors.append(tuple(float(number) for number in embedding))
    return tuple(vectors)


def is_missing_model(payload: object, status_code: int) -> bool:
    """Report a missing or incompatible vLLM model identity."""
    text = _error_message(payload).lower()
    if "not found" in text or "does not exist" in text:
        return True
    return status_code == 404


def is_unsupported(payload: object, status_code: int) -> bool:
    """Report an architecture or capability rejection from vLLM."""
    if status_code not in {400, 422}:
        return False
    lowered = _error_message(payload).lower()
    return any(token in lowered for token in ("not support", "unsupported", "embedding"))


def _error_message(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    raw = error.get("message") if isinstance(error, dict) else error
    return raw if isinstance(raw, str) else ""


def _usage(usage: object, name: str) -> int:
    if isinstance(usage, dict):
        value = usage.get(name)
        if isinstance(value, int):
            return value
    return 0
