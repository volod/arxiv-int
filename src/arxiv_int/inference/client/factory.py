"""Construct a local inference client from resolved runtime configuration."""

from arxiv_int.inference.client import LocalInferenceClient
from arxiv_int.inference.client.types import ModelIdentity
from arxiv_int.inference.policy import DEFAULT_TIMEOUT_SECONDS
from arxiv_int.inference.policy.footprint import (
    ModelFootprint,
    default_footprint_for,
    with_cpu_offload,
)
from arxiv_int.inference.policy.profiles import load_footprints, load_profiles
from arxiv_int.inference.providers.vllm_control import ComposeVllmController
from arxiv_int.inference.scheduler import ModelResourceScheduler, scheduler_paths
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.inference_config import inference_base_url, selected_backend


def client_from_config(
    config: RuntimeConfig,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> LocalInferenceClient:
    """Build a client for the configured Ollama or vLLM loopback endpoint."""
    values = dict(config.values)
    backend = selected_backend(values)
    base_url = inference_base_url(values)
    if base_url is None:
        raise ValueError(f"unsupported inference backend {backend!r}")
    return LocalInferenceClient(
        backend,
        base_url,
        default_model=values.get("GENERATION_MODEL", ""),
        default_revision=values.get("GENERATION_MODEL_REVISION", ""),
        embedding_model=values.get("EMBEDDING_MODEL", ""),
        timeout=timeout,
        profiles=load_profiles(config.project_root),
    )


def footprint_from_config(config: RuntimeConfig, backend: str, model_id: str) -> ModelFootprint:
    """Return a declared or conservative footprint, applying vLLM CPU offload when set."""
    footprints = load_footprints(config.project_root)
    footprint = footprints.get((backend, model_id))
    if footprint is None:
        footprint = default_footprint_for(ModelIdentity(model_id, "", backend, frozenset()))
    if backend != "vllm":
        return footprint
    raw = dict(config.values).get("VLLM_CPU_OFFLOAD_GB", "").strip()
    if not raw:
        return footprint
    return with_cpu_offload(footprint, float(raw))


def scheduler_from_config(
    config: RuntimeConfig,
    *,
    run_id: str,
    client: LocalInferenceClient | None = None,
    wait_seconds: float = 30.0,
) -> ModelResourceScheduler:
    """Build the host-wide GPU scheduler for one run id."""
    lease, sink = scheduler_paths(config.service_state_dir, config.runs_dir, run_id)
    return ModelResourceScheduler(
        lease=lease,
        sink=sink,
        run_id=run_id,
        client=client,
        vllm=ComposeVllmController(config),
        wait_seconds=wait_seconds,
    )
