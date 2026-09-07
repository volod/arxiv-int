"""Zero-history ranges, replay, device dedup, and atomic/aggregate agreement."""

from arxiv_int.pipeline.forecast.engine import build_forecast, fingerprint_inputs
from arxiv_int.pipeline.forecast.inputs import CacheHitPlan
from tests.pipeline.forecast.conftest import make_devices, make_inputs, make_inventory


def test_zero_history_sample_is_conservative_and_low_confidence() -> None:
    document = build_forecast(make_inputs(inventory=make_inventory(source="sample")))
    assert document.confidence == "low"
    assert document.decision == "degraded"
    assert document.inventory_source == "sample"
    indexed = 4_096
    assert document.outputs.normalized.lower >= int(indexed * 2.5 * 0.4)
    assert document.outputs.normalized.upper <= int(indexed * 4.0)
    assert document.time.lower_seconds < document.time.upper_seconds
    assert "archive-organization" in document.excluded
    names = {item.name for item in document.coefficients}
    assert "amplification_lower" in names
    assert all(
        item.source in {"envelope", "sample", "declared", "telemetry"}
        for item in document.coefficients
    )


def test_estimates_replay_from_captured_evidence() -> None:
    inputs = make_inputs()
    first = build_forecast(inputs)
    second = build_forecast(inputs)
    assert first.fingerprint == second.fingerprint == fingerprint_inputs(inputs)
    assert first.decision == second.decision
    assert first.outputs.normalized == second.outputs.normalized
    assert first.time == second.time
    assert [item.stage for item in first.stages] == [item.stage for item in second.stages]


def test_shared_devices_are_budgeted_once() -> None:
    shared = build_forecast(make_inputs(devices=make_devices(shared_results=True)))
    split = build_forecast(make_inputs(devices=make_devices(shared_results=False)))
    results = next(item for item in shared.devices if "RESULTS_DIR" in item.roots)
    assert "RUNS_DIR" in results.roots
    assert results.device_id == "8:1"
    split_results = next(item for item in split.devices if "RESULTS_DIR" in item.roots)
    split_runs = next(item for item in split.devices if "RUNS_DIR" in item.roots)
    assert "RUNS_DIR" not in split_results.roots
    assert results.peak.upper == split_results.peak.upper + split_runs.peak.upper
    assert results.peak.upper == split_results.peak.upper + split_runs.peak.upper
    assert len([item for item in shared.devices if item.device_id == "8:1"]) == 1


def test_atomic_and_aggregate_agree_on_captured_inputs() -> None:
    inputs = make_inputs(run_id="run-agg")
    aggregate = build_forecast(inputs)
    atomic = build_forecast(inputs)
    assert aggregate.fingerprint == atomic.fingerprint
    assert aggregate.decision == atomic.decision
    assert aggregate.outputs.wal == atomic.outputs.wal
    assert aggregate.outputs.temp == atomic.outputs.temp
    assert aggregate.outputs.staging == atomic.outputs.staging
    assert aggregate.outputs.rebuild == atomic.outputs.rebuild
    assert aggregate.outputs.rollback == atomic.outputs.rollback


def test_cache_hit_stage_has_near_zero_time_and_output() -> None:
    cache = CacheHitPlan((("alpha", True, 128), ("beta", False, 0), ("gamma", False, 0)))
    document = build_forecast(make_inputs(cache=cache))
    alpha = next(item for item in document.stages if item.stage == "alpha")
    beta = next(item for item in document.stages if item.stage == "beta")
    assert alpha.cache_hit
    assert alpha.work.recomputed == 0
    assert alpha.time.upper_seconds <= 1.0
    assert not beta.cache_hit
    assert beta.work.recomputed > 0
