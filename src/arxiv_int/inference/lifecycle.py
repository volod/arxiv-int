"""Ollama unload/keep-alive and requested vLLM Compose start/stop."""

from dataclasses import dataclass
from threading import Event
from typing import Protocol

from arxiv_int.inference.client import LocalInferenceClient
from arxiv_int.inference.errors import ModelFitError
from arxiv_int.inference.scheduling import ModelRequirement, OccupancySnapshot
from arxiv_int.inference.transport import TransportError
from arxiv_int.inference.types import LoadedModel


class VllmController(Protocol):
    """Start or stop the optional vLLM Compose profile when the caller requested it."""

    def start(self) -> None:
        """Start the vLLM service."""

    def stop(self) -> None:
        """Stop only the vLLM service."""

    def ready(self) -> bool:
        """Return whether the vLLM endpoint currently responds."""


@dataclass
class RecordingVllmController:
    """Test double that records requested start/stop without touching Compose."""

    running: bool = False
    starts: int = 0
    stops: int = 0

    def start(self) -> None:
        self.starts += 1
        self.running = True

    def stop(self) -> None:
        self.stops += 1
        self.running = False

    def ready(self) -> bool:
        return self.running


@dataclass
class OccupancyProbe:
    """Read Ollama resident models and optional vLLM occupancy."""

    client: LocalInferenceClient | None = None
    vllm: VllmController | None = None
    loaded: tuple[str, ...] = ()
    loaded_vram_gib: float = 0.0

    def probe(self, cancel: Event | None = None) -> OccupancySnapshot:
        models = self._ollama_models(cancel)
        vllm_ready = self.vllm.ready() if self.vllm is not None else False
        names = tuple(model.model_id for model in models)
        vram = sum(model.vram_gib for model in models)
        resident = tuple((model.model_id, model.vram_gib) for model in models)
        return OccupancySnapshot(names, vram, vllm_ready, resident)

    def _ollama_models(self, cancel: Event | None) -> tuple[LoadedModel, ...]:
        if self.client is None or self.client.name != "ollama":
            return _fallback_loaded(self.loaded, self.loaded_vram_gib)
        try:
            return self.client.loaded_models(cancel=cancel)
        except (TransportError, OSError, ValueError):
            return _fallback_loaded(self.loaded, self.loaded_vram_gib)


def prepare_device(
    requirement: ModelRequirement,
    occupancy: OccupancySnapshot,
    *,
    client: LocalInferenceClient | None,
    vllm: VllmController | None,
    cancel: Event | None = None,
) -> tuple[str, ...]:
    """Unload competing Ollama models and start/stop vLLM only when requested."""
    actions: list[str] = []
    if requirement.backend == "ollama" and occupancy.vllm_ready:
        _stop_vllm_if_requested(requirement, vllm)
        actions.append("stopped vLLM profile")
    if requirement.backend == "vllm":
        _start_vllm_if_requested(requirement, occupancy, vllm)
        if vllm is not None and not occupancy.vllm_ready:
            actions.append("started vLLM profile")
    if client is not None and client.name == "ollama" and requirement.allow_unload:
        keep = requirement.model_id if requirement.backend == "ollama" else ""
        unloaded = unload_resident(client, keep=keep, cancel=cancel)
        actions.extend(f"unloaded {name}" for name in unloaded)
    return tuple(actions)


def unload_resident(
    client: LocalInferenceClient, *, keep: str, cancel: Event | None = None
) -> tuple[str, ...]:
    """Ask Ollama to drop loaded models other than keep via keep_alive=0."""
    try:
        loaded = client.loaded_models(cancel=cancel)
    except (TransportError, OSError, ValueError):
        return ()
    unloaded: list[str] = []
    for model in loaded:
        if model.model_id == keep:
            continue
        try:
            client.unload(model.model_id, cancel=cancel)
        except (TransportError, OSError, ValueError):
            continue
        unloaded.append(model.model_id)
    return tuple(unloaded)


def release_device(
    requirement: ModelRequirement,
    *,
    client: LocalInferenceClient | None,
    cancel: Event | None = None,
) -> tuple[str, ...]:
    """Drop the Ollama model from VRAM after a sequential GPU session."""
    if (
        client is None
        or client.name != "ollama"
        or not requirement.unload_on_release
        or requirement.backend != "ollama"
    ):
        return ()
    try:
        client.unload(requirement.model_id, cancel=cancel)
    except (TransportError, OSError, ValueError):
        return ()
    return (requirement.model_id,)


def _stop_vllm_if_requested(requirement: ModelRequirement, vllm: VllmController | None) -> None:
    if not requirement.allow_service_control or vllm is None:
        raise ModelFitError(
            "vLLM occupies the GPU; stop the vllm Compose profile with an explicit "
            "operator request or pass allow_service_control"
        )
    vllm.stop()


def _start_vllm_if_requested(
    requirement: ModelRequirement, occupancy: OccupancySnapshot, vllm: VllmController | None
) -> None:
    if occupancy.vllm_ready:
        return
    if not requirement.allow_service_control or vllm is None:
        raise ModelFitError(
            "vLLM is not running; start the vllm Compose profile with an explicit "
            "operator request or pass allow_service_control"
        )
    vllm.start()


def _fallback_loaded(names: tuple[str, ...], vram_gib: float) -> tuple[LoadedModel, ...]:
    if not names:
        return ()
    share = vram_gib / len(names)
    return tuple(LoadedModel(name, share) for name in names)
