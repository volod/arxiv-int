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


@pytest.fixture(scope="module")
def rendered_topology(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[RuntimeConfig, dict[str, object]]:
    config = _runtime_config(tmp_path_factory.mktemp("topology"))
    services = _render_config(config, PROFILES)["services"]
    assert isinstance(services, dict)
    return config, services


def test_rendered_services_pin_images_and_declare_health_and_stop(
    rendered_topology: tuple[RuntimeConfig, dict[str, object]],
) -> None:
    _, services = rendered_topology

    for name, service in services.items():
        assert "latest" not in service["image"]
        if name not in {"age-viewer"} and not str(service["image"]).startswith("arxiv-int/"):
            assert "@sha256:" in service["image"]
        assert service["healthcheck"]["test"]
        assert service["stop_grace_period"]


def test_rendered_services_publish_ports_on_loopback_only(
    rendered_topology: tuple[RuntimeConfig, dict[str, object]],
) -> None:
    _, services = rendered_topology

    for service in services.values():
        for port in service.get("ports", ()):  # not every service publishes a port
            assert port["host_ip"] == "127.0.0.1"


def test_rendered_ports_follow_the_resolved_configuration(
    tmp_path: Path, rendered_topology: tuple[RuntimeConfig, dict[str, object]]
) -> None:
    config, services = rendered_topology
    published = {
        name: str(service["ports"][0]["published"])
        for name, service in services.items()
        if service.get("ports")
    }
    defaults = dict(config.values)
    overridden = _render_config(_runtime_config(tmp_path, VLLM_PORT="8100"), ("vllm",))

    assert published["database"] == defaults["POSTGRES_PORT"] == "5432"
    assert published["grafana"] == defaults["GRAFANA_PORT"] == "3000"
    assert published["age-viewer"] == defaults["AGE_VIEWER_PORT"] == "3001"
    assert published["prometheus"] == defaults["PROMETHEUS_PORT"] == "9090"
    assert published["cadvisor"] == defaults["CADVISOR_PORT"] == "8080"
    assert published["vllm"] == defaults["VLLM_PORT"] == "8000"
    assert str(overridden["services"]["vllm"]["ports"][0]["published"]) == "8100"


def test_rendered_vllm_service_pins_gpu_model_and_revision(
    rendered_topology: tuple[RuntimeConfig, dict[str, object]],
) -> None:
    _, services = rendered_topology
    vllm = services["vllm"]

    assert vllm["gpus"] == [{"count": -1}]
    assert "Qwen/Qwen3.8-27B-FP8" in vllm["command"]
    assert "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a" in vllm["command"]


def test_rendered_database_root_is_mounted_only_by_the_database(
    rendered_topology: tuple[RuntimeConfig, dict[str, object]],
) -> None:
    config, services = rendered_topology

    assert services["database"]["volumes"] == [
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


def test_rendered_services_drop_privileges_and_keep_configs_read_only(
    rendered_topology: tuple[RuntimeConfig, dict[str, object]],
) -> None:
    _, services = rendered_topology

    assert services["grafana"]["volumes"][1]["read_only"] is True
    assert services["prometheus"]["volumes"][1]["read_only"] is True
    expected_user = f"{os.getuid()}:{os.getgid()}"
    for name in ("database", "age-viewer", "grafana", "prometheus", "postgres-exporter", "vllm"):
        assert services[name]["user"] == expected_user
    assert "user" not in services["cadvisor"]


def test_profile_parser_is_ordered_deduplicated_and_rejects_unknown() -> None:
    assert parse_profiles("ui, core ui vllm") == ("core", "ui", "vllm")
    assert parse_profiles("pipeline") == ("core", "ui", "observability")
    assert parse_profiles("pipeline vllm") == ("core", "ui", "observability", "vllm")
    assert parse_profiles("pipeline graph") == (
        "core",
        "graph",
        "ui",
        "observability",
    )
    assert parse_profiles(()) == ("core", "ui", "observability")
    with pytest.raises(ComposeConfigurationError, match=r"unknown Compose profile.*remote"):
        parse_profiles("core remote")


@pytest.mark.parametrize("backend", ["ollama", "vllm"])
def test_generation_override_only_reaches_vllm_when_selected(tmp_path: Path, backend: str) -> None:
    config = _runtime_config(
        tmp_path,
        INFERENCE_BACKEND=backend,
        GENERATION_MODEL="operator/model",
        GENERATION_MODEL_REVISION="operator-revision",
    )
    services = _render_config(config, ("vllm",))["services"]
    assert isinstance(services, dict)
    expected_model = "operator/model" if backend == "vllm" else "Qwen/Qwen3.8-27B-FP8"
    assert expected_model in services["vllm"]["command"]
    assert ("operator-revision" in services["vllm"]["command"]) == (backend == "vllm")


def test_pipeline_service_start_waits_for_every_required_service(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    observed: list[tuple[str, ...]] = []

    assert (
        run_compose(
            config,
            "up",
            "pipeline",
            runner=lambda command, _cwd, _environment: observed.append(command) or 0,
        )
        == 0
    )

    command = observed[0]
    selected = tuple(
        command[index + 1] for index, item in enumerate(command) if item == "--profile"
    )
    assert selected == ("core", "ui", "observability")
    assert "--wait" in command

    services = _render_config(config, selected)["services"]
    assert isinstance(services, dict)
    assert set(services) == {"database", "grafana", "postgres-exporter", "prometheus"}
    assert all(service["healthcheck"] for service in services.values())
    exporter = services["postgres-exporter"]
    data_source = exporter["environment"]["DATA_SOURCE_NAME"]
    assert " @" not in data_source
    assert "@database:5432/" in data_source
    health_test = " ".join(exporter["healthcheck"]["test"])
    assert "/metrics" in health_test
    assert "/health" not in health_test


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
