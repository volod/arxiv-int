"""Forced work budgets and stale forecasts use the execution cache policy."""

from pathlib import Path

import pytest

from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.forecast.commands import bind_forecast, forecast_bound_run
from arxiv_int.pipeline.forecast.errors import StaleForecastError
from arxiv_int.pipeline.run.fixtures import fixture_registry
from arxiv_int.runtime import load_runtime_config
from tests.pipeline.conftest import make_context
from tests.pipeline.forecast.conftest import plentiful_inspect
from tests.pipeline.publish.test_publish import _plan


def test_forced_work_cannot_use_a_cache_hit_forecast(tmp_path: Path) -> None:
    registry, _ = fixture_registry()
    context = make_context(tmp_path)
    (context.project_root / "pyproject.toml").write_text("[project]\nname = 'fixture'\n")
    config = load_runtime_config(
        project_root=context.project_root,
        environment={**context.secret_free, "PGDATA_DIR": str(tmp_path / "pgdata")},
    )
    plan = _plan(registry)
    assert not Orchestrator(registry, context.runs_dir).execute_plan(context, plan).halted
    cached = forecast_bound_run(context, config, registry, inspector=plentiful_inspect)
    assert all(stage.cache_hit for stage in cached.stages)
    with pytest.raises(StaleForecastError, match="cache plan"):
        bind_forecast(context, registry, plan, config, inspector=plentiful_inspect, force=True)
    forced = forecast_bound_run(context, config, registry, inspector=plentiful_inspect, force=True)
    assert all(not stage.cache_hit for stage in forced.stages)
    bound, _guard = bind_forecast(
        context, registry, plan, config, inspector=plentiful_inspect, force=True
    )
    assert bound.fingerprint == forced.fingerprint
