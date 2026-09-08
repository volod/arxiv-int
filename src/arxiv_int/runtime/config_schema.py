"""The documented runtime variable registry: names, defaults and value rules."""

import re
from collections.abc import Mapping

from arxiv_int.runtime.inference_config import (
    OLLAMA_BASE_URL,
    SUPPORTED_BACKENDS,
    VLLM_DEFAULT_PORT,
)

SERVICE_PORTS = {
    "POSTGRES_PORT": "5432",
    "GRAFANA_PORT": "3000",
    "AGE_VIEWER_PORT": "3001",
    "PROMETHEUS_PORT": "9090",
    "CADVISOR_PORT": "8080",
    "VLLM_PORT": VLLM_DEFAULT_PORT,
}
DEFAULTS = {
    "DATA_DIR": ".data",
    "INFERENCE_BACKEND": SUPPORTED_BACKENDS[0],
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "console+jsonl",
    "OLLAMA_BASE_URL": OLLAMA_BASE_URL,
    "PIPELINE_PROFILE": "investigation",
    "POSTGRES_DB": "arxiv_int",
    "POSTGRES_USER": "arxiv_int",
    "PROGRESS_INTERVAL_SEC": "30",
    "SERVICE_PROFILES": "pipeline",
    "SETUP_DOWNLOADS": "1",
    **SERVICE_PORTS,
}
DERIVED_PATHS = {
    "RUNS_DIR": "runs",
    "SERVICE_STATE_DIR": "services",
    "MODEL_CACHE_DIR": "models",
    "TMP_DIR": "tmp",
}
PATH_NAMES = {
    "ARCHIVE_DIR",
    "RESULTS_DIR",
    "PGDATA_DIR",
    "PG_WAL_DIR",
    "DATA_DIR",
    *DERIVED_PATHS,
}
SCALAR_NAMES = {
    "DATABASE_URL",
    "POSTGRES_DB",
    "POSTGRES_PASSWORD",
    "POSTGRES_USER",
    "OLLAMA_BASE_URL",
    "INFERENCE_BACKEND",
    "EMBEDDING_MODEL",
    "GENERATION_MODEL",
    "GENERATION_MODEL_REVISION",
    "VLLM_MODEL",
    "VLLM_MODEL_REVISION",
    "RERANK_MODEL",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "PIPELINE_PROFILE",
    "SERVICE_PROFILES",
    "SETUP_DOWNLOADS",
    "PROGRESS_INTERVAL_SEC",
    "PIPELINE_WORKERS",
    "BATCH_SIZE",
    "GPU_MAX_CONCURRENCY",
    "VLLM_TENSOR_PARALLEL_SIZE",
    "VLLM_CPU_OFFLOAD_GB",
    "VLLM_GPU_MEMORY_UTILIZATION",
    "VLLM_MAX_MODEL_LEN",
    *SERVICE_PORTS,
}
DYNAMIC_PATH = re.compile(r"(?:ARCHIVE_SILO_[A-Z][A-Z0-9_]*|PG_TABLESPACE_[A-Z][A-Z0-9_]*)_DIR")
MAX_PORT = 65535


class ConfigurationError(ValueError):
    """A runtime configuration cannot be resolved safely."""


def selected(values: Mapping[str, str]) -> dict[str, str]:
    """Keep only the documented runtime variables, including the dynamic root families."""
    names = PATH_NAMES | SCALAR_NAMES
    return {
        name: value
        for name, value in values.items()
        if name in names or DYNAMIC_PATH.fullmatch(name)
    }


def apply_defaults(values: dict[str, str]) -> None:
    """Treat an explicitly empty value as a request for the documented default."""
    for name, default in DEFAULTS.items():
        if not values.get(name, "").strip():
            values[name] = default


def check_ports(values: Mapping[str, str]) -> None:
    """Refuse a service port that is not a TCP port number."""
    for name in sorted(SERVICE_PORTS):
        value = values[name].strip()
        if not value.isdigit() or not 1 <= int(value) <= MAX_PORT:
            raise ConfigurationError(f"{name} must be a TCP port between 1 and {MAX_PORT}")
