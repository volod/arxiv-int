"""Coordinator for retryable setup over independently callable phase handlers."""

import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.setup.adapters import SetupAdapters, production_adapters
from arxiv_int.runtime.setup.config_phase import run_config_phase
from arxiv_int.runtime.setup.dispatch import CONFIGURED_HANDLERS, env_result
from arxiv_int.runtime.setup.lock import (
    SetupLockError,
    exclusive_setup_lock,
    lock_identity,
    lock_path,
)
from arxiv_int.runtime.setup.model import (
    ATOMIC_PHASES,
    PHASE_ORDER,
    RETRY_COMMAND,
    PhaseName,
    PhaseResult,
    ProviderStatus,
    SetupReport,
)
from arxiv_int.runtime.setup.report import aggregate_status, persist_setup_report
from arxiv_int.runtime.setup.requirements import ProfileRequirements, resolve_requirements
from arxiv_int.runtime.setup.settings import (
    SetupSettings,
    effective_service_profiles,
    load_setup_settings,
)
from arxiv_int.runtime.setup.state import load_verified, store_verified

NEEDS_CONFIG = frozenset(PHASE_ORDER) - {"config", "env"}


def _attempt_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _next_action(phases: tuple[PhaseResult, ...], pipeline: ProviderStatus) -> str:
    failed = next((item for item in reversed(phases) if not item.ok), None)
    if failed is not None and failed.action:
        return failed.action
    if pipeline == "unavailable":
        return "infrastructure is ready; pipeline stages remain unimplemented"
    return RETRY_COMMAND if failed is not None else "setup complete"


def _phases_to_run(phase: str | None) -> tuple[PhaseName, ...]:
    if phase is None:
        return PHASE_ORDER
    if phase not in ATOMIC_PHASES:
        known = ", ".join(sorted(ATOMIC_PHASES))
        raise ValueError(f"unknown setup phase {phase!r}; expected {known}")
    return (ATOMIC_PHASES[phase],)


def run_setup(
    *,
    project_root: Path,
    phase: str | None = None,
    environment: Mapping[str, str] | None = None,
    adapters: SetupAdapters | None = None,
    settings: SetupSettings | None = None,
) -> SetupReport:
    """Run the aggregate coordinator or one atomic phase with shared policy."""
    active = adapters or production_adapters()
    resolved = settings or load_setup_settings(project_root=project_root, environment=environment)
    requirements = resolve_requirements(resolved, dict(environment or {}))
    names = _phases_to_run(phase)
    attempt = _attempt_id()
    merged = dict(os.environ)
    if environment is not None:
        merged.update(environment)
    data_dir = Path(str(merged.get("DATA_DIR") or project_root / ".data"))
    if not data_dir.is_absolute():
        data_dir = (project_root / data_dir).resolve()
    log_dir = data_dir / "setup" / attempt
    log_dir.mkdir(parents=True, exist_ok=True)
    verified = load_verified(data_dir)
    identity = lock_identity(
        project_root, str(data_dir), str(project_root), effective_service_profiles(resolved)
    )
    try:
        with exclusive_setup_lock(lock_path(data_dir, identity)):
            phases, config, pipeline = _run_phases(
                names, project_root, resolved, requirements, environment, active, verified, attempt
            )
    except SetupLockError as error:
        blocked = PhaseResult("config", "blocked", str(error), action=RETRY_COMMAND)
        phases, config, pipeline = (blocked,), None, "unavailable"
    store_verified(data_dir, verified)
    status = aggregate_status(phases)
    report = SetupReport(
        attempt,
        status,
        phases,
        infrastructure=status if status != "cancelled" else "blocked",
        pipeline_implementation=pipeline,
        next_action=_next_action(phases, pipeline),
        log_dir=log_dir,
    )
    path = persist_setup_report(report, config)
    return SetupReport(
        report.attempt_id,
        report.status,
        report.phases,
        report.infrastructure,
        report.pipeline_implementation,
        report.next_action,
        report.retry_command,
        path,
        log_dir,
    )


def _run_phases(
    names: tuple[PhaseName, ...],
    project_root: Path,
    settings: SetupSettings,
    requirements: ProfileRequirements,
    environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    attempt: str,
) -> tuple[tuple[PhaseResult, ...], RuntimeConfig | None, ProviderStatus]:
    results: list[PhaseResult] = []
    config: RuntimeConfig | None = None
    pipeline: ProviderStatus = "unavailable"
    profiles = requirements.service_profiles
    for name in names:
        if adapters.cancel():
            results.append(PhaseResult(name, "cancelled", "setup cancelled", action=RETRY_COMMAND))
            break
        result, config, pipeline = _one_phase(
            name,
            project_root,
            settings,
            requirements,
            environment,
            adapters,
            verified,
            config,
            attempt,
            profiles,
        )
        results.append(result)
        if result.fingerprint:
            verified[name] = result.fingerprint
        if not result.ok:
            break
    skipped = names[len(results) :]
    results.extend(
        PhaseResult(item, "skipped", "not run after a prior failure", action=RETRY_COMMAND)
        for item in skipped
    )
    return tuple(results), config, pipeline


def _one_phase(
    name: PhaseName,
    project_root: Path,
    settings: SetupSettings,
    requirements: ProfileRequirements,
    environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    config: RuntimeConfig | None,
    attempt: str,
    profiles: str,
) -> tuple[PhaseResult, RuntimeConfig | None, ProviderStatus]:
    pipeline: ProviderStatus = "unavailable"
    if name == "config":
        result, loaded = run_config_phase(
            project_root, which=adapters.which, environment=environment, verified=verified
        )
        return result, loaded or config, pipeline
    if name == "env":
        return env_result(project_root, settings, environment, adapters, verified), config, pipeline
    if config is None and name in NEEDS_CONFIG:
        loaded_result, loaded = run_config_phase(
            project_root, which=adapters.which, environment=environment, verified=verified
        )
        if loaded is None:
            return (
                PhaseResult(name, "blocked", loaded_result.detail, action=loaded_result.action),
                None,
                pipeline,
            )
        config = loaded
    if config is None:
        missing = PhaseResult(
            name,
            "blocked",
            "configuration is incomplete",
            action="edit .env, then " + RETRY_COMMAND,
        )
        return missing, config, pipeline
    handler = CONFIGURED_HANDLERS[name]
    result, pipeline = handler(
        project_root,
        settings,
        requirements,
        environment,
        adapters,
        verified,
        config,
        attempt,
        profiles,
    )
    return result, config, pipeline
