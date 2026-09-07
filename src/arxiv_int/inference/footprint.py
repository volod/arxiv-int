"""Declared model footprints: weights, KV cache, overhead, and host RAM."""

import re
from dataclasses import dataclass

from arxiv_int.inference.types import ModelIdentity

_SIZE_TOKEN = re.compile(r"(\d+)b")
DEFAULT_CONTEXT_TOKENS = 2048
DEFAULT_BATCH_SIZE = 1
DEFAULT_RUNTIME_OVERHEAD_GIB = 1.0
DEFAULT_KV_PER_1K_GIB = 0.08
DEFAULT_CPU_RAM_GIB = 4.0
DEFAULT_HEADROOM_GIB = 0.5
DEFAULT_DB_RESERVE_GIB = 4.0


@dataclass(frozen=True, slots=True)
class ModelFootprint:
    """Declared per-model resource envelope used before a load is attempted."""

    weights_gib: float
    kv_cache_per_1k_context_gib: float = DEFAULT_KV_PER_1K_GIB
    runtime_overhead_gib: float = DEFAULT_RUNTIME_OVERHEAD_GIB
    cpu_ram_gib: float = DEFAULT_CPU_RAM_GIB
    cpu_offload_gib: float = 0.0
    allow_cpu: bool = True

    def __post_init__(self) -> None:
        for name in (
            "weights_gib",
            "kv_cache_per_1k_context_gib",
            "runtime_overhead_gib",
            "cpu_ram_gib",
            "cpu_offload_gib",
        ):
            value = float(getattr(self, name))
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True, slots=True)
class FootprintEstimate:
    """Accounted GPU and host-RAM cost for one context/batch setting."""

    gpu_gib: float
    cpu_ram_gib: float
    weights_on_gpu_gib: float
    kv_cache_gib: float
    runtime_overhead_gib: float
    cpu_offload_gib: float
    context_tokens: int
    batch_size: int

    def reason(self) -> str:
        """Return an ASCII breakdown operators can act on."""
        return (
            f"need {self.gpu_gib:.1f} GiB GPU (weights {self.weights_on_gpu_gib:.1f} + "
            f"kv {self.kv_cache_gib:.1f} + overhead {self.runtime_overhead_gib:.1f}) "
            f"at context {self.context_tokens} batch {self.batch_size}; "
            f"host RAM {self.cpu_ram_gib:.1f} GiB"
            + (
                f" after {self.cpu_offload_gib:.1f} GiB CPU offload"
                if self.cpu_offload_gib > 0
                else ""
            )
        )


def estimate_footprint(
    footprint: ModelFootprint,
    *,
    context_tokens: int = DEFAULT_CONTEXT_TOKENS,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> FootprintEstimate:
    """Estimate VRAM and RAM from declared weights plus KV/context/batch/overhead."""
    if context_tokens <= 0:
        raise ValueError("context_tokens must be positive")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    kv = footprint.kv_cache_per_1k_context_gib * (context_tokens / 1000.0) * batch_size
    weights_on_gpu = max(0.0, footprint.weights_gib - footprint.cpu_offload_gib)
    gpu = weights_on_gpu + kv + footprint.runtime_overhead_gib
    return FootprintEstimate(
        gpu_gib=gpu,
        cpu_ram_gib=footprint.cpu_ram_gib,
        weights_on_gpu_gib=weights_on_gpu,
        kv_cache_gib=kv,
        runtime_overhead_gib=footprint.runtime_overhead_gib,
        cpu_offload_gib=footprint.cpu_offload_gib,
        context_tokens=context_tokens,
        batch_size=batch_size,
    )


def footprint_from_mapping(item: object) -> ModelFootprint:
    """Parse an optional registry footprint object."""
    if not isinstance(item, dict):
        raise ValueError("model footprint must be an object")
    weights = item.get("weights_gib")
    if not isinstance(weights, (int, float)):
        raise ValueError("model footprint is missing weights_gib")
    return ModelFootprint(
        weights_gib=float(weights),
        kv_cache_per_1k_context_gib=_optional_float(
            item, "kv_cache_per_1k_context_gib", DEFAULT_KV_PER_1K_GIB
        ),
        runtime_overhead_gib=_optional_float(
            item, "runtime_overhead_gib", DEFAULT_RUNTIME_OVERHEAD_GIB
        ),
        cpu_ram_gib=_optional_float(item, "cpu_ram_gib", DEFAULT_CPU_RAM_GIB),
        cpu_offload_gib=_optional_float(item, "cpu_offload_gib", 0.0),
        allow_cpu=bool(item.get("allow_cpu", True)),
    )


def with_cpu_offload(footprint: ModelFootprint, cpu_offload_gib: float) -> ModelFootprint:
    """Return a copy that places declared CPU offload on the host instead of the GPU."""
    if cpu_offload_gib < 0:
        raise ValueError("cpu_offload_gib must be non-negative")
    if cpu_offload_gib == footprint.cpu_offload_gib:
        return footprint
    return ModelFootprint(
        weights_gib=footprint.weights_gib,
        kv_cache_per_1k_context_gib=footprint.kv_cache_per_1k_context_gib,
        runtime_overhead_gib=footprint.runtime_overhead_gib,
        cpu_ram_gib=footprint.cpu_ram_gib,
        cpu_offload_gib=cpu_offload_gib,
        allow_cpu=footprint.allow_cpu,
    )


def default_footprint_for(identity: ModelIdentity) -> ModelFootprint:
    """Conservative envelope when a registry profile omits a footprint."""
    sizes = tuple(int(token) for token in _SIZE_TOKEN.findall(identity.model_id.lower()))
    if any(size >= 24 for size in sizes):
        return ModelFootprint(
            weights_gib=16.8,
            kv_cache_per_1k_context_gib=0.18,
            runtime_overhead_gib=1.2,
            cpu_ram_gib=24.0,
            allow_cpu=True,
        )
    if any(size <= 4 for size in sizes):
        return ModelFootprint(
            weights_gib=3.1,
            kv_cache_per_1k_context_gib=0.05,
            runtime_overhead_gib=0.6,
            cpu_ram_gib=6.0,
            allow_cpu=True,
        )
    return ModelFootprint(weights_gib=8.0, allow_cpu=True)


def _optional_float(item: dict[str, object], name: str, default: float) -> float:
    value = item.get(name, default)
    if not isinstance(value, (int, float)):
        raise ValueError(f"model footprint {name} must be a number")
    return float(value)
