"""Seam between callers and one local inference provider."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

GenerationStatus = Literal[
    "ok",
    "refused",
    "malformed",
    "timeout",
    "cancelled",
    "backend_error",
    "architecture_unsupported",
]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One chat turn. Prompt text is never a log field."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """One local generation call and the settings that belong to its provenance."""

    prompt: str
    temperature: float = 0.0
    max_output_tokens: int | None = None
    json_schema: Mapping[str, object] | None = None
    schema_version: str = ""
    model_id: str = ""
    messages: tuple[ChatMessage, ...] = ()


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """One provider answer with the model identity that produced it."""

    text: str
    status: GenerationStatus
    model_id: str
    model_digest: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_seconds: float = 0.0

    @property
    def tokens_per_second(self) -> float:
        """Report measured completion throughput only for a successful timed call."""
        if self.status != "ok" or self.latency_seconds <= 0 or self.completion_tokens <= 0:
            return 0.0
        return self.completion_tokens / self.latency_seconds


@runtime_checkable
class InferenceProvider(Protocol):
    """Provider-neutral access to a local model endpoint, never a hosted one."""

    name: str
    feature: str

    def available_models(self) -> Sequence[str]:
        """Return the model identifiers the local endpoint currently serves."""

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Run one bounded generation and report an explicit result status."""
