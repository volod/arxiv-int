"""Fixture DAG execution: skip, failure halt, aggregate vs atomic, resume, force."""

from pathlib import Path

import pytest

from arxiv_int.pipeline.dag.actions import fixture_plan, remaining_plan
from arxiv_int.pipeline.dag.cancel import CancelToken
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.dag.registry import ResourceEstimate, StageRegistry, StageSpec
from arxiv_int.pipeline.run.errors import StaleUpstreamError, UnregisteredStageError
from arxiv_int.pipeline.run.fixtures import (
    FIXTURE_OPTIONAL,
    FIXTURE_PROFILE_STAGES,
    fixture_registry,
)
from arxiv_int.pipeline.run.persist import load_status
from tests.pipeline.conftest import make_context


def _plan(registry: StageRegistry, **kwargs: object):
    return fixture_plan(
        registry,
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
        **kwargs,
    )


def test_aggregate_run_produces_lineage_and_skips_on_rerun(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    plan = _plan(registry)
    first = orchestrator.execute_plan(context, plan)
    assert [item.stage for item in first.executions] == ["alpha", "beta", "gamma"]
    assert not first.halted
    assert first.not_selected == ("omega",)
    assert first.lineage
    second = orchestrator.execute_plan(context, plan)
    assert all(item.cache_hit and not item.worker_invoked for item in second.executions)
    assert runners["alpha"].calls == 1
    assert runners["gamma"].calls == 1


def test_failure_halts_downstream_gamma(tmp_path: Path) -> None:
    registry, runners = fixture_registry(fail_gamma=True)
    context = make_context(tmp_path)
    result = Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    assert result.halted
    assert [item.stage for item in result.executions] == ["alpha", "beta", "gamma"]
    assert result.executions[-1].status == "failed"
    assert runners["omega"].calls == 0


def test_aggregate_and_atomic_refuse_the_same_missing_upstream(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    gamma_only = _plan(registry, from_stage="gamma", to_stage="gamma")
    with pytest.raises(StaleUpstreamError):
        orchestrator.execute_plan(context, gamma_only)
    atomic = Orchestrator(registry, context.runs_dir)
    with pytest.raises(StaleUpstreamError):
        atomic.execute_plan(context, gamma_only)


def test_aggregate_and_atomic_produce_equivalent_outcomes(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    agg = Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    atomic_registry, _atomic = fixture_registry()
    atomic_context = make_context(tmp_path / "atomic", text="one")
    atomic = Orchestrator(atomic_registry, atomic_context.runs_dir)
    stages: list[str] = []
    outcomes: list[str] = []
    for name in ("alpha", "beta", "gamma"):
        result = atomic.execute_plan(
            atomic_context, _plan(atomic_registry, from_stage=name, to_stage=name)
        )
        assert not result.halted
        stages.extend(item.stage for item in result.executions)
        outcomes.extend(item.outcome for item in result.executions)
    assert [item.stage for item in agg.executions] == stages == ["alpha", "beta", "gamma"]
    assert [item.outcome for item in agg.executions] == outcomes
    assert len(agg.lineage) == 2
    assert len(load_status(atomic_context.runs_dir, atomic_context.run_id).lineage) >= 1


def test_unregistered_required_stages_fail_before_work(tmp_path: Path) -> None:
    estimate = ResourceEstimate()
    registry = StageRegistry(
        (
            StageSpec("alpha", "1", (), (), (), estimate, (), (), None),
            StageSpec("beta", "1", ("alpha",), ("alpha",), (), estimate, (), (), None),
        )
    )
    context = make_context(tmp_path)
    with pytest.raises(UnregisteredStageError, match="alpha"):
        Orchestrator(registry, context.runs_dir).execute_plan(
            context, fixture_plan(registry, profile_stages=("alpha", "beta"))
        )


def test_resume_after_cancel_continues_remaining_stages(tmp_path: Path) -> None:
    token = CancelToken()
    registry, runners = fixture_registry()
    runners["alpha"]._hook = lambda _context: token.cancel()
    context = make_context(tmp_path)
    plan = _plan(registry)
    first = Orchestrator(registry, context.runs_dir, cancel=token).execute_plan(context, plan)
    assert first.halted
    assert [item.stage for item in first.executions] == ["alpha"]
    remaining = remaining_plan(plan, load_status(context.runs_dir, context.run_id))
    resumed = Orchestrator(registry, context.runs_dir).execute_plan(context, remaining)
    assert not resumed.halted
    assert [item.stage for item in resumed.executions] == ["beta", "gamma"]
    assert runners["alpha"].calls == 1
    assert runners["beta"].calls == 1


def test_force_writes_a_new_attempt_without_overwriting(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    plan = _plan(registry)
    first = orchestrator.execute_plan(context, plan)
    forced = orchestrator.execute_plan(context, plan, force=True)
    first_dir = first.executions[0].directory
    forced_dir = forced.executions[0].directory
    assert first_dir is not None and forced_dir is not None
    assert first_dir != forced_dir
    assert Path(first_dir).joinpath("stage.json").is_file()
    assert Path(forced_dir).joinpath("stage.json").is_file()
    assert forced.executions[0].attempt == first.executions[0].attempt + 1
    assert not forced.executions[0].cache_hit
