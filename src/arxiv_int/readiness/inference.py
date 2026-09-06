"""Read-only contract and local inference readiness checks."""

from urllib.parse import urljoin

from arxiv_int.readiness.http_transport import local_base
from arxiv_int.readiness.probes import Probe
from arxiv_int.readiness.report import PreflightReport
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.inference_config import inference_base_url, selected_backend


def check_contracts(report: PreflightReport, config: RuntimeConfig) -> None:
    """Report whether the currently shipped contract registry has readable state."""
    registry = config.project_root / "contracts" / "registry.yaml"
    if not registry.exists():
        report.add("contracts", "ready", "no product contract registry is shipped yet")
        return
    try:
        from arxiv_int.contracts import FileRegistry

        loaded = FileRegistry(registry.parent)
        for contract_id in loaded.contract_ids():
            loaded.load_odcs(contract_id)
            if loaded.get_entry(contract_id).mapping_ref is not None:
                loaded.load_mapping(contract_id)
                loaded.verify_semantic_fingerprint(contract_id)
    except ModuleNotFoundError:
        report.add(
            "contracts",
            "degraded",
            "contract registry exists but the contracts feature group is unavailable",
            action="source scripts/shared/common.sh; arxiv_int_load_env; uv sync --extra contracts",
        )
    except Exception as error:
        report.add(
            "contracts",
            "blocked",
            f"contract registry validation failed: {error.__class__.__name__}",
            action="make contracts",
        )
    else:
        report.add(
            "contracts", "ready", f"{len(loaded.contract_ids())} registered contract(s) validated"
        )


def _vllm_values(values: dict[str, str]) -> dict[str, str]:
    """Use the model identity actually passed to the selected Compose service."""
    model = (
        values["GENERATION_MODEL"] if selected_backend(values) == "vllm" else values["VLLM_MODEL"]
    )
    return dict(
        values,
        INFERENCE_BACKEND="vllm",
        GENERATION_MODEL=model,
        EMBEDDING_MODEL="",
        RERANK_MODEL="",
    )


def check_inference(
    report: PreflightReport,
    config: RuntimeConfig,
    probe: Probe,
    timeout: float,
    *,
    vllm_service: bool = False,
) -> None:
    """Inspect the configured local inference API and requested model identities."""
    values = dict(config.values)
    if vllm_service:
        values = _vllm_values(values)
    backend = selected_backend(values)
    base_url = inference_base_url(values)
    if backend == "ollama":
        endpoint = local_base(base_url or "")
        if endpoint is None:
            report.add(
                "inference.endpoint",
                "blocked",
                "OLLAMA_BASE_URL is not a loopback endpoint",
                action="set OLLAMA_BASE_URL to http://127.0.0.1:11434",
            )
            return
        result = probe.get_json(urljoin(endpoint, "api/tags"), timeout=timeout)
        models = _ollama_models(result.payload)
        action = "ollama serve"
    elif backend == "vllm":
        result = probe.get_json(urljoin(f"{base_url}/", "v1/models"), timeout=timeout)
        models = _openai_models(result.payload)
        action = "make services-up SERVICE_PROFILES=vllm"
    else:
        report.add(
            "inference.backend",
            "blocked",
            f"unsupported inference backend {backend!r}",
            action="set INFERENCE_BACKEND to ollama or vllm",
        )
        return
    if result.status != 200 or models is None:
        report.add(
            "inference.endpoint",
            "degraded",
            f"{backend} local API is unavailable ({result.error or ('invalid model response' if models is None else result.status)})",
            action=action,
        )
        return
    report.add(
        "inference.endpoint", "ready", f"{backend} local API responded; {len(models)} model(s)"
    )
    _check_models(report, values, models, backend, action)


def _check_models(
    report: PreflightReport, values: dict[str, str], models: set[str], backend: str, action: str
) -> None:
    configured = {
        value
        for name in ("EMBEDDING_MODEL", "GENERATION_MODEL", "RERANK_MODEL")
        if (value := values.get(name, "")).strip()
    }
    if not configured:
        report.add(
            "inference.models",
            "degraded",
            "no embedding, generation, or rerank model is configured",
            action="set model identities in .env",
        )
        return
    missing = sorted(configured - models)
    if missing:
        pull = f"ollama pull {missing[0]}" if backend == "ollama" else action
        report.add(
            "inference.models",
            "degraded",
            "configured model(s) unavailable: " + ", ".join(missing),
            action=pull,
        )
    else:
        report.add("inference.models", "ready", "all configured model identities are available")


def _ollama_models(payload: object | None) -> set[str] | None:
    return _model_names(payload, "models", ("name", "model"))


def _openai_models(payload: object | None) -> set[str] | None:
    return _model_names(payload, "data", ("id",))


def _model_names(payload: object | None, key: str, fields: tuple[str, ...]) -> set[str] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
        return None
    names: set[str] = set()
    for item in payload[key]:
        if not isinstance(item, dict):
            return None
        name = next((item[field] for field in fields if item.get(field)), None)
        if not isinstance(name, str) or not name.strip():
            return None
        names.add(name)
    return names
