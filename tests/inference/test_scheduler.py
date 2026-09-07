"""Host-wide scheduler: fit, exclusive CUDA sessions, fallback, and vLLM policy."""

from pathlib import Path
from threading import Event, Thread
from time import sleep

import pytest

from arxiv_int.inference.client import LocalInferenceClient
from arxiv_int.inference.errors import LeaseCancelledError, ModelFitError
from arxiv_int.inference.footprint import ModelFootprint, estimate_footprint
from arxiv_int.inference.lifecycle import OccupancyProbe, RecordingVllmController
from arxiv_int.inference.resources import GpuDevice, HostSnapshot, RamSnapshot
from arxiv_int.inference.scheduler import ModelResourceScheduler, scheduler_paths
from arxiv_int.inference.scheduling import ModelRequirement, OccupancySnapshot, place_requirement
from tests.inference.fakes import FakeState, default_models, serve

SMALL_MODEL = "gemma3:4b"
LARGE = ModelFootprint(
    weights_gib=16.8,
    kv_cache_per_1k_context_gib=0.18,
    runtime_overhead_gib=1.2,
    cpu_ram_gib=24.0,
    allow_cpu=True,
)
SMALL = ModelFootprint(
    weights_gib=3.1,
    kv_cache_per_1k_context_gib=0.05,
    runtime_overhead_gib=0.6,
    cpu_ram_gib=6.0,
    allow_cpu=True,
)


def _host(free_gib: float = 14.6, ram_gib: float = 112.0) -> HostSnapshot:
    used = max(16.0 - free_gib, 0.0)
    return HostSnapshot(
        ram=RamSnapshot(125.0, ram_gib),
        gpus=(GpuDevice(0, "NVIDIA GeForce RTX 4060 Ti", 16.0, free_gib, used, 10.0, 26.0),),
        database_reserve_gib=4.0,
    )


def _scheduler(
    tmp_path: Path,
    snapshot: HostSnapshot,
    *,
    client: LocalInferenceClient | None = None,
    vllm: RecordingVllmController | None = None,
    occupancy: OccupancyProbe | None = None,
    wait_seconds: float = 2.0,
) -> ModelResourceScheduler:
    lease, sink = scheduler_paths(tmp_path / "services", tmp_path / "runs", "run-1")
    return ModelResourceScheduler(
        lease=lease,
        sink=sink,
        run_id="run-1",
        client=client,
        vllm=vllm,
        occupancy=occupancy or OccupancyProbe(client=client, vllm=vllm),
        snapshot=lambda: snapshot,
        wait_seconds=wait_seconds,
    )


def test_small_model_fits_cuda_and_large_gpu_only_is_actionable() -> None:
    snapshot = _host()
    small_req = ModelRequirement(SMALL_MODEL, backend="ollama")
    large_req = ModelRequirement("qwen3.8:27b", backend="ollama", allow_cpu=False)
    small = place_requirement(small_req, snapshot, estimate_footprint(SMALL), OccupancySnapshot())
    large = place_requirement(large_req, snapshot, estimate_footprint(LARGE), OccupancySnapshot())
    assert small.device == "cuda"
    assert large.device == "unavailable"
    assert "KV cache" in large.detail or "kv" in large.detail
    assert "smaller" in large.detail or "CPU fallback" in large.detail or "offload" in large.detail


def test_large_model_cpu_fallback_is_explicit() -> None:
    placement = place_requirement(
        ModelRequirement("qwen3.8:27b", allow_cpu=True),
        _host(),
        estimate_footprint(LARGE),
        OccupancySnapshot(),
    )
    assert placement.device == "cpu"
    assert "explicit CPU fallback" in placement.detail


def test_reclaimable_ollama_vram_enables_cuda() -> None:
    snapshot = _host(free_gib=1.0)
    occupancy = OccupancySnapshot(ollama_loaded=("other",), ollama_vram_gib=14.0)
    allowed = place_requirement(
        ModelRequirement(SMALL_MODEL, allow_unload=True),
        snapshot,
        estimate_footprint(SMALL),
        occupancy,
    )
    blocked = place_requirement(
        ModelRequirement(SMALL_MODEL, allow_unload=False, allow_cpu=False),
        snapshot,
        estimate_footprint(SMALL),
        occupancy,
    )
    assert allowed.device == "cuda"
    assert "reclaim" in allowed.detail
    assert blocked.device == "unavailable"


