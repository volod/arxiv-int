"""Typed PIPELINE_PROFILE, SERVICE_PROFILES, and SETUP_DOWNLOADS resolution."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.runtime.config import merge_config_layers
from arxiv_int.runtime.config_schema import DEFAULTS, ConfigurationError, apply_defaults, selected
from arxiv_int.runtime.dotenv import DotenvError, read_dotenv
from arxiv_int.runtime.inference_config import selected_backend
from arxiv_int.runtime.project_root import find_project_root

DEFAULT_PIPELINE_PROFILE = "investigation"
DEFAULT_SERVICE_PROFILES = "pipeline"
DEFAULT_SETUP_DOWNLOADS = "1"
LOCKED_EXTRAS: tuple[str, ...] = (
    "dev",
    "contracts",
    "graph",
    "store",
    "lake",
    "data-quality",
    "inference",
)
_DOWNLOAD_TRUE = frozenset({"1", "true", "yes", "on"})
_DOWNLOAD_FALSE = frozenset({"0", "false", "no", "off"})


@dataclass(frozen=True, slots=True)
class SetupSettings:
    """Operator-selected setup profile, services, and download policy."""

    pipeline_profile: str
    service_profiles: str
    downloads: bool
    backend: str

    @property
    def extras(self) -> tuple[str, ...]:
        return LOCKED_EXTRAS


def parse_setup_downloads(value: str) -> bool:
    """Parse SETUP_DOWNLOADS; unknown values are configuration errors."""
    normalized = value.strip().lower()
    if normalized in _DOWNLOAD_TRUE:
        return True
    if normalized in _DOWNLOAD_FALSE:
        return False
    raise ConfigurationError("SETUP_DOWNLOADS must be 0 or 1")


def effective_service_profiles(settings: SetupSettings) -> str:
    """Add the vLLM profile when the selected backend requires it."""
    tokens = settings.service_profiles.replace(",", " ").split()
    if settings.backend == "vllm" and "vllm" not in tokens:
        return f"{settings.service_profiles} vllm".strip()
    return settings.service_profiles


def load_setup_settings(
    *,
    project_root: Path | None = None,
    environment: Mapping[str, str] | None = None,
    cli: Mapping[str, str | None] | None = None,
) -> SetupSettings:
    """Resolve setup settings without requiring operator roots."""
    root = find_project_root(project_root, environment)
    try:
        dotenv = read_dotenv(root / ".env")
    except DotenvError as error:
        raise ConfigurationError(str(error)) from error
    env_values = selected(os.environ if environment is None else environment)
    values = selected(merge_config_layers(DEFAULTS, dotenv, env_values, cli or {}))
    apply_defaults(values)
    return SetupSettings(
        pipeline_profile=values.get("PIPELINE_PROFILE", "").strip() or DEFAULT_PIPELINE_PROFILE,
        service_profiles=values.get("SERVICE_PROFILES", "").strip() or DEFAULT_SERVICE_PROFILES,
        downloads=parse_setup_downloads(
            values.get("SETUP_DOWNLOADS", "").strip() or DEFAULT_SETUP_DOWNLOADS
        ),
        backend=selected_backend(values),
    )
