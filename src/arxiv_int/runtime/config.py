"""Layered, checkout-independent runtime configuration."""

import os
import re
from collections.abc import Mapping
from pathlib import Path

from arxiv_int.runtime.config_model import ArchiveSilo, RuntimeConfig
from arxiv_int.runtime.dotenv import DotenvError, read_dotenv
from arxiv_int.runtime.inference_config import resolve_inference_defaults

_DEFAULTS = {
    "DATA_DIR": ".data",
    "INFERENCE_BACKEND": "ollama",
    "LOG_LEVEL": "INFO",
    "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
    "POSTGRES_DB": "arxiv_int",
    "POSTGRES_USER": "arxiv_int",
}
_DERIVED_PATHS = {
    "RUNS_DIR": "runs",
    "SERVICE_STATE_DIR": "services",
    "MODEL_CACHE_DIR": "models",
    "TMP_DIR": "tmp",
}
_PATH_NAMES = {
    "ARCHIVE_DIR",
    "RESULTS_DIR",
    "PGDATA_DIR",
    "PROOF_ARCHIVE_DIR",
    "PG_WAL_DIR",
    "DATA_DIR",
    *_DERIVED_PATHS,
}
_SCALAR_NAMES = {
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
    "PROGRESS_INTERVAL_SEC",
    "PIPELINE_WORKERS",
    "BATCH_SIZE",
    "GPU_MAX_CONCURRENCY",
    "VLLM_TENSOR_PARALLEL_SIZE",
    "VLLM_CPU_OFFLOAD_GB",
    "VLLM_GPU_MEMORY_UTILIZATION",
    "VLLM_MAX_MODEL_LEN",
}
_DYNAMIC_PATH = re.compile(r"(?:ARCHIVE_SILO_[A-Z][A-Z0-9_]*|PG_TABLESPACE_[A-Z][A-Z0-9_]*)_DIR")
_REFERENCE = re.compile(r"\$(?:\{([A-Z][A-Z0-9_]*)\}|([A-Z][A-Z0-9_]*))")


class ConfigurationError(ValueError):
    """A runtime configuration cannot be resolved safely."""


def merge_config_layers(
    defaults: Mapping[str, str],
    dotenv: Mapping[str, str | None],
    environment: Mapping[str, str],
    cli: Mapping[str, str | None],
) -> dict[str, str]:
    """Merge configuration from lowest to highest precedence."""
    merged = dict(defaults)
    for layer in (dotenv, environment, cli):
        merged.update({key: value for key, value in layer.items() if value is not None})
    return merged


def _project_root(root: Path | None) -> Path:
    if root is not None:
        candidate = root.resolve()
        if (candidate / "pyproject.toml").is_file():
            return candidate
        raise ConfigurationError(f"PROJECT_ROOT is not a checkout: {candidate}")
    for start in (Path.cwd(), Path(__file__).resolve()):
        for candidate in (start, *start.parents):
            if (candidate / "pyproject.toml").is_file():
                return candidate
    raise ConfigurationError("cannot find project root; pass an explicit project_root")


def _selected(values: Mapping[str, str]) -> dict[str, str]:
    names = _PATH_NAMES | _SCALAR_NAMES
    return {
        name: value
        for name, value in values.items()
        if name in names or _DYNAMIC_PATH.fullmatch(name)
    }


