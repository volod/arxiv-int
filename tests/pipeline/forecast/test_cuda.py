"""CUDA host assumptions for the forecast, without loading models."""

import pytest

from arxiv_int.inference.resources import snapshot_host
from arxiv_int.pipeline.forecast.engine import build_forecast
from tests.pipeline.forecast.conftest import make_inputs


def test_live_nvidia_snapshot_is_recorded_when_a_device_is_present() -> None:
    from dataclasses import replace

    from arxiv_int.pipeline.forecast.model import HostAssumptions

    host = snapshot_host()
    if not host.gpus:
        pytest.skip("no NVIDIA device visible to nvidia-smi")
    inputs = replace(
        make_inputs(gpu=True),
        host=HostAssumptions(
            host.available_ram_gib,
            host.gpu_name,
            host.total_gpu_gib,
            host.device_id,
            1,
        ),
    )
    document = build_forecast(inputs)
    assert document.host.gpu_name == host.gpu_name
    assert document.host.gpu_total_gib == host.total_gpu_gib
    facts = next(item for item in document.stages if item.stage == "gamma")
    assert facts.gpu_required
    assert facts.decision != "blocked"
