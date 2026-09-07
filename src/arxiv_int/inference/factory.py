"""Construct a local inference client from resolved runtime configuration."""

from arxiv_int.inference.client import DEFAULT_TIMEOUT_SECONDS, LocalInferenceClient
from arxiv_int.inference.profiles import load_profiles
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
