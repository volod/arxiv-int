"""Ollama local HTTP payload builders and response parsers."""

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

HEALTH_PATH = "/api/tags"
CHAT_PATH = "/api/chat"
GENERATE_PATH = "/api/generate"
EMBED_PATH = "/api/embed"
SHOW_PATH = "/api/show"
UNLOAD_KEEP_ALIVE = "0"


def chat_payload(
    request: GenerationRequest, model_id: str, messages: Sequence[ChatMessage]
) -> dict[str, Any]:
    """Build a streaming Ollama /api/chat body."""
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": message.role, "content": message.content} for message in messages],
        "stream": True,
        "options": {"temperature": request.temperature},
    }
    if request.max_output_tokens is not None:
        payload["options"]["num_predict"] = request.max_output_tokens
    if request.json_schema is not None:
        payload["format"] = dict(request.json_schema)
    return payload


def generate_payload(request: GenerationRequest, model_id: str) -> dict[str, Any]:
    """Build a streaming Ollama /api/generate body."""
    payload: dict[str, Any] = {
        "model": model_id,
        "prompt": request.prompt,
        "stream": True,
        "options": {"temperature": request.temperature},
    }
    if request.max_output_tokens is not None:
        payload["options"]["num_predict"] = request.max_output_tokens
    if request.json_schema is not None:
        payload["format"] = dict(request.json_schema)
    return payload


def embed_payload(model_id: str, texts: Sequence[str]) -> dict[str, Any]:
    """Build an Ollama /api/embed body."""
    return {"model": model_id, "input": list(texts)}


def show_payload(model_id: str) -> dict[str, Any]:
    """Build an Ollama /api/show body."""
    return {"model": model_id}


def unload_payload(model_id: str) -> dict[str, Any]:
    """Ask Ollama to drop a loaded model without generating tokens."""
    return {"model": model_id, "keep_alive": UNLOAD_KEEP_ALIVE, "prompt": "", "stream": False}


def parse_tags(payload: object) -> tuple[ModelIdentity, ...]:
    """Parse /api/tags into model identities."""
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise ValueError("invalid Ollama model list")
    models: list[ModelIdentity] = []
    for item in payload["models"]:
        if not isinstance(item, dict):
            raise ValueError("invalid Ollama model list")
        name = item.get("name") or item.get("model")
        digest = item.get("digest")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("invalid Ollama model list")
        models.append(
            ModelIdentity(
                model_id=name,
                digest=digest if isinstance(digest, str) else "",
                backend="ollama",
                capabilities=_capabilities_from_details(item),
            )
        )
    return tuple(models)


def parse_show(payload: object, model_id: str, digest: str) -> ModelIdentity:
    """Parse /api/show into capabilities plus digest."""
    if not isinstance(payload, dict):
        raise ValueError("invalid Ollama model identity")
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    merged = dict(payload)
    if isinstance(details, dict):
        merged.update(details)
    return ModelIdentity(
        model_id=model_id,
        digest=_show_digest(payload, digest),
        backend="ollama",
        capabilities=_capabilities_from_details(merged),
        detail="ollama show",
    )


def parse_stream_line(payload: Mapping[str, Any]) -> StreamChunk:
    """Parse one Ollama NDJSON stream object."""
    message = payload.get("message")
    text = ""
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        text = message["content"]
    elif isinstance(payload.get("response"), str):
        text = payload["response"]
    done = bool(payload.get("done"))
    finish = payload.get("done_reason")
    return StreamChunk(
        text=text,
        done=done,
        prompt_tokens=_int_field(payload, "prompt_eval_count"),
        completion_tokens=_int_field(payload, "eval_count"),
        finish_reason=finish if isinstance(finish, str) else "",
    )


def parse_embeddings(payload: object) -> tuple[tuple[float, ...], ...]:
    """Parse /api/embed vectors."""
    if not isinstance(payload, dict):
        raise ValueError("invalid Ollama embeddings")
    vectors = payload.get("embeddings")
    if isinstance(vectors, list):
        return _as_vectors(vectors)
    single = payload.get("embedding")
    if isinstance(single, list):
        return _as_vectors([single])
    raise ValueError("invalid Ollama embeddings")


def is_missing_model(payload: object, status_code: int) -> bool:
    """Report a missing or unknown Ollama model identity."""
    if status_code == 404:
        return True
    if isinstance(payload, dict) and isinstance(payload.get("error"), str):
        return "not found" in payload["error"].lower()
    return False


def _show_digest(payload: Mapping[str, Any], fallback: str) -> str:
    model_info = payload.get("model_info")
    if isinstance(model_info, dict):
        digest = model_info.get("general.basename")
        if isinstance(digest, str) and digest.startswith("sha256:"):
            return digest
    details = payload.get("details")
    if isinstance(details, dict):
        digest_value = details.get("digest")
        if isinstance(digest_value, str):
            return digest_value
    payload_digest = payload.get("digest")
    if isinstance(payload_digest, str):
        return payload_digest
    return fallback


def _capabilities_from_details(item: Mapping[str, Any]) -> frozenset[str]:
    raw = item.get("capabilities")
    names: set[str] = set()
    if isinstance(raw, list):
        tokens = {str(value).lower() for value in raw}
        if tokens & {"completion", "chat", "tools"}:
            names.add(CAPABILITY_CHAT)
            names.add(CAPABILITY_STRUCTURED)
        if "embedding" in tokens or "embeddings" in tokens:
            names.add(CAPABILITY_EMBEDDINGS)
    family = str(item.get("family") or item.get("parameter_size") or "")
    if "embed" in family.lower():
        names.add(CAPABILITY_EMBEDDINGS)
    if not names:
        names.update({CAPABILITY_CHAT, CAPABILITY_STRUCTURED})
    return frozenset(names)


def _int_field(payload: Mapping[str, Any], name: str) -> int:
    value = payload.get(name)
    return int(value) if isinstance(value, int) else 0


def _as_vectors(values: list[object]) -> tuple[tuple[float, ...], ...]:
    vectors: list[tuple[float, ...]] = []
    for item in values:
        if not isinstance(item, list) or not all(
            isinstance(number, (int, float)) for number in item
        ):
            raise ValueError("invalid Ollama embeddings")
        vectors.append(tuple(float(number) for number in item))
    return tuple(vectors)
