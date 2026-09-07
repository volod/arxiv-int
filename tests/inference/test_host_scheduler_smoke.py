"""Declared CUDA-host smoke for the model resource scheduler."""

import json
import os
from pathlib import Path
from shutil import copytree

import pytest

from arxiv_int.inference.errors import ModelFitError
from arxiv_int.inference.factory import (
    client_from_config,
    footprint_from_config,
    scheduler_from_config,
)
from arxiv_int.inference.resources import snapshot_host
from arxiv_int.inference.scheduling import ModelRequirement
from arxiv_int.interfaces.inference import GenerationRequest
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.config_model import RuntimeConfig

pytestmark = pytest.mark.skipif(
    os.environ.get("ARXIV_INT_RUN_INFERENCE_SMOKE") != "1",
    reason="set ARXIV_INT_RUN_INFERENCE_SMOKE=1 for the declared local CUDA scheduler smoke",
)

RUN_ID = "scheduler-0032"
SMALL_MODEL = "llama3.2:3b"
LARGE_MODEL = "qwen3.8:27b"


def test_host_gpu_fit_lease_generate_and_telemetry() -> None:
    config = load_runtime_config()
    snapshot = snapshot_host()
    assert snapshot.gpus, "CUDA-host smoke requires a visible NVIDIA GPU"
    assert snapshot.total_gpu_gib >= 15.0
    client = client_from_config(config, timeout=120.0)
    scheduler = scheduler_from_config(config, run_id=RUN_ID, client=client, wait_seconds=15.0)
    try:
        models = set(client.available_models())
        small_id = (
            SMALL_MODEL if SMALL_MODEL in models else (client.default_model or next(iter(models)))
        )
        small_fp = footprint_from_config(config, client.name, small_id)
        small_req = ModelRequirement(small_id, backend=client.name, allow_cpu=small_fp.allow_cpu)
        _snapshot, _occ, _est, small_place = scheduler.decide(small_req, small_fp)
        assert small_place.device == "cuda", small_place.detail
        if LARGE_MODEL in models:
            large_fp = footprint_from_config(config, client.name, LARGE_MODEL)
            large_req = ModelRequirement(
                LARGE_MODEL, backend=client.name, allow_cpu=False, context_tokens=2048
            )
            with (
                pytest.raises(ModelFitError, match=r"insufficient|occupied"),
                scheduler.session(large_req, large_fp),
            ):
                pass
        with scheduler.session(small_req, small_fp) as granted:
            assert granted.placement.device == "cuda"
            assert granted.lease is not None
            chat = client.generate(
                GenerationRequest(
                    "Reply with the single word pong.", model_id=small_id, max_output_tokens=16
                )
            )
            assert chat.status == "ok", chat.text
            scheduler.record_metrics(
                small_req,
                snapshot_host(),
                granted.estimate,
                lease_id=granted.lease.lease_id,
                throughput_tokens_per_s=chat.tokens_per_second,
                detail=chat.status,
            )
        current = config.service_state_dir / "inference" / "gpu.lease.json"
        if current.is_file():
            payload = json.loads(current.read_text(encoding="utf-8"))
            assert payload.get("status") != "acquired"
    finally:
        client.close()
    telemetry = config.runs_dir / RUN_ID / "telemetry" / "resource-events.jsonl"
    assert telemetry.is_file()
    payload = telemetry.read_text(encoding="utf-8")
    assert "acquired" in payload
    assert "released" in payload
    assert "pong" not in payload
    _copy_evidence(config, telemetry)


def _copy_evidence(config: RuntimeConfig, telemetry: Path) -> None:
    data_dir = os.environ.get("DATA_DIR", ".data")
    target = Path(data_dir) / "inference" / RUN_ID
    target.mkdir(parents=True, exist_ok=True)
    (target / "resource-events.jsonl").write_text(telemetry.read_text(encoding="utf-8"))
    snapshot = snapshot_host()
    (target / "host-snapshot.json").write_text(
        json.dumps(
            {
                "gpu": snapshot.gpu_name,
                "total_gib": snapshot.total_gpu_gib,
                "free_gib": snapshot.free_gpu_gib,
                "power_watts": snapshot.power_watts,
                "ram_available_gib": snapshot.available_ram_gib,
            },
            indent=2,
        )
        + "\n"
    )
    lease_dir = config.service_state_dir / "inference"
    if lease_dir.is_dir():
        copytree(lease_dir, target / "ctl.resource_lease", dirs_exist_ok=True)
