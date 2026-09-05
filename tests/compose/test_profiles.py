import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from arxiv_int.runtime import (
    ComposeConfigurationError,
    RuntimeConfig,
    compose_command,
    compose_environment,
    load_runtime_config,
    parse_profiles,
    run_compose,
)

PROJECT_ROOT = Path(__file__).parents[2]
PROFILES = ("core", "graph", "ui", "observability", "vllm", "cadvisor")


def _runtime_config(tmp_path: Path, **overrides: str) -> RuntimeConfig:
    checkout = tmp_path / "copied checkout"
    checkout.mkdir()
    (checkout / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (checkout / "docker").symlink_to(PROJECT_ROOT / "docker", target_is_directory=True)
    archive = tmp_path / "archive"
    archive.mkdir()
    values = {
        "ARCHIVE_DIR": str(archive),
        "RESULTS_DIR": str(tmp_path / "bulk results"),
        "PGDATA_DIR": str(tmp_path / "database"),
        "POSTGRES_PASSWORD": "fixture-secret-never-rendered",
        **overrides,
    }
    (checkout / ".env").write_text(
        "ARCHIVE_DIR=unused\nRESULTS_DIR=unused\nPGDATA_DIR=unused\n", encoding="utf-8"
    )
    return load_runtime_config(project_root=checkout, environment=values)


def _run_quiet_config(config: RuntimeConfig, profiles: tuple[str, ...]) -> int:
    command = compose_command(config, "config", profiles)
    completed = subprocess.run(
        command,
        cwd=config.project_root,
        env=compose_environment(config, base={"PATH": os.environ["PATH"]}),
        check=False,
        capture_output=True,
        text=True,
    )
    assert "fixture-secret-never-rendered" not in completed.stdout
    assert "fixture-secret-never-rendered" not in completed.stderr
    return completed.returncode


def _render_config(config: RuntimeConfig, profiles: tuple[str, ...]) -> dict[str, object]:
    command = list(compose_command(config, "config", profiles))
    command[-1:] = ("--format", "json")
    completed = subprocess.run(
        command,
        cwd=config.project_root,
        env=compose_environment(config, base={"PATH": os.environ["PATH"]}),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


@pytest.mark.parametrize("profile", PROFILES)
def test_each_compose_profile_validates_without_starting_services(
    tmp_path: Path, profile: str
) -> None:
    config = _runtime_config(tmp_path)

    assert _run_quiet_config(config, (profile,)) == 0


def test_combined_profiles_validate_without_rendering_secrets(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)

    assert _run_quiet_config(config, PROFILES) == 0


def test_rendered_topology_has_pins_health_stop_and_mount_isolation(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    rendered = _render_config(config, PROFILES)
    services = rendered["services"]
    assert isinstance(services, dict)
    for name, service in services.items():
        assert "latest" not in service["image"]
        if name != "age-viewer":
            assert "@sha256:" in service["image"]
        assert service["healthcheck"]["test"]
        assert service["stop_grace_period"]
        for port in service.get("ports", ()):  # not every service publishes a port
            assert port["host_ip"] == "127.0.0.1"
    vllm = services["vllm"]
    assert vllm["gpus"] == [{"count": -1}]
    assert "Qwen/Qwen3.8-27B-FP8" in vllm["command"]
    assert "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a" in vllm["command"]
    database_mounts = services["database"]["volumes"]
    assert database_mounts == [
        {
            "type": "bind",
            "source": str(config.pgdata_dir),
            "target": "/var/lib/postgresql/data",
        }
    ]
    for name, service in services.items():
        if name == "database":
            continue
        sources = {mount["source"] for mount in service.get("volumes", ())}
        assert str(config.pgdata_dir) not in sources
    assert services["grafana"]["volumes"][1]["read_only"] is True
    assert services["prometheus"]["volumes"][1]["read_only"] is True


def test_make_exposes_the_operator_wrappers() -> None:
    completed = subprocess.run(
        ["make", "--no-print-directory", "-n", "services-up", "SERVICE_PROFILES=core ui"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert 'arxiv_int_services up --profiles "core ui"' in completed.stdout
    help_text = subprocess.run(
        ["make", "--no-print-directory", "help"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert all(
        name in help_text for name in ("services-up", "services-status", "services-down", "logs")
    )


def test_profile_parser_is_ordered_deduplicated_and_rejects_unknown() -> None:
    assert parse_profiles("ui, core ui vllm") == ("core", "ui", "vllm")
    assert parse_profiles(()) == ("core",)
    with pytest.raises(ComposeConfigurationError, match=r"unknown Compose profile.*remote"):
        parse_profiles("core remote")


def test_operator_run_resolves_mounts_and_keeps_database_roots_private(
    tmp_path: Path,
) -> None:
    config = _runtime_config(
        tmp_path,
        PG_WAL_DIR=str(tmp_path / "database wal"),
        PG_TABLESPACE_COLD_DIR=str(tmp_path / "database cold"),
    )
    observed: dict[str, object] = {}

    def runner(command: tuple[str, ...], cwd: Path, environment: Mapping[str, str]) -> int:
        observed.update(command=command, cwd=cwd, environment=dict(environment))
        override = Path(command[command.index("--file", command.index("--file") + 1) + 1])
        observed["override"] = json.loads(override.read_text(encoding="utf-8"))
        return 0

    assert run_compose(config, "config", "core ui", runner=runner) == 0
    assert config.pgdata_dir.stat().st_mode & 0o777 == 0o700
    command = observed["command"]
    environment = observed["environment"]
    override = observed["override"]
    assert isinstance(command, tuple)
    assert isinstance(environment, dict)
    assert isinstance(override, dict)
    assert "fixture-secret-never-rendered" not in " ".join(command)
    assert environment["PGDATA_DIR"] == str(config.pgdata_dir)
    assert environment["GRAFANA_STATE_DIR"] == str(config.service_state_dir / "grafana")
    mounts = override["services"]["database"]["volumes"]
    assert {mount["source"] for mount in mounts} == {
        str(config.pg_wal_dir),
        str(config.pg_tablespaces[0][1]),
    }
    assert not tuple(config.data_dir.glob("compose-mounts-*.json"))


def test_up_requires_database_password_but_down_does_not(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path, POSTGRES_PASSWORD="")
    calls = 0

    def runner(_command: tuple[str, ...], _cwd: Path, _environment: Mapping[str, str]) -> int:
        nonlocal calls
        calls += 1
        return 0

    with pytest.raises(ComposeConfigurationError, match="POSTGRES_PASSWORD"):
        run_compose(config, "up", "core", runner=runner)
    assert run_compose(config, "down", "core", runner=runner) == 0
    assert calls == 1


def test_service_preflight_does_not_require_an_unused_proof_mount(tmp_path: Path) -> None:
    proof = tmp_path / "writable proof archive"
    proof.mkdir()
    config = _runtime_config(tmp_path, PROOF_ARCHIVE_DIR=str(proof))

    assert run_compose(config, "config", "core", runner=lambda _c, _w, _e: 0) == 0