def test_already_loaded_target_is_kept_not_unloaded() -> None:
    placement = place_requirement(
        ModelRequirement(SMALL_MODEL),
        _host(free_gib=12.0),
        estimate_footprint(SMALL),
        OccupancySnapshot(
            ollama_loaded=(SMALL_MODEL,),
            ollama_vram_gib=3.3,
            ollama_resident=((SMALL_MODEL, 3.3),),
        ),
    )
    assert placement.device == "cuda"
    assert "will unload" not in placement.detail


def test_ram_shortfall_rejects_even_when_vram_fits() -> None:
    placement = place_requirement(
        ModelRequirement(SMALL_MODEL, cpu_ram_gib=40.0, allow_cpu=False),
        _host(ram_gib=20.0),
        estimate_footprint(SMALL),
        OccupancySnapshot(),
    )
    assert placement.device == "unavailable"
    assert "RAM" in placement.detail


def test_vllm_occupancy_blocks_ollama_without_service_control() -> None:
    occupancy = OccupancySnapshot(vllm_ready=True)
    blocked = place_requirement(
        ModelRequirement(SMALL_MODEL, allow_cpu=False),
        _host(),
        estimate_footprint(SMALL),
        occupancy,
    )
    fallback = place_requirement(
        ModelRequirement(SMALL_MODEL, allow_cpu=True),
        _host(),
        estimate_footprint(SMALL),
        occupancy,
    )
    assert blocked.device == "unavailable"
    assert "vLLM" in blocked.detail
    assert fallback.device == "cpu"


def test_vllm_backend_without_running_service_does_not_take_cuda() -> None:
    occupancy = OccupancySnapshot(vllm_ready=False)
    blocked = place_requirement(
        ModelRequirement("fixture-chat", backend="vllm", allow_cpu=False),
        _host(),
        estimate_footprint(SMALL),
        occupancy,
    )
    fallback = place_requirement(
        ModelRequirement("fixture-chat", backend="vllm", allow_cpu=True),
        _host(),
        estimate_footprint(SMALL),
        occupancy,
    )
    start = place_requirement(
        ModelRequirement(
            "fixture-chat", backend="vllm", allow_cpu=False, allow_service_control=True
        ),
        _host(),
        estimate_footprint(SMALL),
        occupancy,
    )
    assert blocked.device == "unavailable"
    assert "vLLM is not running" in blocked.detail
    assert fallback.device == "cpu"
    assert start.device == "cuda"


def test_session_serializes_cuda_and_cpu_does_not_take_the_lease(tmp_path: Path) -> None:
    scheduler = _scheduler(tmp_path, _host())
    holding = Event()
    released = Event()
    order: list[str] = []

    def gpu_holder() -> None:
        with scheduler.session(ModelRequirement("small-a"), SMALL):
            order.append("gpu")
            holding.set()
            released.wait(timeout=2.0)

    thread = Thread(target=gpu_holder)
    thread.start()
    assert holding.wait(timeout=2.0)
    with scheduler.session(ModelRequirement("qwen3.8:27b", allow_cpu=True), LARGE) as cpu:
        assert cpu.placement.device == "cpu"
        order.append("cpu")
    released.set()
    thread.join(timeout=2.0)
    assert order == ["gpu", "cpu"]


def test_incompatible_cuda_workloads_do_not_overlap(tmp_path: Path) -> None:
    scheduler = _scheduler(tmp_path, _host())
    holding = Event()
    overlapping = []

    def first() -> None:
        with scheduler.session(ModelRequirement("one"), SMALL):
            holding.set()
            overlapping.append("one")
            sleep(0.2)
            overlapping.append("one-done")

    thread = Thread(target=first)
    thread.start()
    assert holding.wait(timeout=2.0)
    with scheduler.session(ModelRequirement("two"), SMALL):
        overlapping.append("two")
    thread.join(timeout=2.0)
    assert overlapping == ["one", "one-done", "two"]


