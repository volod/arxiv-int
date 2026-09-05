"""Read-only contract and local inference readiness checks."""

from urllib.parse import urljoin, urlparse

from arxiv_int.readiness.probes import Probe
from arxiv_int.readiness.report import PreflightReport
from arxiv_int.runtime.config_model import RuntimeConfig


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


def check_inference(
    report: PreflightReport, config: RuntimeConfig, probe: Probe, timeout: float
) -> None:
    """Inspect the configured local inference API and requested model identities."""
    values = dict(config.values)
    backend = values.get("INFERENCE_BACKEND", "ollama").lower()
    if backend == "ollama":
        base_url = values.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        local_base = _local_base(base_url)
        if local_base is None:
            report.add(
                "inference.endpoint",
                "blocked",
                "OLLAMA_BASE_URL is not a loopback endpoint",
                action="set OLLAMA_BASE_URL to http://127.0.0.1:11434",
            )
            return
        result = probe.get_json(urljoin(local_base, "api/tags"), timeout=timeout)
        models = _ollama_models(result.payload)
        action = "ollama serve"
    elif backend == "vllm":
        result = probe.get_json("http://127.0.0.1:8000/v1/models", timeout=timeout)
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
    if result.status != 200:
        report.add(
            "inference.endpoint",
            "degraded",
            f"{backend} local API is unavailable ({result.error or result.status})",
            action=action,
        )
        return
    report.add(
        "inference.endpoint", "ready", f"{backend} local API responded; {len(models)} model(s)"
    )
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


def _local_base(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost"}:
        return None
    return value.rstrip("/") + "/"


def _ollama_models(payload: object | None) -> set[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        return set()
    return {
        str(item.get("name") or item.get("model"))
        for item in payload["models"]
        if isinstance(item, dict) and (item.get("name") or item.get("model"))
    }


def _openai_models(payload: object | None) -> set[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return set()
    return {
        str(item["id"]) for item in payload["data"] if isinstance(item, dict) and item.get("id")
    }
