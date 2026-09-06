"""Read-only readiness checks for a configured local workstation."""

import json
import platform
import sys
from pathlib import Path

from arxiv_int.readiness.probes import CommandResult, Probe
from arxiv_int.readiness.report import CheckStatus, PreflightReport
from arxiv_int.runtime.compose import PROFILE_ALIASES, compose_command, compose_environment
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.service_plan import plan_services

_GIB = 1024**3
_MINIMUM_PYTHON = (3, 12)
_PLACEHOLDER_PASSWORDS = frozenset(
    {"changeme", "compose-validation-only", "password", "postgres", "replace-me"}
)


def check_tools(report: PreflightReport, probe: Probe, root: Path, timeout: float) -> None:
    """Check the required command-line tools and their responsive entry points."""
    version = platform.python_version()
    status: CheckStatus = "ready" if sys.version_info >= _MINIMUM_PYTHON else "blocked"
    action = None if status == "ready" else "make bootstrap PYTHON_VERSION=3.12"
    report.add("tool.python", status, f"Python {version}", action=action)
    commands = {
        "git": ("git", "--version"),
        "make": ("make", "--version"),
        "uv": ("uv", "--version"),
        "docker": ("docker", "version", "--format", "{{.Client.Version}}"),
        "compose": ("docker", "compose", "version", "--short"),
    }
    for name, command in commands.items():
        if probe.which(command[0]) is None:
            report.add(
                f"tool.{name}",
                "blocked",
                f"{command[0]} is not installed",
                action=f"install {name if name != 'compose' else 'Docker Compose'}",
            )
            continue
        result = probe.run(command, cwd=root, timeout=timeout)
        _command_finding(report, f"tool.{name}", result, command)


def check_resources(
    report: PreflightReport,
    probe: Probe,
    root: Path,
    timeout: float,
    *,
    require_gpu: bool = False,
) -> None:
    """Record host RAM and NVIDIA GPU evidence without forecasting capacity."""
    memory = probe.memory_bytes()
    if memory is None:
        report.add("resource.ram", "degraded", "total RAM could not be measured")
    else:
        report.add("resource.ram", "ready", f"{memory / _GIB:.1f} GiB total RAM detected")
    if probe.which("nvidia-smi") is None:
        report.add(
            "resource.gpu",
            "blocked" if require_gpu else "ready",
            "no NVIDIA utility detected; CPU execution remains usable",
            action="install and verify the NVIDIA container runtime" if require_gpu else None,
        )
        return
    result = probe.run(
        (
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free",
            "--format=csv,noheader,nounits",
        ),
        cwd=root,
        timeout=timeout,
    )
    _command_finding(
        report,
        "resource.gpu",
        result,
        ("nvidia-smi",),
        degraded=not require_gpu,
    )


def check_password(report: PreflightReport, config: RuntimeConfig) -> None:
    """Reject an absent or obvious database placeholder without revealing it."""
    password = dict(config.values).get("POSTGRES_PASSWORD", "").strip()
    if not password or password.lower() in _PLACEHOLDER_PASSWORDS:
        report.add(
            "config.POSTGRES_PASSWORD",
            "blocked",
            "database password is absent or a known placeholder",
            action="set POSTGRES_PASSWORD to a local secret in .env",
        )
    else:
        report.add(
            "config.POSTGRES_PASSWORD", "ready", "database password is configured and masked"
        )


def check_services(
    report: PreflightReport,
    config: RuntimeConfig,
    profiles: tuple[str, ...],
    probe: Probe,
    timeout: float,
) -> bool:
    """Report Compose service state and return whether the database is healthy."""
    if probe.which("docker") is None:
        report.add("services", "degraded", "service health unavailable because Docker is missing")
        return False
    command = (*compose_command(config, "status", profiles), "--format", "json")
    result = probe.run(
        command,
        cwd=config.project_root,
        environment=compose_environment(config),
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = (
            "service health probe timed out"
            if result.timed_out
            else "Docker service state unavailable"
        )
        report.add("services", "degraded", detail, action="start Docker, then run make readiness")
        return False
    states = _service_states(result.stdout)
    plan = plan_services(profiles)
    expected = plan.services
    profile_value = " ".join(profiles)
    start_action = (
        "make services-up"
        if profiles == PROFILE_ALIASES["pipeline"]
        else f'make services-up SERVICE_PROFILES="{profile_value}"'
    )
    for name in expected:
        state, health = states.get(name, ("absent", ""))
        ready = state.lower() == "running" and health.lower() in {"", "healthy"}
        report.add(
            f"service.{name}",
            "ready" if ready else "degraded",
            f"state={state}, health={health or 'not-reported'}",
            action=None if ready else start_action,
        )
    database = states.get("database", ("", ""))
    return plan.database and database[0].lower() == "running" and database[1].lower() == "healthy"


def _command_finding(
    report: PreflightReport,
    name: str,
    result: CommandResult,
    command: tuple[str, ...],
    *,
    degraded: bool = False,
) -> None:
    if result.returncode == 0:
        detail = next(
            (line.strip() for line in result.stdout.splitlines() if line.strip()), "available"
        )
        report.add(name, "ready", detail)
        return
    status: CheckStatus = "degraded" if degraded else "blocked"
    detail = "probe timed out" if result.timed_out else f"probe exited {result.returncode}"
    report.add(name, status, detail, action="check " + " ".join(command))


def _service_states(raw: str) -> dict[str, tuple[str, str]]:
    states: dict[str, tuple[str, str]] = {}
    for item in _json_objects(raw):
        if not isinstance(item, dict):
            continue
        name = str(item.get("Service") or item.get("Name") or "")
        if name:
            states[name] = (str(item.get("State") or "unknown"), str(item.get("Health") or ""))
    return states


def _json_objects(raw: str) -> list[object]:
    if not raw.strip():
        return []
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        objects: list[object] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                objects.append(json.loads(line))
            except json.JSONDecodeError:
                return []
        return objects
    return decoded if isinstance(decoded, list) else [decoded]
