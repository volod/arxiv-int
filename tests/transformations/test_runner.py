from pathlib import Path

import pytest

from arxiv_int.transformations.invoke import InvokeOutcome
from arxiv_int.transformations.model import (
    STATUS_FAILED,
    STATUS_NOT_RUN,
    STATUS_OK,
    TransformRequest,
)
from arxiv_int.transformations.runner import run_transform


def test_missing_database_is_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("ARXIV_INT_TRANSFORM_DATABASE_URL", raising=False)
    monkeypatch.delenv("ARXIV_INT_MIGRATION_DATABASE_URL", raising=False)
    root = Path(__file__).resolve().parents[2]
    result = run_transform(
        TransformRequest(command="build", run_id="missing-db", project_root=root)
    )
    assert result.status == STATUS_NOT_RUN
    assert result.activatable is False
    assert "no transform database" in result.detail


def test_unknown_command_and_invalid_run_id_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    root = Path(__file__).resolve().parents[2]
    unknown = run_transform(TransformRequest(command="explode", run_id="r1", project_root=root))
    assert unknown.status == STATUS_FAILED
    invalid = run_transform(TransformRequest(command="parse", run_id="---", project_root=root))
    assert invalid.status == STATUS_FAILED


def test_failed_invoke_cannot_activate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    from arxiv_int.transformations import runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "invoke_dbt",
        lambda args, credentials: InvokeOutcome(False, "data test failed"),
    )
    monkeypatch.setattr(runner_mod, "_row_counts", lambda url, names: {})
    root = Path(__file__).resolve().parents[2]
    result = run_transform(
        TransformRequest(
            command="build",
            run_id="fail-build",
            project_root=root,
            database_url="postgresql://arxiv_int:x@127.0.0.1:5432/arxiv_int",
            activate=True,
        )
    )
    assert result.status == STATUS_FAILED
    assert result.activatable is False
    from arxiv_int.transformations.activation import load_active_generation

    assert (
        load_active_generation(root) is None
        or load_active_generation(root).get("runId") != "fail-build"
    )


def test_successful_build_can_activate_and_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    from arxiv_int.transformations import runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "invoke_dbt",
        lambda args, credentials: InvokeOutcome(True, "ok"),
    )
    monkeypatch.setattr(
        runner_mod, "_row_counts", lambda url, names: {names[0]: 2} if names else {}
    )
    root = Path(__file__).resolve().parents[2]
    runs = tmp_path / "runs"
    result = run_transform(
        TransformRequest(
            command="build",
            run_id="ok-build",
            project_root=root,
            database_url="postgresql://arxiv_int:x@127.0.0.1:5432/arxiv_int",
            activate=True,
            publish=True,
            runs_dir=runs,
        )
    )
    assert result.status == STATUS_OK
    assert result.activatable is True
    assert (Path(result.artifact_dir) / "result.json").is_file()
    text = (Path(result.artifact_dir) / "result.json").read_text(encoding="utf-8")
    assert "arxiv_int:x@" not in text
    assert "postgresql://arxiv_int:x@" not in text
    from arxiv_int.transformations.activation import load_active_generation

    pointer = load_active_generation(root)
    assert pointer is not None
    assert pointer["runId"] == "ok-build"
    assert (runs / "ok-build" / "quality" / "result.json").is_file()


def test_concurrent_same_generation_cannot_activate_partial_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    from arxiv_int.transformations import runner as runner_mod

    started = threading.Event()
    release = threading.Event()

    def _blocking_invoke(args: object, credentials: object) -> InvokeOutcome:
        started.set()
        release.wait(timeout=5)
        return InvokeOutcome(True, "ok")

    monkeypatch.setattr(runner_mod, "invoke_dbt", _blocking_invoke)
    monkeypatch.setattr(runner_mod, "_row_counts", lambda url, names: {})
    root = Path(__file__).resolve().parents[2]
    url = "postgresql://arxiv_int:x@127.0.0.1:5432/arxiv_int"
    first: list[object] = []
    second: list[object] = []

    def _first() -> None:
        first.append(
            run_transform(
                TransformRequest(
                    command="build",
                    run_id="shared-gen",
                    project_root=root,
                    database_url=url,
                    activate=True,
                )
            )
        )

    worker = threading.Thread(target=_first)
    worker.start()
    assert started.wait(timeout=5)
    second.append(
        run_transform(
            TransformRequest(
                command="build",
                run_id="shared-gen",
                project_root=root,
                database_url=url,
                activate=True,
            )
        )
    )
    release.set()
    worker.join(timeout=5)
    assert second[0].status == STATUS_FAILED  # type: ignore[union-attr]
    assert "already owned" in second[0].detail  # type: ignore[union-attr]
    assert first[0].status == STATUS_OK  # type: ignore[union-attr]
    assert first[0].activatable is True  # type: ignore[union-attr]
