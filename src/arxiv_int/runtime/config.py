"""Layered, checkout-independent runtime configuration."""

import os
from collections.abc import Mapping
from pathlib import Path

from arxiv_int.runtime.config_model import ArchiveSilo, RuntimeConfig
from arxiv_int.runtime.config_schema import (
    DEFAULTS,
    DERIVED_PATHS,
    ConfigurationError,
    apply_defaults,
    check_ports,
    selected,
)
from arxiv_int.runtime.dotenv import DotenvError, expand_references, read_dotenv
from arxiv_int.runtime.inference_config import resolve_inference_defaults
from arxiv_int.runtime.project_root import ProjectRootError, find_project_root

__all__ = ["ConfigurationError", "load_runtime_config", "merge_config_layers"]


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


def _resolve_path(value: str, name: str, root: Path) -> Path:
    expanded = Path(value).expanduser()
    if not str(expanded).strip():
        raise ConfigurationError(f"{name} resolves to an empty path")
    return (expanded if expanded.is_absolute() else root / expanded).resolve()


def _optional_path(
    values: Mapping[str, str], name: str, root: Path, *, fallback: Path | None = None
) -> Path | None:
    value = values.get(name, "").strip()
    return _resolve_path(value, name, root) if value else fallback


def _silo_variables(values: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name, value in values.items()
            if name.startswith("ARCHIVE_SILO_") and value.strip()
        )
    )


def _require_operator_roots(values: Mapping[str, str]) -> None:
    missing = (
        []
        if values.get("ARCHIVE_DIR", "").strip() or _silo_variables(values)
        else ["ARCHIVE_DIR (or ARCHIVE_SILO_<ID>_DIR)"]
    )
    missing.extend(
        name for name in ("RESULTS_DIR", "PGDATA_DIR") if not values.get(name, "").strip()
    )
    if missing:
        raise ConfigurationError("missing required configuration: " + ", ".join(missing))


def _resolve_silos(values: Mapping[str, str], root: Path) -> tuple[ArchiveSilo, ...]:
    silos = []
    if values.get("ARCHIVE_DIR", "").strip():
        path = _resolve_path(values["ARCHIVE_DIR"], "ARCHIVE_DIR", root)
        silos.append(ArchiveSilo("default", "ARCHIVE_DIR", path))
    for name in _silo_variables(values):
        silo_id = name.removeprefix("ARCHIVE_SILO_").removesuffix("_DIR")
        silos.append(
            ArchiveSilo(
                silo_id.lower().replace("_", "-"), name, _resolve_path(values[name], name, root)
            )
        )
    return tuple(silos)


def _resolve_tablespaces(values: Mapping[str, str], root: Path) -> tuple[tuple[str, Path], ...]:
    return tuple(
        (
            name.removeprefix("PG_TABLESPACE_").removesuffix("_DIR").lower(),
            _resolve_path(value, name, root),
        )
        for name, value in sorted(values.items())
        if name.startswith("PG_TABLESPACE_") and value.strip()
    )


def _resolved_values(
    values: Mapping[str, str],
    silos: tuple[ArchiveSilo, ...],
    paths: Mapping[str, Path],
    tablespaces: tuple[tuple[str, Path], ...],
    root: Path,
) -> dict[str, str]:
    resolved = dict(values)
    for silo in silos:
        resolved[silo.variable] = str(silo.root)
    for name, path in paths.items():
        resolved[name] = str(path)
    for name in ("PG_WAL_DIR", "DATA_DIR"):
        optional = _optional_path(values, name, root)
        if optional is not None:
            resolved[name] = str(optional)
    for name, path in tablespaces:
        resolved[f"PG_TABLESPACE_{name.upper()}_DIR"] = str(path)
    return resolved


def _merged_values(
    root: Path,
    environment: Mapping[str, str] | None,
    cli: Mapping[str, str | None] | None,
    dotenv_path: Path | None,
) -> dict[str, str]:
    """Apply precedence, documented defaults and reference expansion in that order."""
    try:
        dotenv = read_dotenv(dotenv_path or root / ".env")
    except DotenvError as error:
        raise ConfigurationError(str(error)) from error
    environment_values = selected(os.environ if environment is None else environment)
    values = selected(merge_config_layers(DEFAULTS, dotenv, environment_values, cli or {}))
    apply_defaults(values)
    check_ports(values)
    resolve_inference_defaults(values)
    _require_operator_roots(values)
    for name, suffix in DERIVED_PATHS.items():
        if not values.get(name, "").strip():
            values[name] = f"${{RESULTS_DIR}}/{suffix}"
    try:
        return expand_references(values)
    except DotenvError as error:
        raise ConfigurationError(str(error)) from error


def load_runtime_config(
    *,
    project_root: Path | None = None,
    environment: Mapping[str, str] | None = None,
    cli: Mapping[str, str | None] | None = None,
    dotenv_path: Path | None = None,
) -> RuntimeConfig:
    """Load CLI > environment > .env > defaults and resolve every runtime path."""
    try:
        root = find_project_root(project_root, environment)
    except ProjectRootError as error:
        raise ConfigurationError(str(error)) from error
    values = _merged_values(root, environment, cli, dotenv_path)
    silos = _resolve_silos(values, root)
    tablespaces = _resolve_tablespaces(values, root)
    paths = {
        name: _resolve_path(values[name], name, root)
        for name in ("RESULTS_DIR", "PGDATA_DIR", *DERIVED_PATHS)
    }
    return RuntimeConfig(
        project_root=root,
        archive_silos=silos,
        results_dir=paths["RESULTS_DIR"],
        pgdata_dir=paths["PGDATA_DIR"],
        runs_dir=paths["RUNS_DIR"],
        service_state_dir=paths["SERVICE_STATE_DIR"],
        model_cache_dir=paths["MODEL_CACHE_DIR"],
        tmp_dir=paths["TMP_DIR"],
        pg_wal_dir=_optional_path(values, "PG_WAL_DIR", root),
        pg_tablespaces=tablespaces,
        data_dir=_resolve_path(values["DATA_DIR"], "DATA_DIR", root),
        values=tuple(sorted(_resolved_values(values, silos, paths, tablespaces, root).items())),
    )
