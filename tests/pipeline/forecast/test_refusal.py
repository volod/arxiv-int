"""Inaccessible paths, reserve shortfalls, stale forecasts, and config drift."""

from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.pipeline.dag.graph import StagePlan
from arxiv_int.pipeline.forecast.engine import build_forecast
from arxiv_int.pipeline.forecast.errors import StaleForecastError
from arxiv_int.pipeline.forecast.persist import require_fresh_forecast, save_forecast
from tests.pipeline.conftest import make_context
from tests.pipeline.forecast.conftest import make_devices, make_inputs


def test_inaccessible_paths_block() -> None:
    document = build_forecast(make_inputs(devices=make_devices(accessible=False)))
    assert document.decision == "blocked"
    assert any("inaccessible" in action for action in document.actions)


def test_upper_bound_plus_reserve_shortfall_blocks() -> None:
    document = build_forecast(make_inputs(devices=make_devices(free_bytes=10)))
    assert document.decision == "blocked"
    assert any("exceeds free" in action for action in document.actions)


def test_changed_configuration_cannot_reuse_stale_forecast(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    inputs = make_inputs(
        forecast_id=context.run_id,
        run_id=context.run_id,
        config_fingerprint=context.config_fingerprint,
        source_snapshot=context.source_snapshot,
    )
    document = build_forecast(inputs)
    save_forecast(context.runs_dir, document)
    plan = StagePlan(("alpha", "beta", "gamma"), (), ("omega",))
    require_fresh_forecast(context, plan, inputs)
    drifted = replace(context, config_fingerprint="other-config")
    with pytest.raises(StaleForecastError, match="configuration changed"):
        require_fresh_forecast(drifted, plan, inputs)


def test_missing_forecast_is_rejected(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    inputs = make_inputs(
        forecast_id=context.run_id,
        run_id=context.run_id,
        config_fingerprint=context.config_fingerprint,
        source_snapshot=context.source_snapshot,
    )
    plan = StagePlan(("alpha",), (), ())
    with pytest.raises(StaleForecastError, match="has no forecast"):
        require_fresh_forecast(context, plan, inputs)


def test_uncovered_stage_is_rejected(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    inputs = make_inputs(
        forecast_id=context.run_id,
        run_id=context.run_id,
        config_fingerprint=context.config_fingerprint,
        source_snapshot=context.source_snapshot,
        plan=("alpha",),
    )
    save_forecast(context.runs_dir, build_forecast(inputs))
    plan = StagePlan(("alpha", "facts"), (), ())
    with pytest.raises(StaleForecastError, match="does not cover"):
        require_fresh_forecast(context, plan, inputs)
