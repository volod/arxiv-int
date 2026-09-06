"""Branch coverage for model, image, and support setup phases."""

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from arxiv_int.readiness.report import PreflightFinding, PreflightReport
from arxiv_int.readiness.run import ReadinessResult
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.setup.adapters import CancelToken
from arxiv_int.runtime.setup.env_phase import run_env_phase
from arxiv_int.runtime.setup.images import (
    compose_service_images,
    run_images_phase,
    run_postgres_image_phase,
)
from arxiv_int.runtime.setup.models import parse_ollama_list, run_models_phase
from arxiv_int.runtime.setup.requirements import resolve_requirements
from arxiv_int.runtime.setup.settings import load_setup_settings
from arxiv_int.runtime.setup.support import (
    run_contracts_phase,
    run_package_phase,
    run_paths_phase,
    run_readiness_phase,
    run_services_phase,
)
from arxiv_int.runtime.setup.wait import _health_result, run_wait_phase
from tests.compose.test_profiles import _runtime_config
from tests.runtime.setup.conftest import FixtureProbe, checkout, completed, operator_env


def test_parse_ollama_list_skips_blank_lines() -> None:
    assert parse_ollama_list("NAME ID\n\nllama:latest  abc\n") == {"llama:latest"}


def test_models_ollama_list_failure_then_pull(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    config = load_runtime_config(project_root=root, environment=environment)

    def runner(command: tuple[str, ...], **_kwargs: object) -> CompletedProcess[str]:
        if command[:2] == ("ollama", "list"):
            return completed(1, stderr="down")
        if command[:2] == ("ollama", "pull"):
            return completed(1, stderr="pull failed")
        return completed(0)

    listed = run_models_phase(config, downloads=True, runner=runner, listed=None)
    assert listed.status == "blocked"
    pulled = run_models_phase(
        config, downloads=True, runner=lambda *_a, **_k: completed(0), listed=set()
    )
    assert pulled.status == "ready"


def test_models_offline_and_empty_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    config = load_runtime_config(project_root=root, environment=environment)
    offline = run_models_phase(
        config, downloads=False, runner=lambda *_a, **_k: completed(0), listed=set()
    )
    assert "offline" in offline.detail
    monkeypatch.setattr("arxiv_int.runtime.setup.models.configured_models", lambda _config: ())
    empty = run_models_phase(config, downloads=True, runner=lambda *_a, **_k: completed(0))
    assert empty.status == "blocked"


def test_vllm_cache_present(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root, INFERENCE_BACKEND="vllm")
    config = load_runtime_config(project_root=root, environment=environment)
    hub = config.model_cache_dir / "hub"
    hub.mkdir(parents=True)
    (hub / "weights.bin").write_text("x", encoding="utf-8")
    result = run_models_phase(
        config, downloads=True, runner=lambda *_a, **_k: completed(0), listed=set()
    )
    assert "vLLM" in result.detail


def test_postgres_image_builder_paths(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    assert compose_service_images(tmp_path) == {}
    missing = run_postgres_image_phase(
        root, downloads=True, image_present=lambda _ref: False, builder=None
    )
    assert "builder is unavailable" in missing.detail
    failed = run_postgres_image_phase(
        root, downloads=True, image_present=lambda _ref: False, builder=lambda _root: 1
    )
    assert failed.status == "blocked"
    built = run_postgres_image_phase(
        root, downloads=True, image_present=lambda _ref: False, builder=lambda _root: 0
    )
    assert built.status == "ready"


def test_images_pull_failure_and_success(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    listed = {"grafana": "grafana/grafana:fixture", "database": "arxiv-int/postgres:x"}
    failed = run_images_phase(
        config,
        "pipeline",
        downloads=True,
        runner=lambda *_a, **_k: completed(1),
        image_present=lambda _ref: False,
        listed_images=listed,
    )
    assert failed.status == "blocked"
    acquired = run_images_phase(
        config,
        "pipeline",
        downloads=True,
        runner=lambda *_a, **_k: completed(0),
        image_present=lambda _ref: False,
        listed_images={"grafana": "grafana/grafana:fixture"},
    )
    assert acquired.status == "ready"


def test_package_paths_services_and_contracts_failures(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    config = load_runtime_config(project_root=root, environment=environment)
    assert run_package_phase(root, runner=lambda *_a, **_k: completed(0)).status == "blocked"
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "arxiv-int").write_text("x", encoding="utf-8")
    assert run_package_phase(root, runner=lambda *_a, **_k: completed(1)).status == "blocked"
    assert run_paths_phase(config, "pipeline", compose=lambda *_a, **_k: 1).status == "blocked"
    failed_up = run_services_phase(config, "pipeline", downloads=False, compose=lambda *_a, **_k: 1)
    assert failed_up.status == "blocked"
    failed_contract = run_contracts_phase(
        root, runner=lambda command, **_k: completed(1 if "contracts" in command else 0)
    )
    assert failed_contract.status == "blocked"


def test_readiness_blocked_and_degraded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    config = load_runtime_config(project_root=root, environment=environment)
    settings = load_setup_settings(project_root=root, environment=environment)
    requirements = resolve_requirements(settings, environment)

    def _result(status: str) -> ReadinessResult:
        report = PreflightReport("r")
        report.add("inference.endpoint", status, f"{status} finding", action="retry")
        return ReadinessResult(report, None)

    monkeypatch.setattr(
        "arxiv_int.runtime.setup.support.run_readiness",
        lambda **_k: _result("blocked"),
    )
    blocked, pipeline = run_readiness_phase(
        config, "core", requirements, probe=FixtureProbe(), persist=False
    )
    assert blocked.status == "blocked"
    assert pipeline == "unavailable"
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.support.run_readiness",
        lambda **_k: _result("degraded"),
    )
    degraded, _pipeline = run_readiness_phase(
        config, "core", requirements, probe=FixtureProbe(), persist=False
    )
    assert degraded.status == "degraded"


def test_wait_cancel(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    config = load_runtime_config(project_root=root, environment=environment)
    token = CancelToken()
    token.cancel()
    waiting = run_wait_phase(
        config,
        "core",
        FixtureProbe(endpoint=False),
        timeout=0.01,
        deadline_seconds=1.0,
        sleep=lambda _seconds: None,
        cancelled=token,
    )
    assert waiting.status == "cancelled"


def test_wait_models_unready_when_endpoint_is_up() -> None:
    report = PreflightReport("w")
    report.extend(
        (
            PreflightFinding("inference.endpoint", "ready", "up"),
            PreflightFinding("inference.models", "blocked", "missing model", action="pull"),
        )
    )
    health = _health_result(report, type("Plan", (), {"services": ("database",)})())
    assert health is not None
    assert health.status == "blocked"


def test_contracts_inherit_process_environment(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "arxiv-int").write_text("x", encoding="utf-8")
    seen: dict[str, object] = {}

    def runner(
        command: tuple[str, ...], *, cwd: Path, env: dict[str, str] | None = None
    ) -> CompletedProcess[str]:
        del command, cwd
        seen["env"] = env
        return completed(0)

    result = run_contracts_phase(root, runner=runner, environment=None)
    assert result.status in {"ready", "reused"}
    env = seen["env"]
    assert isinstance(env, dict)
    assert "PATH" in env


def test_env_phase_requires_venv_after_sync(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    result = run_env_phase(
        root,
        downloads=False,
        runner=lambda *_a, **_k: completed(0),
        extras=(),
        environment={},
    )
    assert "did not create .venv" in result.detail
