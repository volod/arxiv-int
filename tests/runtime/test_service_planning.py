from pathlib import Path

import pytest

from arxiv_int.cli import build_parser
from arxiv_int.runtime import (
    ComposeConfigurationError,
    compose_command,
    compose_environment,
    run_compose,
)
from arxiv_int.runtime.compose import compose_base_command
from arxiv_int.runtime.service_plan import PROFILE_SERVICES, plan_services
from tests.runtime.test_profiles import _render_config, _runtime_config


@pytest.mark.heavy
@pytest.mark.parametrize(
    "profiles", [*PROFILE_SERVICES, "core vllm", "pipeline", "pipeline graph vllm cadvisor"]
)
def test_plan_matches_rendered_compose(tmp_path: Path, profiles: str) -> None:
    config = _runtime_config(tmp_path)
    plan = plan_services(profiles)
    assert set(_render_config(config, plan.profiles)["services"]) == set(plan.services)


@pytest.mark.parametrize("profiles", ["core", "vllm", "core vllm", "cadvisor"])
def test_only_selected_service_layout_is_prepared(tmp_path: Path, profiles: str) -> None:
    config = _runtime_config(tmp_path, ARCHIVE_DIR=str(tmp_path / "missing archive"))
    assert run_compose(config, "config", profiles, runner=lambda _c, _w, _e: 0) == 0
    selected = profiles.split()
    assert config.pgdata_dir.exists() == ("core" in selected)
    assert config.model_cache_dir.exists() == ("vllm" in selected)
    assert not config.service_state_dir.exists()
    assert (config.results_dir / "normalized").is_dir()
    assert config.runs_dir.is_dir()
    assert config.tmp_dir.is_dir()


def test_vllm_up_ignores_unselected_database_disk_and_password(tmp_path: Path) -> None:
    disk = tmp_path / "unavailable database"
    disk.write_text("not a directory")
    config = _runtime_config(tmp_path, PGDATA_DIR=str(disk), POSTGRES_PASSWORD="")
    assert run_compose(config, "up", "vllm", runner=lambda _c, _w, _e: 0) == 0
    assert disk.read_text() == "not a directory"


@pytest.mark.parametrize("action", ["status", "down", "logs"])
def test_observational_commands_do_not_prepare_unavailable_disks(
    tmp_path: Path, action: str
) -> None:
    config = _runtime_config(tmp_path)
    config.results_dir.write_text("offline fixture")
    config.pgdata_dir.write_text("offline fixture")
    calls = []
    assert (
        run_compose(config, action, "pipeline", runner=lambda c, _w, _e: calls.append(c) or 0) == 0
    )
    assert len(calls) == 1
    assert config.results_dir.read_text() == "offline fixture"


@pytest.mark.parametrize("services", [("--follow",), ("vllm",), ("unknown",)])
def test_log_service_arguments_are_bounded_before_layout(
    tmp_path: Path, services: tuple[str, ...]
) -> None:
    config = _runtime_config(tmp_path)
    with pytest.raises(ComposeConfigurationError, match="selected profiles"):
        run_compose(config, "config", "core", services=services)
    assert not config.results_dir.exists()


def test_base_builder_and_log_command_are_pure(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    base = compose_base_command(config, ("core",))
    assert compose_command(config, "status", ("core",)) == (*base, "ps", "--all")
    assert compose_command(
        config, "logs", ("core",), services=("database",), tail=0, follow=True
    ) == (*base, "logs", "--no-color", "--tail", "0", "--follow", "database")
    assert compose_command(config, "up", ("core",), pull="never")[-2:] == ("--pull", "never")
    with pytest.raises(ComposeConfigurationError, match="tail"):
        run_compose(config, "config", "core", tail=-1)
    with pytest.raises(ComposeConfigurationError, match="unknown Compose"):
        compose_base_command(config, ("--all",))
    with pytest.raises(ComposeConfigurationError, match="unsupported"):
        compose_command(config, "reset", ("core",))
    assert not config.results_dir.exists()


def test_cli_help_uses_shared_profile_policy(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["services", "up", "--help"])
    output = " ".join(capsys.readouterr().out.split()).replace("- ", "-")
    for profile, services in PROFILE_SERVICES.items():
        assert f"{profile}: {', '.join(services)}" in output


def test_ambient_profiles_cannot_activate_unselected_services(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    assert compose_environment(config, base={"COMPOSE_PROFILES": "vllm"})["COMPOSE_PROFILES"] == ""


@pytest.mark.parametrize(
    "profiles, extensions",
    [("core", {"pg_search", "vector"}), ("graph", {"pg_search", "vector", "age"}), ("vllm", set())],
)
def test_extension_requirements_follow_the_plan(profiles: str, extensions: set[str]) -> None:
    assert plan_services(profiles).extensions == extensions
