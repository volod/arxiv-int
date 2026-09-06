"""Per-phase setup dispatch kept as one-function handlers."""

import os
from collections.abc import Mapping
from pathlib import Path

from arxiv_int.contracts.migrations.runner import DATABASE_URL_VARIABLE
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.setup.adapters import SetupAdapters
from arxiv_int.runtime.setup.env_phase import run_env_phase
from arxiv_int.runtime.setup.images import run_images_phase, run_postgres_image_phase
from arxiv_int.runtime.setup.model import PhaseResult, ProviderStatus
from arxiv_int.runtime.setup.models import run_models_phase
from arxiv_int.runtime.setup.requirements import ProfileRequirements
from arxiv_int.runtime.setup.schema import run_schema_phase
from arxiv_int.runtime.setup.settings import SetupSettings
from arxiv_int.runtime.setup.support import (
    run_contracts_phase,
    run_package_phase,
    run_paths_phase,
    run_readiness_phase,
    run_services_phase,
)
from arxiv_int.runtime.setup.wait import run_wait_phase


def env_result(
    project_root: Path,
    settings: SetupSettings,
    environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
) -> PhaseResult:
    """Sync the locked extra union."""
    return run_env_phase(
        project_root,
        downloads=settings.downloads,
        runner=adapters.run,
        extras=settings.extras,
        environment=environment,
        verified=verified,
    )


def _package(
    project_root: Path,
    _settings: SetupSettings,
    _requirements: ProfileRequirements,
    environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    _config: RuntimeConfig,
    _attempt: str,
    _profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    return (
        run_package_phase(
            project_root, runner=adapters.run, environment=environment, verified=verified
        ),
        "unavailable",
    )


def _paths(
    _project_root: Path,
    _settings: SetupSettings,
    _requirements: ProfileRequirements,
    _environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    config: RuntimeConfig,
    _attempt: str,
    profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    return run_paths_phase(
        config, profiles, compose=adapters.compose, verified=verified
    ), "unavailable"


def _postgres_image(
    project_root: Path,
    settings: SetupSettings,
    _requirements: ProfileRequirements,
    _environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    _config: RuntimeConfig,
    _attempt: str,
    _profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    return (
        run_postgres_image_phase(
            project_root,
            downloads=settings.downloads,
            image_present=adapters.image_present,
            builder=adapters.build_image,
            verified=verified,
        ),
        "unavailable",
    )


def _images(
    _project_root: Path,
    settings: SetupSettings,
    _requirements: ProfileRequirements,
    _environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    config: RuntimeConfig,
    _attempt: str,
    profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    return (
        run_images_phase(
            config,
            profiles,
            downloads=settings.downloads,
            runner=adapters.run,
            image_present=adapters.image_present,
            listed_images=adapters.listed_images,
            verified=verified,
        ),
        "unavailable",
    )


def _models(
    _project_root: Path,
    settings: SetupSettings,
    _requirements: ProfileRequirements,
    _environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    config: RuntimeConfig,
    _attempt: str,
    _profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    return (
        run_models_phase(
            config,
            downloads=settings.downloads,
            runner=adapters.run,
            listed=adapters.listed_models,
            verified=verified,
        ),
        "unavailable",
    )


def _services(
    _project_root: Path,
    settings: SetupSettings,
    _requirements: ProfileRequirements,
    _environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    config: RuntimeConfig,
    _attempt: str,
    profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    del verified
    return (
        run_services_phase(
            config, profiles, downloads=settings.downloads, compose=adapters.compose
        ),
        "unavailable",
    )


def _wait(
    _project_root: Path,
    _settings: SetupSettings,
    _requirements: ProfileRequirements,
    _environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    config: RuntimeConfig,
    _attempt: str,
    profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    del verified
    return (
        run_wait_phase(
            config,
            profiles,
            adapters.probe,
            sleep=adapters.sleep,
            cancelled=adapters.cancel,
            deadline_seconds=adapters.wait_seconds,
        ),
        "unavailable",
    )


def _contracts(
    project_root: Path,
    _settings: SetupSettings,
    _requirements: ProfileRequirements,
    environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    _config: RuntimeConfig,
    _attempt: str,
    _profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    return (
        run_contracts_phase(
            project_root, runner=adapters.run, environment=environment, verified=verified
        ),
        "unavailable",
    )


def _schema(
    _project_root: Path,
    _settings: SetupSettings,
    _requirements: ProfileRequirements,
    environment: Mapping[str, str] | None,
    _adapters: SetupAdapters,
    verified: dict[str, str],
    config: RuntimeConfig,
    attempt: str,
    _profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    override = None if environment is None else environment.get(DATABASE_URL_VARIABLE)
    if environment is None:
        override = os.environ.get(DATABASE_URL_VARIABLE)
    return run_schema_phase(
        config, override=override, run_id=attempt, verified=verified
    ), "unavailable"


def _readiness(
    _project_root: Path,
    _settings: SetupSettings,
    requirements: ProfileRequirements,
    environment: Mapping[str, str] | None,
    adapters: SetupAdapters,
    verified: dict[str, str],
    config: RuntimeConfig,
    _attempt: str,
    profiles: str,
) -> tuple[PhaseResult, ProviderStatus]:
    del verified
    return run_readiness_phase(
        config, profiles, requirements, probe=adapters.probe, environment=environment
    )


CONFIGURED_HANDLERS = {
    "package": _package,
    "paths": _paths,
    "postgres-image": _postgres_image,
    "images": _images,
    "models": _models,
    "services": _services,
    "wait": _wait,
    "contracts": _contracts,
    "schema": _schema,
    "readiness": _readiness,
}
