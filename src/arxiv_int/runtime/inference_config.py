"""Backend-specific generation defaults shared by configuration and Compose."""

OLLAMA_GENERATION_MODEL = "qwen3.8:27b"
VLLM_GENERATION_MODEL = "Qwen/Qwen3.8-27B-FP8"
VLLM_GENERATION_REVISION = "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"


def resolve_inference_defaults(values: dict[str, str]) -> None:
    """Resolve the active model while preserving separate vLLM service settings."""
    defaults = {
        "VLLM_MODEL": VLLM_GENERATION_MODEL,
        "VLLM_MODEL_REVISION": VLLM_GENERATION_REVISION,
    }
    for name, default in defaults.items():
        if not values.get(name, "").strip():
            values[name] = default
    is_vllm = values["INFERENCE_BACKEND"].lower() == "vllm"
    if not values.get("GENERATION_MODEL", "").strip():
        values["GENERATION_MODEL"] = values["VLLM_MODEL"] if is_vllm else OLLAMA_GENERATION_MODEL
    if is_vllm and not values.get("GENERATION_MODEL_REVISION", "").strip():
        values["GENERATION_MODEL_REVISION"] = values["VLLM_MODEL_REVISION"]
