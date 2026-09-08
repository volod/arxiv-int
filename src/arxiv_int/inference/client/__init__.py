"""Provider-neutral local inference client for Ollama and vLLM."""

from collections.abc import Sequence
from threading import Event
from time import monotonic
from typing import Any

from arxiv_int.inference.client.completion import CompletionMixin
from arxiv_int.inference.client.embeddings import EmbeddingMixin
from arxiv_int.inference.client.transport import (
    MAX_ATTEMPTS,
    LocalHttpTransport,
    TransportError,
    retryable_status,
)
from arxiv_int.inference.client.types import HealthStatus, LoadedModel, ModelIdentity
from arxiv_int.inference.policy import (
    DEFAULT_TIMEOUT_SECONDS,
    HEALTH_TIMEOUT_SECONDS,
    log_outcome,
)
from arxiv_int.inference.policy.profiles import profile_for
from arxiv_int.inference.providers import ollama, vllm

FEATURE = "inference"


class LocalInferenceClient(CompletionMixin, EmbeddingMixin):
    """One local HTTP endpoint with typed chat, structured output, and embeddings."""

    feature = FEATURE

    def __init__(
        self,
        backend: str,
        base_url: str,
        *,
        default_model: str = "",
        default_revision: str = "",
        embedding_model: str = "",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        profiles: tuple[ModelIdentity, ...] = (),
        transport: LocalHttpTransport | None = None,
    ) -> None:
        if backend not in {"ollama", "vllm"}:
            raise ValueError("INFERENCE_BACKEND must be ollama or vllm")
        self.name = backend
        self.default_model = default_model
        self.default_revision = default_revision
        self.embedding_model = embedding_model
        self.timeout = timeout
        self.profiles = profiles
        self._transport = transport or LocalHttpTransport(base_url, timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._transport.close()

    def health(self, *, cancel: Event | None = None) -> HealthStatus:
        """Probe endpoint reachability and list served model identities."""
        start = monotonic()
        try:
            models = self._list_models(cancel=cancel)
        except TransportError as error:
            log_outcome(
                "health",
                backend=self.name,
                model_id="",
                status=error.status,
                latency_seconds=monotonic() - start,
            )
            return HealthStatus(False, self.name, error.detail)
        detail = f"{self.name} local API responded; {len(models)} model(s)"
        log_outcome(
            "health",
            backend=self.name,
            model_id="",
            status="ok",
            latency_seconds=monotonic() - start,
        )
        return HealthStatus(True, self.name, detail, models)

    def available_models(self) -> Sequence[str]:
        """Return served model identifiers."""
        return tuple(model.model_id for model in self._list_models())

    def identify(self, model_id: str, *, cancel: Event | None = None) -> ModelIdentity:
        """Return digest and capabilities for one served model."""
        listed = {model.model_id: model for model in self._list_models(cancel=cancel)}
        digest = listed[model_id].digest if model_id in listed else self.default_revision
        if self.name == "ollama":
            status, payload = self._json(
                "POST", ollama.SHOW_PATH, ollama.show_payload(model_id), cancel=cancel
            )
            if ollama.is_missing_model(payload, status):
                raise TransportError(
                    "architecture_unsupported", f"model {model_id} is not available"
                )
            if status != 200:
                raise TransportError("backend_error", f"HTTP {status}")
            identity = ollama.parse_show(payload, model_id, digest)
        else:
            if model_id not in listed:
                raise TransportError(
                    "architecture_unsupported", f"model {model_id} is not available"
                )
            identity = listed[model_id]
        profile = profile_for(self.profiles, self.name, model_id)
        capabilities = identity.capabilities
        if profile is not None:
            capabilities = capabilities | profile.capabilities
            digest = identity.digest or profile.digest
        return ModelIdentity(model_id, digest, self.name, capabilities, identity.detail)

    def loaded_models(self, *, cancel: Event | None = None) -> tuple[LoadedModel, ...]:
        """Return models currently resident on the local endpoint."""
        if self.name != "ollama":
            if not self.default_model:
                return ()
            return (LoadedModel(self.default_model, 0.0),)
        status, payload = self._json(
            "GET", ollama.PS_PATH, cancel=cancel, timeout=HEALTH_TIMEOUT_SECONDS
        )
        if status != 200:
            raise TransportError("backend_error", f"HTTP {status}")
        return ollama.parse_ps(payload)

    def _list_models(self, cancel: Event | None = None) -> tuple[ModelIdentity, ...]:
        if self.name == "ollama":
            status, payload = self._json(
                "GET", ollama.HEALTH_PATH, cancel=cancel, timeout=HEALTH_TIMEOUT_SECONDS
            )
            if status != 200:
                raise TransportError("backend_error", f"HTTP {status}")
            return ollama.parse_tags(payload)
        health_status, _ = self._json(
            "GET", vllm.HEALTH_PATH, cancel=cancel, timeout=HEALTH_TIMEOUT_SECONDS
        )
        if health_status != 200:
            raise TransportError("backend_error", f"HTTP {health_status}")
        status, payload = self._json(
            "GET", vllm.MODELS_PATH, cancel=cancel, timeout=HEALTH_TIMEOUT_SECONDS
        )
        if status != 200:
            raise TransportError("backend_error", f"HTTP {status}")
        return vllm.parse_models(payload, self.default_revision)

    def _json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        cancel: Event | None = None,
    ) -> tuple[int, object]:
        last_error: TransportError | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                status, body = self._transport.request_json(
                    method, path, payload, timeout=timeout, cancel=cancel
                )
            except TransportError as error:
                last_error = error
                if error.status in {"timeout", "cancelled"} or attempt + 1 >= MAX_ATTEMPTS:
                    raise
                continue
            if status < 500 and not retryable_status(status):
                return status, body
            last_error = TransportError("backend_error", f"HTTP {status}")
            if attempt + 1 >= MAX_ATTEMPTS:
                break
        assert last_error is not None
        raise last_error
