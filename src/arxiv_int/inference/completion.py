"""Chat, generate, structured-output validation, and bounded repair."""

import json
from collections.abc import Mapping, Sequence
from threading import Event
from time import monotonic
from typing import Any

from arxiv_int.inference import ollama, vllm
from arxiv_int.inference.policy import log_outcome
from arxiv_int.inference.schema import (
    MAX_REPAIR_ATTEMPTS,
    is_refusal_payload,
    parse_json_object,
    repair_user_message,
    validate_instance,
)
from arxiv_int.inference.stream import collect_text
from arxiv_int.inference.transport import (
    MAX_ATTEMPTS,
    LocalHttpTransport,
    TransportError,
    cancelled,
)
from arxiv_int.inference.types import CAPABILITY_CHAT, CAPABILITY_EMBEDDINGS, ModelIdentity
from arxiv_int.interfaces.inference import ChatMessage, GenerationRequest, GenerationResult


class CompletionMixin:
    """Chat and structured-output methods mixed into LocalInferenceClient."""

    name: str
    default_model: str
    timeout: float
    _transport: LocalHttpTransport

    def identify(self, model_id: str, *, cancel: Event | None = None) -> ModelIdentity:
        raise NotImplementedError

    def generate(self, request: GenerationRequest, cancel: Event | None = None) -> GenerationResult:
        """Run one bounded generation, including structured output and repair."""
        model_id = request.model_id or self.default_model
        start = monotonic()
        try:
            result = self._generate(request, model_id, cancel)
        except TransportError as error:
            result = failed_result(error.status, model_id, "")
        result = GenerationResult(
            text=result.text,
            status=result.status,
            model_id=result.model_id or model_id,
            model_digest=result.model_digest,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_seconds=monotonic() - start,
        )
        log_outcome(
            "generate",
            backend=self.name,
            model_id=result.model_id,
            status=result.status,
            latency_seconds=result.latency_seconds,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
        return result

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model_id: str = "",
        temperature: float = 0.0,
        json_schema: dict[str, Any] | None = None,
        schema_version: str = "",
        max_output_tokens: int | None = None,
        cancel: Event | None = None,
    ) -> GenerationResult:
        """Run one chat completion through the same typed generate path."""
        prompt = messages[-1].content if messages else ""
        return self.generate(
            GenerationRequest(
                prompt=prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                json_schema=json_schema,
                schema_version=schema_version,
                model_id=model_id,
                messages=tuple(messages),
            ),
            cancel,
        )

    def _generate(
        self, request: GenerationRequest, model_id: str, cancel: Event | None
    ) -> GenerationResult:
        identity = self._require_chat(model_id, cancel)
        messages = request.messages or (ChatMessage("user", request.prompt),)
        digest = identity.digest
        last = failed_result("malformed", model_id, digest)
        for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
            if cancelled(cancel):
                return failed_result("cancelled", model_id, digest)
            text, chunk = self._complete(request, model_id, messages, cancel)
            digest = digest or identity.digest
            if chunk.finish_reason == "content_filter":
                return GenerationResult(
                    "", "refused", model_id, digest, chunk.prompt_tokens, chunk.completion_tokens
                )
            last = GenerationResult(
                text, "ok", model_id, digest, chunk.prompt_tokens, chunk.completion_tokens
            )
            if request.json_schema is None:
                return last
            last, errors = validate_structured(last, request.json_schema)
            if last.status in {"ok", "refused"} or attempt >= MAX_REPAIR_ATTEMPTS:
                return last
            messages = (
                *messages,
                ChatMessage("assistant", text),
                ChatMessage("user", repair_user_message(errors)),
            )
        return last

    def _complete(
        self,
        request: GenerationRequest,
        model_id: str,
        messages: Sequence[ChatMessage],
        cancel: Event | None,
    ) -> tuple[str, Any]:
        last_error: TransportError | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                return self._complete_once(request, model_id, messages, cancel)
            except TransportError as error:
                last_error = error
                if error.status in {"timeout", "cancelled", "architecture_unsupported"}:
                    raise
                if attempt + 1 >= MAX_ATTEMPTS:
                    raise
        assert last_error is not None
        raise last_error

    def _complete_once(
        self,
        request: GenerationRequest,
        model_id: str,
        messages: Sequence[ChatMessage],
        cancel: Event | None,
    ) -> tuple[str, Any]:
        if self.name == "ollama":
            use_chat = bool(request.messages) or request.json_schema is not None
            path = ollama.CHAT_PATH if use_chat else ollama.GENERATE_PATH
            payload = (
                ollama.chat_payload(request, model_id, messages)
                if use_chat
                else ollama.generate_payload(request, model_id)
            )
            parse = ollama.parse_stream_line
        else:
            path = vllm.CHAT_PATH
            payload = vllm.chat_payload(request, model_id, messages)
            parse = vllm.parse_stream_line
        return collect_text(
            self._transport, path, payload, parse, timeout=self.timeout, cancel=cancel
        )

    def _require_chat(self, model_id: str, cancel: Event | None) -> ModelIdentity:
        if not model_id.strip():
            raise TransportError("architecture_unsupported", "no generation model is configured")
        identity = self.identify(model_id, cancel=cancel)
        if (
            CAPABILITY_CHAT not in identity.capabilities
            and CAPABILITY_EMBEDDINGS in identity.capabilities
        ):
            raise TransportError(
                "architecture_unsupported", f"model {model_id} does not support chat"
            )
        return identity


def validate_structured(
    result: GenerationResult, schema: Mapping[str, Any]
) -> tuple[GenerationResult, tuple[str, ...]]:
    """Validate one model payload against a JSON Schema without logging it."""
    try:
        instance = parse_json_object(result.text)
    except (json.JSONDecodeError, ValueError):
        return _with_status(result, "malformed"), ("output was not valid JSON",)
    if is_refusal_payload(instance):
        return _with_status(result, "refused"), ()
    errors = validate_instance(schema, instance)
    if errors:
        return _with_status(result, "malformed"), errors
    return result, ()


def failed_result(status: str, model_id: str, digest: str) -> GenerationResult:
    """Build a typed failure without prompt text."""
    return GenerationResult("", status, model_id, digest)  # type: ignore[arg-type]


def _with_status(result: GenerationResult, status: str) -> GenerationResult:
    return GenerationResult(
        result.text,
        status,  # type: ignore[arg-type]
        result.model_id,
        result.model_digest,
        result.prompt_tokens,
        result.completion_tokens,
    )
