"""Validated Docker Compose orchestration for operator services."""

import json
import logging
import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Literal

from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.host_identity import host_gid, host_uid
from arxiv_int.runtime.paths import create_results_layout, validate_runtime_paths
from arxiv_int.runtime.service_plan import (
    PROFILE_ALIASES as PROFILE_ALIASES,
)
from arxiv_int.runtime.service_plan import (
    STATE_SERVICES,
    ServicePlan,
    plan_services,
    require_graph_age,
)
from arxiv_int.runtime.service_plan import (
    SUPPORTED_PROFILES as SUPPORTED_PROFILES,
)
from arxiv_int.runtime.service_plan import (
    ComposeConfigurationError as ComposeConfigurationError,
)
from arxiv_int.runtime.service_plan import (
    parse_profiles as parse_profiles,
)
from arxiv_int.runtime.service_reset import (
    ServiceResetError,
    reset_service_data,
    validate_service_reset,
)

ComposeAction = Literal["config", "down", "logs", "reset", "status", "up"]
ComposeRunner = Callable[[tuple[str, ...], Path, Mapping[str, str]], int]

_LOG = logging.getLogger(__name__)


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
            "COMPOSE_PROFILES": "",
            "RUNTIME_GID": str(host_gid()),
            "RUNTIME_UID": str(host_uid()),
            "AGE_VIEWER_STATE_DIR": str(config.service_state_dir / "age-viewer"),
            "GRAFANA_STATE_DIR": str(config.service_state_dir / "grafana"),
            "PROMETHEUS_STATE_DIR": str(config.service_state_dir / "prometheus"),
        }
    )
    return environment


def prepare_service_layout(
    config: RuntimeConfig, plan: ServicePlan | None = None
) -> tuple[Path, ...]:
    """Validate service roots and create the runtime and per-service state directories."""
    selected = plan or plan_services("pipeline", project_root=config.project_root)
    variables = selected.path_variables(config)
    validation = validate_runtime_paths(config, variables=variables)
    created = list(create_results_layout(config, validation, variables=variables))
    for service in (name for name in STATE_SERVICES if name in selected.services):
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


def compose_base_command(
    config: RuntimeConfig, profiles: Sequence[str], *, override: Path | None = None
) -> tuple[str, ...]:
    """Build only global Compose arguments, without an action or filesystem writes."""
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
    for profile in parse_profiles(profiles):
        command.extend(("--profile", profile))
    return tuple(command)


def compose_command(
    config: RuntimeConfig,
    action: ComposeAction,
    profiles: Sequence[str],
    *,
    override: Path | None = None,
    services: Sequence[str] = (),
    follow: bool = False,
    tail: int = 200,
    pull: str | None = None,
) -> tuple[str, ...]:
    """Return one stable Docker Compose command without shell interpolation."""
    if tail < 0:
        raise ComposeConfigurationError("log tail must be zero or greater")
    if pull is not None and pull not in {"always", "missing", "never"}:
        raise ComposeConfigurationError("unsupported Compose pull policy")
    plan = plan_services(profiles, project_root=config.project_root)
    if action not in {"config", "up", "down", "status", "logs"}:
        raise ComposeConfigurationError("unsupported Compose command action")
    if any(service not in plan.services for service in services):
        raise ComposeConfigurationError("log services must belong to selected profiles")
    command = list(compose_base_command(config, plan.profiles, override=override))
    if action == "config":
        command.extend(("config", "--quiet"))
    elif action == "up":
        command.extend(("up", "--detach", "--remove-orphans", "--wait"))
        if pull is not None:
            command.extend(("--pull", pull))
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


def _run_reset(
    config: RuntimeConfig, selected: tuple[str, ...], apply: bool, runner: ComposeRunner
) -> int:
    """Preserve the existing project-wide reset validation and execution policy."""
    try:
        validate_service_reset(config)
    except ServiceResetError as error:
        raise ComposeConfigurationError(str(error)) from error
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


def run_compose(
    config: RuntimeConfig,
    action: ComposeAction,
    profiles: str | Sequence[str],
    *,
    services: Sequence[str] = (),
    follow: bool = False,
    tail: int = 200,
    apply: bool = False,
    pull: str | None = None,
    runner: ComposeRunner = _subprocess_runner,
) -> int:
    """Preflight mutating requests and run Docker Compose with secrets only in memory."""
    plan = plan_services(profiles, project_root=config.project_root)
    selected = plan.profiles
    if action != "reset":
        compose_command(
            config, action, selected, services=services, follow=follow, tail=tail, pull=pull
        )
    password = dict(config.values).get("POSTGRES_PASSWORD", "")
    if action == "up" and plan.database and not password:
        raise ComposeConfigurationError(
            "set POSTGRES_PASSWORD in .env before starting the database"
        )
    if action == "up":
        require_graph_age(plan)
    if action == "reset":
        return _run_reset(config, selected, apply, runner)
    needs_layout = action in {"config", "up"}
    if needs_layout:
        prepare_service_layout(config, plan)
    override = _write_mount_override(config) if needs_layout and plan.database else None
    try:
        command = compose_command(
            config,
            action,
            selected,
            override=override,
            services=services,
            follow=follow,
            tail=tail,
            pull=pull,
        )
        return runner(command, config.project_root, compose_environment(config))
    finally:
        if override is not None:
            override.unlink(missing_ok=True)
