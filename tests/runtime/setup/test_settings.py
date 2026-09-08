"""Setup settings, extras, and fixture requirements."""

from pathlib import Path

import pytest

from arxiv_int.runtime import ConfigurationError
from arxiv_int.runtime.setup.requirements import resolve_requirements
from arxiv_int.runtime.setup.settings import (
    LOCKED_EXTRAS,
    load_setup_settings,
    parse_setup_downloads,
)
from tests.runtime.setup.conftest import checkout, operator_env


def test_setup_settings_use_spec_defaults(tmp_path: Path) -> None:
    root = checkout(tmp_path, dotenv="ARCHIVE_DIR=a\nRESULTS_DIR=r\nPGDATA_DIR=p\n")
    settings = load_setup_settings(project_root=root, environment={})
    assert settings.pipeline_profile == "investigation"
    assert settings.service_profiles == "pipeline"
    assert settings.downloads is True
    assert settings.extras == LOCKED_EXTRAS


def test_setup_settings_honor_dotenv_and_cli(tmp_path: Path) -> None:
    root = checkout(
        tmp_path,
        dotenv="PIPELINE_PROFILE=lexical\nSERVICE_PROFILES=core\nSETUP_DOWNLOADS=0\n",
    )
    settings = load_setup_settings(
        project_root=root,
        environment={"SETUP_DOWNLOADS": "1"},
        cli={"SERVICE_PROFILES": "core vllm"},
    )
    assert settings.pipeline_profile == "lexical"
    assert settings.service_profiles == "core vllm"
    assert settings.downloads is True


def test_parse_setup_downloads_rejects_unknown_values() -> None:
    with pytest.raises(ConfigurationError, match="SETUP_DOWNLOADS"):
        parse_setup_downloads("maybe")


def test_investigation_requirements_name_unimplemented_providers(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    operator_env(tmp_path, root)
    settings = load_setup_settings(project_root=root, environment={})
    requirements = resolve_requirements(settings)
    assert requirements.unimplemented_stages
    assert requirements.missing_providers
    assert "extraction" in requirements.missing_providers or "nlp" in requirements.missing_providers
    assert "gpu" not in requirements.feature_groups
    assert "ui" not in requirements.feature_groups