def test_cancellation_releases_lease_for_the_next_caller(tmp_path: Path) -> None:
    scheduler = _scheduler(tmp_path, _host())
    cancel = Event()
    started = Event()

    def cancelled_holder() -> None:
        with (
            pytest.raises(RuntimeError, match="cancelled work"),
            scheduler.session(ModelRequirement("held"), SMALL, cancel=cancel),
        ):
            started.set()
            cancel.set()
            raise RuntimeError("cancelled work")

    thread = Thread(target=cancelled_holder)
    thread.start()
    assert started.wait(timeout=2.0)
    thread.join(timeout=2.0)
    with scheduler.session(ModelRequirement("next"), SMALL) as granted:
        assert granted.placement.device == "cuda"
        assert granted.lease is not None


def test_cancel_while_waiting_does_not_steal_the_lease(tmp_path: Path) -> None:
    scheduler = _scheduler(tmp_path, _host())
    holding = Event()
    cancel = Event()

    def holder() -> None:
        with scheduler.session(ModelRequirement("owner"), SMALL):
            holding.set()
            sleep(0.3)

    thread = Thread(target=holder)
    thread.start()
    assert holding.wait(timeout=2.0)
    cancel.set()
    with (
        pytest.raises(LeaseCancelledError),
        scheduler.session(ModelRequirement("waiter"), SMALL, cancel=cancel),
    ):
        raise AssertionError("waiter must not enter")
    thread.join(timeout=2.0)


def test_fit_rejection_writes_rejected_lease_and_telemetry(tmp_path: Path) -> None:
    scheduler = _scheduler(tmp_path, _host())
    with (
        pytest.raises(ModelFitError, match="insufficient"),
        scheduler.session(ModelRequirement("qwen3.8:27b", allow_cpu=False), LARGE),
    ):
        pass
    ledger = (tmp_path / "services" / "inference" / "ctl.resource_lease.jsonl").read_text(
        encoding="utf-8"
    )
    events = (tmp_path / "runs" / "run-1" / "telemetry" / "resource-events.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"status": "rejected"' in ledger
    assert "rejected" in events
    assert "secret" not in events


def test_unload_and_requested_vllm_stop(tmp_path: Path) -> None:
    pytest.importorskip("httpx")
    vllm = RecordingVllmController(running=True)
    state = FakeState(models=default_models("ollama"), loaded=["fixture-embed"])
    with serve("ollama", state) as base_url:
        client = LocalInferenceClient("ollama", base_url, default_model="fixture-chat", timeout=2.0)
        try:
            occupancy = OccupancyProbe(client=client, vllm=vllm)
            scheduler = _scheduler(tmp_path, _host(), client=client, vllm=vllm, occupancy=occupancy)
            requirement = ModelRequirement(
                "fixture-chat", allow_service_control=True, allow_unload=True
            )
            with scheduler.session(requirement, SMALL) as granted:
                assert granted.placement.device == "cuda"
                assert vllm.stops == 1
                assert "fixture-embed" in granted.occupancy.ollama_loaded
                assert "unloaded fixture-embed" in granted.actions
                assert "fixture-embed" not in state.loaded
        finally:
            client.close()


def test_vllm_session_starts_only_when_requested(tmp_path: Path) -> None:
    vllm = RecordingVllmController(running=False)
    scheduler = _scheduler(tmp_path, _host(), vllm=vllm)
    with scheduler.session(
        ModelRequirement("small", backend="vllm", allow_cpu=True), SMALL
    ) as granted:
        assert granted.placement.device == "cpu"
        assert vllm.starts == 0
    with scheduler.session(
        ModelRequirement("small", backend="vllm", allow_cpu=False, allow_service_control=True),
        SMALL,
    ) as granted:
        assert granted.placement.device == "cuda"
        assert vllm.starts == 1
