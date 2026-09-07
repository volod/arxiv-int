"""GPU-aware placement from a host snapshot and a declared footprint."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal

from arxiv_int.inference.footprint import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CONTEXT_TOKENS,
    DEFAULT_HEADROOM_GIB,
    FootprintEstimate,
)
from arxiv_int.inference.resources import HostSnapshot

DevicePlacement = Literal["cuda", "cpu", "unavailable"]


@dataclass(frozen=True, slots=True)
class OccupancySnapshot:
    """Who currently occupies the GPU runtime."""

    ollama_loaded: tuple[str, ...] = ()
    ollama_vram_gib: float = 0.0
    vllm_ready: bool = False
    ollama_resident: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True, slots=True)
class ModelRequirement:
    """Resources and fallback policy for one model-backed operation."""

    model_id: str
    gpu_gib: float = 0.0
    allow_cpu: bool = True
    backend: str = "ollama"
    context_tokens: int = DEFAULT_CONTEXT_TOKENS
    batch_size: int = DEFAULT_BATCH_SIZE
    cpu_ram_gib: float = 0.0
    allow_unload: bool = True
    allow_service_control: bool = False
    unload_on_release: bool = True
    workload: str = "generation"

    def __post_init__(self) -> None:
        if self.gpu_gib < 0 or self.cpu_ram_gib < 0:
            raise ValueError("resource amounts must be non-negative")
        if self.backend not in {"ollama", "vllm"}:
            raise ValueError("backend must be ollama or vllm")


@dataclass(frozen=True, slots=True)
class ModelPlacement:
    """Chosen device and the reason it is safe for this host snapshot."""

    model_id: str
    device: DevicePlacement
    detail: str


def place_requirement(
    requirement: ModelRequirement,
    snapshot: HostSnapshot,
    estimate: FootprintEstimate,
    occupancy: OccupancySnapshot,
    *,
    headroom_gib: float = DEFAULT_HEADROOM_GIB,
) -> ModelPlacement:
    """Choose cuda, explicit CPU fallback, or an actionable unavailable rejection."""
    gpu_need = requirement.gpu_gib if requirement.gpu_gib > 0 else estimate.gpu_gib
    cpu_need = requirement.cpu_ram_gib if requirement.cpu_ram_gib > 0 else estimate.cpu_ram_gib
    ram_budget = snapshot.available_ram_gib - snapshot.database_reserve_gib
    ram_ok = ram_budget >= cpu_need
    free_after_unload, unload_names, reclaimable = _gpu_budget(requirement, snapshot, occupancy)
    gpu_ok = (
        bool(snapshot.gpus)
        and gpu_need + headroom_gib <= free_after_unload
        and _foreign_runtime_allows_cuda(requirement, occupancy)
    )
    if gpu_ok and ram_ok:
        return ModelPlacement(
            requirement.model_id,
            "cuda",
            _cuda_detail(estimate, snapshot, unload_names, reclaimable),
        )
    if requirement.allow_cpu and ram_ok:
        return ModelPlacement(
            requirement.model_id,
            "cpu",
            _cpu_detail(gpu_need, free_after_unload, occupancy, requirement),
        )
    return ModelPlacement(
        requirement.model_id,
        "unavailable",
        _reject_detail(
            gpu_need, free_after_unload, cpu_need, ram_budget, ram_ok, occupancy, requirement
        ),
    )


def _gpu_budget(
    requirement: ModelRequirement, snapshot: HostSnapshot, occupancy: OccupancySnapshot
) -> tuple[float, tuple[str, ...], float]:
    pairs = occupancy.ollama_resident
    if not pairs and occupancy.ollama_loaded:
        share = occupancy.ollama_vram_gib / len(occupancy.ollama_loaded)
        pairs = tuple((name, share) for name in occupancy.ollama_loaded)
    keep = requirement.model_id
    others = tuple(name for name, _vram in pairs if name != keep)
    others_vram = sum(vram for name, vram in pairs if name != keep)
    keep_vram = sum(vram for name, vram in pairs if name == keep)
    reclaimable = others_vram if requirement.allow_unload else 0.0
    unload = others if requirement.allow_unload else ()
    return snapshot.free_gpu_gib + reclaimable + keep_vram, unload, reclaimable


def _vllm_blocks_ollama(requirement: ModelRequirement, occupancy: OccupancySnapshot) -> bool:
    return (
        occupancy.vllm_ready
        and requirement.backend == "ollama"
        and not requirement.allow_service_control
    )


def _vllm_needs_start(requirement: ModelRequirement, occupancy: OccupancySnapshot) -> bool:
    return (
        requirement.backend == "vllm"
        and not occupancy.vllm_ready
        and not requirement.allow_service_control
    )


def _foreign_runtime_allows_cuda(
    requirement: ModelRequirement, occupancy: OccupancySnapshot
) -> bool:
    if requirement.backend == "vllm" and not occupancy.vllm_ready:
        return requirement.allow_service_control
    if occupancy.vllm_ready and requirement.backend == "ollama":
        return requirement.allow_service_control
    return True


def _cuda_detail(
    estimate: FootprintEstimate,
    snapshot: HostSnapshot,
    unload_names: tuple[str, ...],
    reclaimable: float,
) -> str:
    extra = ""
    if unload_names:
        extra = f"; will unload {', '.join(unload_names)} (reclaim {reclaimable:.1f} GiB)"
    return (
        f"fits observed free VRAM {snapshot.free_gpu_gib:.1f} GiB on {snapshot.gpu_name}; "
        f"{estimate.reason()}{extra}"
    )


def _cpu_detail(
    gpu_need: float,
    free_after_unload: float,
    occupancy: OccupancySnapshot,
    requirement: ModelRequirement,
) -> str:
    if _vllm_blocks_ollama(requirement, occupancy):
        return (
            "explicit CPU fallback: vLLM occupies the GPU; stop the vllm Compose profile "
            "or pass allow_service_control"
        )
    if _vllm_needs_start(requirement, occupancy):
        return (
            "explicit CPU fallback: vLLM is not running; start the vllm Compose profile "
            "or pass allow_service_control"
        )
    return (
        f"explicit CPU fallback: GPU budget is insufficient "
        f"(need {gpu_need:.1f} GiB, {free_after_unload:.1f} GiB free after unload)"
    )


def _reject_detail(
    gpu_need: float,
    free_after_unload: float,
    cpu_need: float,
    ram_budget: float,
    ram_ok: bool,
    occupancy: OccupancySnapshot,
    requirement: ModelRequirement,
) -> str:
    if not ram_ok:
        return (
            f"CPU/database RAM is insufficient: need {cpu_need:.1f} GiB plus database reserve, "
            f"{ram_budget:.1f} GiB available; free RAM, reduce batch, or skip this model"
        )
    if _vllm_blocks_ollama(requirement, occupancy):
        return (
            "GPU is occupied by vLLM; stop the vllm Compose profile with an explicit operator "
            "request, select a CPU-capable profile, or pass allow_service_control"
        )
    if _vllm_needs_start(requirement, occupancy):
        return (
            "vLLM is not running; start the vllm Compose profile with an explicit operator "
            "request, select a CPU-capable profile, or pass allow_service_control"
        )
    return (
        f"GPU budget is insufficient: need {gpu_need:.1f} GiB including weights, KV cache, "
        f"context, batch and runtime overhead; {free_after_unload:.1f} GiB free after unload. "
        f"Select a smaller/quantized profile, reduce context/batch, enable CPU fallback, "
        f"or offload"
    )


class ModelScheduler:
    """Plan one-at-a-time model residency from an observed free-VRAM budget."""

    def __init__(
        self,
        free_gpu_gib: float | None = None,
        snapshot: HostSnapshot | None = None,
        occupancy: OccupancySnapshot | None = None,
        headroom_gib: float = DEFAULT_HEADROOM_GIB,
    ) -> None:
        if snapshot is None:
            if free_gpu_gib is None:
                raise ValueError("snapshot or free_gpu_gib is required")
            if free_gpu_gib < 0:
                raise ValueError("free_gpu_gib must be non-negative")
            from arxiv_int.inference.resources import GpuDevice, RamSnapshot

            gpus = (
                (GpuDevice(0, "fixture", free_gpu_gib, free_gpu_gib, 0.0, 0.0, 0.0),)
                if free_gpu_gib > 0
                else ()
            )
            snapshot = HostSnapshot(
                ram=RamSnapshot(total_gib=64.0, available_gib=48.0),
                gpus=gpus,
            )
        self.snapshot = snapshot
        self.occupancy = occupancy or OccupancySnapshot()
        self.headroom_gib = headroom_gib

    def place(
        self, requirement: ModelRequirement, estimate: FootprintEstimate | None = None
    ) -> ModelPlacement:
        used = estimate or FootprintEstimate(
            gpu_gib=requirement.gpu_gib,
            cpu_ram_gib=requirement.cpu_ram_gib,
            weights_on_gpu_gib=requirement.gpu_gib,
            kv_cache_gib=0.0,
            runtime_overhead_gib=0.0,
            cpu_offload_gib=0.0,
            context_tokens=requirement.context_tokens,
            batch_size=requirement.batch_size,
        )
        return place_requirement(
            requirement, self.snapshot, used, self.occupancy, headroom_gib=self.headroom_gib
        )

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
