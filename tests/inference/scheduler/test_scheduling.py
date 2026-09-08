"""Tests for GPU-aware model placement and lifecycle."""

import pytest

from arxiv_int.inference import ModelRequirement, ModelScheduler


def test_scheduler_falls_back_and_releases_on_error() -> None:
    scheduler = ModelScheduler(free_gpu_gib=8.0)
    requirement = ModelRequirement("large", gpu_gib=12.0)
    released: list[object] = []

    with (
        pytest.raises(RuntimeError, match="operation failed"),
        scheduler.session(requirement, lambda device: {"device": device}, released.append) as (
            model,
            placement,
        ),
    ):
        assert model == {"device": "cpu"}
        assert placement.device == "cpu"
        raise RuntimeError("operation failed")

    assert released == [{"device": "cpu"}]
    assert scheduler.place(ModelRequirement("small", gpu_gib=4.0)).device == "cuda"
    assert scheduler.place(ModelRequirement("gpu-only", gpu_gib=12.0, allow_cpu=False)).device == (
        "unavailable"
    )
