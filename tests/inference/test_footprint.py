"""Declared footprint accounting for weights, KV cache, offload, and size tokens."""

from pathlib import Path

from arxiv_int.inference.footprint import (
    ModelFootprint,
    default_footprint_for,
    estimate_footprint,
    with_cpu_offload,
)
from arxiv_int.inference.profiles import load_profiles
from arxiv_int.inference.types import ModelIdentity

PROJECT_ROOT = Path(__file__).parents[2]


def test_estimates_kv_cache_from_context_and_batch() -> None:
    footprint = ModelFootprint(
        weights_gib=16.8,
        kv_cache_per_1k_context_gib=0.18,
        runtime_overhead_gib=1.2,
        cpu_ram_gib=24.0,
    )
    short = estimate_footprint(footprint, context_tokens=2048, batch_size=1)
    wide = estimate_footprint(footprint, context_tokens=32768, batch_size=2)
    assert short.kv_cache_gib == 0.18 * 2.048
    assert wide.kv_cache_gib == 0.18 * 32.768 * 2
    assert short.gpu_gib < wide.gpu_gib
    assert "weights" in short.reason()
    assert "KV" in short.reason() or "kv" in short.reason()


def test_cpu_offload_reduces_gpu_weights() -> None:
    footprint = with_cpu_offload(
        ModelFootprint(weights_gib=28.0, runtime_overhead_gib=1.5, cpu_ram_gib=32.0),
        24.0,
    )
    estimate = estimate_footprint(footprint, context_tokens=2048, batch_size=1)
    assert estimate.weights_on_gpu_gib == 4.0
    assert estimate.cpu_offload_gib == 24.0
    assert estimate.gpu_gib < 8.0


def test_default_footprint_does_not_treat_27b_as_4b() -> None:
    large = default_footprint_for(ModelIdentity("qwen3.8:27b", "", "ollama", frozenset()))
    small = default_footprint_for(ModelIdentity("gemma3:4b", "", "ollama", frozenset()))
    assert large.weights_gib > 10
    assert small.weights_gib < 4


def test_registry_lists_qwen_and_gemma_not_llama() -> None:
    ids = {profile.model_id for profile in load_profiles(PROJECT_ROOT)}
    assert "qwen3.8:27b" in ids
    assert "gemma3:4b" in ids
    assert "Qwen/Qwen3.8-27B-FP8" in ids
    assert not any("llama" in model_id.lower() for model_id in ids)
