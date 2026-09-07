"""Package, path, service, contract, and readiness phases over existing handlers."""

import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from subprocess import CompletedProcess

from arxiv_int.readiness.probes import Probe
from arxiv_int.readiness.run import run_readiness
from arxiv_int.runtime.compose import run_compose
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.setup.model import (
    RETRY_COMMAND,
    PhaseResult,
    ProviderStatus,
    reused_or_ready,
)
from arxiv_int.runtime.setup.requirements import ProfileRequirements
from arxiv_int.runtime.setup.state import fingerprint_for

CommandRunner = Callable[..., CompletedProcess[str]]


def _subprocess_env(environment: Mapping[str, str] | None) -> dict[str, str]:
    values = dict(os.environ)
    if environment is not None:
        values.update(environment)
    return values


def run_package_phase(
    project_root: Path,
    *,
    runner: CommandRunner,
    environment: Mapping[str, str] | None = None,
    verified: dict[str, str] | None = None,
) -> PhaseResult:
    """Verify the installed package identity."""
    executable = project_root / ".venv" / "bin" / "arxiv-int"
    if not executable.is_file():
        return PhaseResult(
            "package", "blocked", "package is not installed", action="make setup-env"
        )
    completed = runner(
        (str(executable), "info"), cwd=project_root, env=_subprocess_env(environment)
    )
    if completed.returncode != 0:
        return PhaseResult(
            "package", "blocked", "package identity check failed", action="make setup-env"
        )
    detail = completed.stdout.strip() or "package identity ok"
    digest = fingerprint_for(detail)
    return PhaseResult(
        "package",
        reused_or_ready(verified, "package", digest),
        detail,
        fingerprint=digest,
    )


def run_paths_phase(
    config: RuntimeConfig,
    profiles: str | Sequence[str],
    *,
    compose: Callable[..., int] = run_compose,
    verified: dict[str, str] | None = None,
) -> PhaseResult:
    """Validate Compose and create only the selected safe roots."""
    status_code = compose(config, "config", profiles)
    if status_code != 0:
        return PhaseResult(
            "paths",
            "blocked",
            "Compose configuration or path preflight failed",
            action="edit .env roots, then " + RETRY_COMMAND,
        )
    digest = fingerprint_for(str(config.results_dir), str(config.pgdata_dir))
    return PhaseResult(
        "paths",
        reused_or_ready(verified, "paths", digest),
        "safe roots and Compose configuration validated",
        fingerprint=digest,
    )


def run_services_phase(
    config: RuntimeConfig,
    profiles: str | Sequence[str],
    *,
    downloads: bool,
    compose: Callable[..., int] = run_compose,
) -> PhaseResult:
    """Start selected services; never implicit-pull in offline mode."""
    pull = None if downloads else "never"
    status_code = compose(config, "up", profiles, pull=pull)
    if status_code != 0:
        return PhaseResult(
            "services",
            "blocked",
            "service start failed",
            action="make services-status, then " + RETRY_COMMAND,
        )
    return PhaseResult("services", "ready", "selected services started")


def run_contracts_phase(
    project_root: Path,
    *,
    runner: CommandRunner,
    environment: Mapping[str, str] | None = None,
    verified: dict[str, str] | None = None,
) -> PhaseResult:
    """Run shipped contract, revision, and ontology checks without repeating uv sync."""
    executable = project_root / ".venv" / "bin" / "arxiv-int"
    env = _subprocess_env(environment)
    commands = (
        ((str(executable), "contracts", "check"), "contracts"),
        ((str(executable), "db", "check"), "db"),
        ((str(executable), "ontology", "check"), "ontology"),
    )
    details: list[str] = []
    for command, label in commands:
        completed = runner(command, cwd=project_root, env=env)
        if completed.returncode != 0:
            return PhaseResult(
                "contracts",
                "blocked",
                f"{label} check failed",
                action=f"make {label}-check",
            )
        details.append(label)
    digest = fingerprint_for(*details)
    return PhaseResult(
        "contracts",
        reused_or_ready(verified, "contracts", digest),
        "contract, revision, and ontology checks passed",
        fingerprint=digest,
    )


def run_readiness_phase(
    config: RuntimeConfig,
    profiles: str,
    requirements: ProfileRequirements,
    *,
    probe: Probe,
    persist: bool = True,
    environment: Mapping[str, str] | None = None,
) -> tuple[PhaseResult, ProviderStatus]:
    """Re-probe readiness; missing mandatory providers stay unavailable."""
    result = run_readiness(
        project_root=config.project_root,
        environment=environment,
        profiles=profiles,
        probe=probe,
        persist=persist,
    )
    pipeline: ProviderStatus = "unavailable" if requirements.unimplemented_stages else "ready"
    if requirements.missing_providers:
        pipeline = "unavailable"
    if result.report.status == "blocked":
        finding = next(item for item in result.report.findings if item.status == "blocked")
        return (
            PhaseResult("readiness", "blocked", finding.detail, action=finding.action),
            pipeline,
        )
    if result.report.status == "degraded":
        finding = next(item for item in result.report.findings if item.status == "degraded")
        return (
            PhaseResult("readiness", "degraded", finding.detail, action=finding.action),
            pipeline,
        )
    return (
        PhaseResult("readiness", "ready", "readiness probes passed"),
        pipeline,
    )
