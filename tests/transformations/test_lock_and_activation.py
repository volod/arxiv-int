from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from arxiv_int.transformations.activation import (
    ActivationRefusedError,
    activate_generation,
    load_active_generation,
)
from arxiv_int.transformations.lock import (
    GenerationLockError,
    exclusive_generation,
    try_acquire_generation_lock,
)
from arxiv_int.transformations.model import STATUS_FAILED, STATUS_OK, TransformResult


def _result(status: str, *, activatable: bool, run_id: str = "r1") -> TransformResult:
    return TransformResult(
        status=status,
        command="build",
        run_id=run_id,
        generation_id="r1",
        activatable=activatable,
        detail="ok" if activatable else "failed",
        artifact_dir="/tmp/dbt/r1",
        selected=("tag:fixture",),
        input_fingerprint="a",
        model_fingerprint="b",
    )


def test_exclusive_generation_refuses_a_concurrent_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    held = try_acquire_generation_lock(tmp_path, "gen_a")
    try:
        with pytest.raises(GenerationLockError, match="already owned"):
            try_acquire_generation_lock(tmp_path, "gen_a")
    finally:
        held.release()
    with exclusive_generation(tmp_path, "gen_a"):
        pass
    again = try_acquire_generation_lock(tmp_path, "gen_a")
    again.release()


def test_thread_cannot_steal_an_active_generation_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    barrier_error: list[BaseException] = []

    def _contender() -> None:
        try:
            try_acquire_generation_lock(tmp_path, "shared")
        except GenerationLockError as error:
            barrier_error.append(error)

    with exclusive_generation(tmp_path, "shared"), ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_contender).result(timeout=5)
    assert barrier_error


def test_activation_refuses_failed_or_partial_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    assert load_active_generation(tmp_path) is None
    with pytest.raises(ActivationRefusedError, match="not activatable"):
        activate_generation(tmp_path, _result(STATUS_FAILED, activatable=False))
    assert load_active_generation(tmp_path) is None
    path = activate_generation(tmp_path, _result(STATUS_OK, activatable=True))
    loaded = load_active_generation(tmp_path)
    assert loaded is not None
    assert loaded["generationId"] == "r1"
    assert path.is_file()
    activate_generation(tmp_path, _result(STATUS_OK, activatable=True, run_id="r2"))
    assert load_active_generation(tmp_path)["runId"] == "r2"  # type: ignore[index]
