"""GPU-aware, backend-neutral model placement and lifecycle policy."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal

DevicePlacement = Literal["cuda", "cpu", "unavailable"]


@dataclass(frozen=True, slots=True)
class ModelRequirement:
    """Resources and fallback policy for one model-backed operation."""

    model_id: str
    gpu_gib: float
    allow_cpu: bool = True

    def __post_init__(self) -> None:
        if self.gpu_gib < 0:
            raise ValueError("gpu_gib must be non-negative")


@dataclass(frozen=True, slots=True)
class ModelPlacement:
    """Chosen device and the reason it is safe for this host snapshot."""

    model_id: str
    device: DevicePlacement
    detail: str


class ModelScheduler:
    """Plan one-at-a-time model residency from an observed free-VRAM budget."""

    def __init__(self, free_gpu_gib: float) -> None:
        if free_gpu_gib < 0:
            raise ValueError("free_gpu_gib must be non-negative")
        self.free_gpu_gib = free_gpu_gib

    def place(self, requirement: ModelRequirement) -> ModelPlacement:
        if requirement.gpu_gib <= self.free_gpu_gib and self.free_gpu_gib > 0:
            return ModelPlacement(requirement.model_id, "cuda", "fits observed free VRAM")
        if requirement.allow_cpu:
            return ModelPlacement(requirement.model_id, "cpu", "GPU budget is insufficient")
        return ModelPlacement(requirement.model_id, "unavailable", "GPU budget is insufficient")

    @contextmanager
    def session(
        self,
        requirement: ModelRequirement,
        load: Callable[[DevicePlacement], object],
        release: Callable[[object], None],
    ) -> Iterator[tuple[object, ModelPlacement]]:
        """Load one placed model and always release it after the operation."""
        placement = self.place(requirement)
        if placement.device == "unavailable":
            raise RuntimeError(f"model {requirement.model_id} cannot be placed: {placement.detail}")
        model = load(placement.device)
        try:
            yield model, placement
        finally:
            release(model)
