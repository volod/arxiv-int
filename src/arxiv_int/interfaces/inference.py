"""Seam between callers and one local inference provider."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

GenerationStatus = Literal["ok", "refused", "malformed"]


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """One local generation call and the settings that belong to its provenance."""

    prompt: str
    temperature: float = 0.0
    max_output_tokens: int | None = None
    json_schema: Mapping[str, object] | None = None
    schema_version: str = ""


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """One provider answer with the model identity that produced it."""

    text: str
    status: GenerationStatus
    model_id: str
    model_digest: str


@runtime_checkable
class InferenceProvider(Protocol):
    """Provider-neutral access to a local model endpoint, never a hosted one."""

    name: str
    feature: str

    def available_models(self) -> Sequence[str]:
        """Return the model identifiers the local endpoint currently serves."""

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Run one bounded generation and report an explicit result status."""
