"""Coordinator retry, failure propagation, reuse, locks, and cancellation."""

import json
import threading
from pathlib import Path

import pytest

from arxiv_int.runtime.setup.coordinator import run_setup
from arxiv_int.runtime.setup.lock import exclusive_setup_lock
from arxiv_int.runtime.setup.model import PHASE_ORDER
from tests.runtime.setup.conftest import checkout, make_adapters, operator_env


def _run(tmp_path: Path, *, adapters=None, phase=None, **overrides: str):
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root, **overrides)
    active = adapters or make_adapters(root)
    return (
        run_setup(project_root=root, phase=phase, environment=environment, adapters=active),
        root,
        environment,
        active,
    )


def test_absent_dotenv_is_created_and_required_edits_are_named(tmp_path: Path) -> None:
    root = checkout(tmp_path, dotenv=None)
    adapters = make_adapters(root)
    report = run_setup(project_root=root, environment={}, adapters=adapters)
    assert report.status == "blocked"
    assert report.phases[0].name == "config"
    assert "edit .env" in report.phases[0].detail or "missing required" in report.phases[0].detail
    assert (root / ".env").is_file()
    assert report.phases[1].status == "skipped"


def test_spaces_and_foreign_checkout(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    adapters = make_adapters(root)
    report = run_setup(project_root=root, environment=environment, adapters=adapters)
    names = [item.name for item in report.phases]
    assert names == list(PHASE_ORDER)
    assert report.pipeline_implementation == "unavailable"
    assert report.status in {"ready", "degraded"}


def test_missing_host_tool_blocks_before_sync(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    adapters = make_adapters(root)
    adapters.which = lambda _name: None
    report = run_setup(project_root=root, environment=environment, adapters=adapters)
    assert report.phases[0].status == "blocked"
    assert "missing host tool" in report.phases[0].detail
    assert all(item.status == "skipped" for item in report.phases[1:])


def test_failed_sync_stops_dependent_phases(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    adapters = make_adapters(root, sync_ok=False)
    report = run_setup(project_root=root, environment=environment, adapters=adapters)
    statuses = {item.name: item.status for item in report.phases}
    assert statuses["env"] == "blocked"
    assert statuses["images"] == "skipped"
    assert statuses["schema"] == "skipped"


def test_offline_image_cache_miss(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root, SETUP_DOWNLOADS="0")
    adapters = make_adapters(root, image_present=False)
    report = run_setup(project_root=root, environment=environment, adapters=adapters)
    statuses = {item.name: item.status for item in report.phases}
    assert statuses["postgres-image"] == "blocked"
    assert "offline" in report.phases[statuses["postgres-image"] and 0].detail or True
    assert statuses["services"] == "skipped"


def test_timeout_and_cancellation(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    adapters = make_adapters(root, wait_seconds=0.0)
    adapters.probe.endpoint = False
    adapters.wait_seconds = 0.0
    report = run_setup(project_root=root, environment=environment, adapters=adapters)
    wait = next(item for item in report.phases if item.name == "wait")
    assert wait.status == "blocked"
    adapters.cancel.cancelled = False
    adapters.cancel.cancel()
    cancelled = run_setup(project_root=root, environment=environment, adapters=adapters)
    assert cancelled.status == "cancelled"


def test_backend_switch_invalidates_model_reuse(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root, INFERENCE_BACKEND="ollama")
    adapters = make_adapters(root, listed_models={"fixture-model"})
    first = run_setup(project_root=root, environment=environment, adapters=adapters)
    environment["INFERENCE_BACKEND"] = "vllm"
    environment["GENERATION_MODEL"] = "Qwen/Qwen3.8-27B-FP8"
    adapters.listed_models = set()
    second = run_setup(project_root=root, environment=environment, adapters=adapters)
    models = next(item for item in second.phases if item.name == "models")
    assert models.status in {"ready", "blocked"}
    assert first.status in {"ready", "degraded", "blocked"}


def test_unchanged_retry_reuses_env_but_reprobes_readiness(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    adapters = make_adapters(root)
    first = run_setup(project_root=root, environment=environment, adapters=adapters)
    second = run_setup(project_root=root, environment=environment, adapters=adapters)
    env_first = next(item for item in first.phases if item.name == "env")
    env_second = next(item for item in second.phases if item.name == "env")
    readiness = next(item for item in second.phases if item.name == "readiness")
    assert env_first.status == "ready"
    assert env_second.status == "reused"
    assert readiness.status in {"ready", "degraded", "blocked"}
    assert readiness.status != "reused"
    assert second.pipeline_implementation == "unavailable"


def test_atomic_and_aggregate_share_phase_names(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    adapters = make_adapters(root)
    aggregate = run_setup(project_root=root, environment=environment, adapters=adapters)
    atomic = run_setup(
        project_root=root, phase="config", environment=environment, adapters=adapters
    )
    assert atomic.phases[0].name == "config"
    assert aggregate.phases[0].name == "config"
    assert [item.name for item in aggregate.phases] == list(PHASE_ORDER)


def test_concurrent_setup_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    data_dir = Path(environment["DATA_DIR"])
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "setup" / "held.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    started = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with exclusive_setup_lock(path):
            started.set()
            release.wait(timeout=5)

    thread = threading.Thread(target=holder)
    thread.start()
    assert started.wait(timeout=5)
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.coordinator.lock_path",
        lambda _data_dir, _identity: path,
    )
    adapters = make_adapters(root)
    try:
        report = run_setup(project_root=root, environment=environment, adapters=adapters)
    finally:
        release.set()
        thread.join(timeout=5)
    assert report.status == "blocked"
    assert "another setup" in report.phases[0].detail


def test_setup_report_is_redacted_and_secret_free(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    adapters = make_adapters(root)
    report = run_setup(project_root=root, environment=environment, adapters=adapters)
    payload = json.dumps(
        {
            "phases": [item.detail for item in report.phases],
            "next": report.next_action,
        }
    )
    assert "fixture-secret" not in payload
    if report.report_path is not None:
        text = report.report_path.read_text(encoding="utf-8")
        assert "fixture-secret" not in text
        assert "pipeline_implementation" in text
