"""Validated Docker Compose orchestration for operator services."""

import json
import logging
import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Literal

from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.paths import create_results_layout, validate_runtime_paths
from arxiv_int.runtime.service_reset import ServiceResetError, reset_service_data

ComposeAction = Literal["config", "down", "logs", "reset", "status", "up"]
ComposeRunner = Callable[[tuple[str, ...], Path, Mapping[str, str]], int]

SUPPORTED_PROFILES = ("core", "graph", "ui", "observability", "vllm", "cadvisor")
PROFILE_ALIASES = {"pipeline": ("core", "ui", "observability")}
_STATE_SERVICES = ("age-viewer", "grafana", "prometheus")
_DATABASE_PROFILES = frozenset(("core", "graph", "ui", "observability"))
_LOG = logging.getLogger(__name__)


class ComposeConfigurationError(ValueError):
    """An operator Compose request cannot be formed safely."""


def parse_profiles(value: str | Sequence[str]) -> tuple[str, ...]:
    """Normalize comma- or whitespace-separated profile names in declared order."""
    raw = value.split() if isinstance(value, str) else value
    requested = {profile for item in raw for profile in item.replace(",", " ").split() if profile}
    if not requested:
        requested = {"pipeline"}
    unknown = sorted(requested.difference((*SUPPORTED_PROFILES, *PROFILE_ALIASES)))
    if unknown:
        raise ComposeConfigurationError("unknown Compose profile(s): " + ", ".join(unknown))
    for alias in requested.intersection(PROFILE_ALIASES):
        requested.update(PROFILE_ALIASES[alias])
        requested.remove(alias)
    return tuple(profile for profile in SUPPORTED_PROFILES if profile in requested)


def compose_environment(
    config: RuntimeConfig, *, base: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Build an in-memory Compose environment with absolute validated host paths."""
    environment = dict(os.environ if base is None else base)
    environment.update(config.values)
    if environment["INFERENCE_BACKEND"].lower() == "vllm":
        environment["VLLM_MODEL"] = environment["GENERATION_MODEL"]
        environment["VLLM_MODEL_REVISION"] = environment["GENERATION_MODEL_REVISION"]
    environment.update(
        {
            "PROJECT_ROOT": str(config.project_root),
            "RUNTIME_GID": str(os.getgid()),
            "RUNTIME_UID": str(os.getuid()),
            "AGE_VIEWER_STATE_DIR": str(config.service_state_dir / "age-viewer"),
            "GRAFANA_STATE_DIR": str(config.service_state_dir / "grafana"),
            "PROMETHEUS_STATE_DIR": str(config.service_state_dir / "prometheus"),
        }
    )
    return environment


def prepare_service_layout(config: RuntimeConfig) -> tuple[Path, ...]:
    """Validate service roots and create the runtime and per-service state directories."""
    service_config = replace(config, proof_archive_dir=None)
    validation = validate_runtime_paths(service_config)
    created = list(create_results_layout(config, validation))
    for service in _STATE_SERVICES:
        state_dir = config.service_state_dir / service
        state_dir.mkdir(parents=True, exist_ok=True)
        created.append(state_dir)
    return tuple(created)


def _database_mounts(config: RuntimeConfig) -> list[dict[str, object]]:
    mounts: list[dict[str, object]] = []
    if config.pg_wal_dir is not None:
        mounts.append(
            {
                "type": "bind",
                "source": str(config.pg_wal_dir),
                "target": "/var/lib/postgresql/wal",
            }
        )
    mounts.extend(
        {
            "type": "bind",
            "source": str(path),
            "target": f"/var/lib/postgresql/tablespaces/{name}",
        }
        for name, path in config.pg_tablespaces
    )
    return mounts


def _write_mount_override(config: RuntimeConfig) -> Path | None:
    mounts = _database_mounts(config)
    if not mounts:
        return None
    config.data_dir.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=config.data_dir, prefix="compose-mounts-", suffix=".json", text=True
    )
    path = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"services": {"database": {"volumes": mounts}}}, stream)
            stream.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def compose_command(
    config: RuntimeConfig,
    action: ComposeAction,
    profiles: Sequence[str],
    *,
    override: Path | None = None,
    services: Sequence[str] = (),
    follow: bool = False,
    tail: int = 200,
) -> tuple[str, ...]:
    """Return one stable Docker Compose command without shell interpolation."""
    if tail < 0:
        raise ComposeConfigurationError("log tail must be zero or greater")
    command = [
        "docker",
        "compose",
        "--project-directory",
        str(config.project_root),
        "--env-file",
        str(config.project_root / ".env"),
        "--file",
        str(config.project_root / "docker/compose.yaml"),
    ]
    if override is not None:
        command.extend(("--file", str(override)))
    for profile in profiles:
        command.extend(("--profile", profile))
    if action == "config":
        command.extend(("config", "--quiet"))
    elif action == "up":
        command.extend(("up", "--detach", "--remove-orphans", "--wait"))
    elif action == "down":
        command.extend(("down", "--remove-orphans", "--timeout", "60"))
    elif action == "status":
        command.extend(("ps", "--all"))
    else:
        command.extend(("logs", "--no-color", "--tail", str(tail)))
        if follow:
            command.append("--follow")
        command.extend(services)
    return tuple(command)


def _subprocess_runner(command: tuple[str, ...], cwd: Path, environment: Mapping[str, str]) -> int:
    completed = subprocess.run(command, cwd=cwd, env=environment, check=False)
    return completed.returncode


def run_compose(
    config: RuntimeConfig,
    action: ComposeAction,
    profiles: str | Sequence[str],
    *,
    services: Sequence[str] = (),
    follow: bool = False,
    tail: int = 200,
    apply: bool = False,
    runner: ComposeRunner = _subprocess_runner,
) -> int:
    """Preflight mutating requests and run Docker Compose with secrets only in memory."""
    selected = parse_profiles(profiles)
    password = dict(config.values).get("POSTGRES_PASSWORD", "")
    if action == "up" and _DATABASE_PROFILES.intersection(selected) and not password:
        raise ComposeConfigurationError(
            "set POSTGRES_PASSWORD in .env before starting the database"
        )
    if action == "reset":
        down_status = runner(
            compose_command(config, "down", selected),
            config.project_root,
            compose_environment(config),
        )
        if down_status != 0:
            return down_status
        try:
            targets = reset_service_data(config, apply=apply)
        except ServiceResetError as error:
            raise ComposeConfigurationError(str(error)) from error
        _LOG.info(
            "services reset %s for %d data root(s)",
            "applied" if apply else "planned",
            len(targets),
        )
        return 0
    needs_layout = action in {"config", "up"}
    if needs_layout:
        prepare_service_layout(config)
    override = _write_mount_override(config) if needs_layout else None
    try:
        command = compose_command(
            config,
            action,
            selected,
            override=override,
            services=services,
            follow=follow,
            tail=tail,
        )
        return runner(command, config.project_root, compose_environment(config))
    finally:
        if override is not None:
            override.unlink(missing_ok=True)
