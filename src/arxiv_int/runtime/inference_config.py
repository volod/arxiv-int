"""Backend-specific inference defaults shared by configuration, Compose and readiness."""

from collections.abc import Mapping

OLLAMA_GENERATION_MODEL = "qwen3.8:27b"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
VLLM_GENERATION_MODEL = "Qwen/Qwen3.8-27B-FP8"
VLLM_GENERATION_REVISION = "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"
VLLM_DEFAULT_PORT = "8000"
SUPPORTED_BACKENDS = ("ollama", "vllm")
_LOOPBACK = "127.0.0.1"


def resolve_inference_defaults(values: dict[str, str]) -> None:
    """Resolve the active model while preserving separate vLLM service settings."""
    defaults = {
        "VLLM_MODEL": VLLM_GENERATION_MODEL,
        "VLLM_MODEL_REVISION": VLLM_GENERATION_REVISION,
    }
    for name, default in defaults.items():
        if not values.get(name, "").strip():
            values[name] = default
    is_vllm = selected_backend(values) == "vllm"
    if not values.get("GENERATION_MODEL", "").strip():
        values["GENERATION_MODEL"] = values["VLLM_MODEL"] if is_vllm else OLLAMA_GENERATION_MODEL
    if is_vllm and not values.get("GENERATION_MODEL_REVISION", "").strip():
        values["GENERATION_MODEL_REVISION"] = values["VLLM_MODEL_REVISION"]


def selected_backend(values: Mapping[str, str]) -> str:
    """Return the normalized inference backend every entry point must agree on."""
    return values.get("INFERENCE_BACKEND", "").strip().lower() or SUPPORTED_BACKENDS[0]


def inference_base_url(values: Mapping[str, str]) -> str | None:
    """Return the base URL of the selected local inference API, or None when unsupported."""
    backend = selected_backend(values)
    if backend == "ollama":
        return values.get("OLLAMA_BASE_URL", "").strip() or OLLAMA_BASE_URL
    if backend == "vllm":
        return f"http://{_LOOPBACK}:{values.get('VLLM_PORT', '').strip() or VLLM_DEFAULT_PORT}"
    return None