def _expand(value: str, values: Mapping[str, str], variable: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        replacement = values.get(name, "")
        if not replacement:
            raise ConfigurationError(f"{variable} references missing {name}")
        return replacement

    return _REFERENCE.sub(replace, value)


def _resolve_path(value: str, values: Mapping[str, str], name: str, root: Path) -> Path:
    expanded = Path(_expand(value, values, name)).expanduser()
    return (expanded if expanded.is_absolute() else root / expanded).resolve()


def _optional_path(
    values: Mapping[str, str], name: str, root: Path, *, fallback: Path | None = None
) -> Path | None:
    value = values.get(name, "").strip()
    return _resolve_path(value, values, name, root) if value else fallback


def _require_operator_roots(values: Mapping[str, str]) -> tuple[str, ...]:
    named = tuple(
        sorted(
            name
            for name, value in values.items()
            if name.startswith("ARCHIVE_SILO_") and value.strip()
        )
    )
    missing = (
        []
        if values.get("ARCHIVE_DIR", "").strip() or named
        else ["ARCHIVE_DIR (or ARCHIVE_SILO_<ID>_DIR)"]
    )
    missing.extend(
        name for name in ("RESULTS_DIR", "PGDATA_DIR") if not values.get(name, "").strip()
    )
    if missing:
        raise ConfigurationError("missing required configuration: " + ", ".join(missing))
    return named


def _resolve_silos(
    values: Mapping[str, str], names: tuple[str, ...], root: Path
) -> tuple[ArchiveSilo, ...]:
    silos = []
    if values.get("ARCHIVE_DIR", "").strip():
        path = _resolve_path(values["ARCHIVE_DIR"], values, "ARCHIVE_DIR", root)
        silos.append(ArchiveSilo("default", "ARCHIVE_DIR", path))
    for name in names:
        silo_id = name.removeprefix("ARCHIVE_SILO_").removesuffix("_DIR")
        path = _resolve_path(values[name], values, name, root)
        silos.append(ArchiveSilo(silo_id.lower().replace("_", "-"), name, path))
    return tuple(silos)


def _resolve_tablespaces(values: Mapping[str, str], root: Path) -> tuple[tuple[str, Path], ...]:
    return tuple(
        (
            name.removeprefix("PG_TABLESPACE_").removesuffix("_DIR").lower(),
            _resolve_path(value, values, name, root),
        )
        for name, value in sorted(values.items())
        if name.startswith("PG_TABLESPACE_") and value.strip()
    )


def load_runtime_config(
    *,
    project_root: Path | None = None,
    environment: Mapping[str, str] | None = None,
    cli: Mapping[str, str | None] | None = None,
    dotenv_path: Path | None = None,
) -> RuntimeConfig:
    """Load CLI > environment > .env > defaults and resolve every runtime path."""
    root = _project_root(project_root)
    try:
        dotenv = read_dotenv(dotenv_path or root / ".env")
    except DotenvError as error:
        raise ConfigurationError(str(error)) from error
    environment_values = _selected(os.environ if environment is None else environment)
    values = merge_config_layers(_DEFAULTS, dotenv, environment_values, cli or {})
    values = _selected(values)
    resolve_inference_defaults(values)

    named_silos = _require_operator_roots(values)
    results = _resolve_path(values["RESULTS_DIR"], values, "RESULTS_DIR", root)
    for name, suffix in _DERIVED_PATHS.items():
        if not values.get(name, "").strip():
            values[name] = str(results / suffix)

    silos = _resolve_silos(values, named_silos, root)
    tablespaces = _resolve_tablespaces(values, root)
    path_values = {
        name: _resolve_path(values[name], values, name, root)
        for name in ("RESULTS_DIR", "PGDATA_DIR", *_DERIVED_PATHS)
    }
    resolved_values = dict(values)
    for silo in silos:
        resolved_values[silo.variable] = str(silo.root)
    for name, path in path_values.items():
        resolved_values[name] = str(path)
    for name in ("PROOF_ARCHIVE_DIR", "PG_WAL_DIR", "DATA_DIR"):
        optional = _optional_path(values, name, root)
        if optional is not None:
            resolved_values[name] = str(optional)
    for name, path in tablespaces:
        resolved_values[f"PG_TABLESPACE_{name.upper()}_DIR"] = str(path)
    proof_archive = _optional_path(values, "PROOF_ARCHIVE_DIR", root)
    return RuntimeConfig(
        project_root=root,
        archive_silos=tuple(silos),
        results_dir=path_values["RESULTS_DIR"],
        pgdata_dir=path_values["PGDATA_DIR"],
        runs_dir=path_values["RUNS_DIR"],
        service_state_dir=path_values["SERVICE_STATE_DIR"],
        model_cache_dir=path_values["MODEL_CACHE_DIR"],
        tmp_dir=path_values["TMP_DIR"],
        proof_archive_dir=proof_archive,
        pg_wal_dir=_optional_path(values, "PG_WAL_DIR", root),
        pg_tablespaces=tablespaces,
        data_dir=_resolve_path(values["DATA_DIR"], values, "DATA_DIR", root),
        values=tuple(sorted(resolved_values.items())),
    )
