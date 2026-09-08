"""Cross-command publication integrity regressions from checkpoint 0046."""

from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.pipeline.actions import remaining_plan, update_context
from arxiv_int.pipeline.control.artifacts import InjectedCrash
from arxiv_int.pipeline.errors import StaleUpstreamError
from arxiv_int.pipeline.fixtures import fixture_registry
from arxiv_int.pipeline.orchestrate import Orchestrator
from arxiv_int.pipeline.persist import load_json, save_context
from arxiv_int.pipeline.publish.finalize import finalize_status
from arxiv_int.pipeline.publish.pointer import load_active_generation
from arxiv_int.pipeline.publish.profiles import FIXTURE_PROFILE
from arxiv_int.pipeline.quality_bound import FixtureQuality
from tests.pipeline.orchestration.conftest import make_context
from tests.pipeline.publish.test_publish import _plan


@pytest.mark.parametrize("damage", ["payload", "manifest", "missing", "stale"])
def test_finalize_rechecks_artifacts_and_invalidation(tmp_path: Path, damage: str) -> None:
    registry, _ = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    status = orchestrator.execute_plan(context, _plan(registry))
    directory = Path(status.executions[0].directory)
    if damage == "stale":
        orchestrator.invalidate("alpha")
    elif damage == "missing":
        (directory / "stage.json").unlink()
    else:
        (directory / ("stage.json" if damage == "payload" else "manifest.json")).write_text("bad")
    document, code = finalize_status(context, status, FIXTURE_PROFILE)
    assert code != 0
    assert not document.active
    assert load_active_generation(context.runs_dir) is None


class WrongGenerationQuality(FixtureQuality):
    def validate(self, dataset, files, generation_id):
        return replace(super().validate(dataset, files, generation_id), generation_id="old")

    def transform(self, select, generation_id, run_id):
        return replace(super().transform(select, generation_id, run_id), generation_id="old")


@pytest.mark.parametrize("kind", ["validation", "transform"])
def test_stage_refuses_quality_for_another_generation(tmp_path: Path, kind: str) -> None:
    registry, _ = fixture_registry(
        validators=("beta",) if kind == "validation" else (),
        dbt_select=("gamma",) if kind == "transform" else (),
    )
    context = make_context(tmp_path)
    status = Orchestrator(
        registry, context.runs_dir, quality=WrongGenerationQuality()
    ).execute_plan(context, _plan(registry))
    assert status.halted
    assert finalize_status(context, status, FIXTURE_PROFILE)[1] != 0


def test_fresh_command_force_preserves_accepted_bytes(tmp_path: Path) -> None:
    registry, _ = fixture_registry()
    context = make_context(tmp_path)
    first = Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    old = Path(first.executions[0].directory)
    before = {p.name: p.read_bytes() for p in old.iterdir()}
    forced = Orchestrator(registry, context.runs_dir).execute_plan(
        context, _plan(registry), force=True
    )
    assert not forced.halted
    assert forced.executions[0].directory != str(old)
    assert {p.name: p.read_bytes() for p in old.iterdir()} == before


def test_atomic_stage_cannot_borrow_unrelated_upstream(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path)
    Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    changed = replace(update_context(context), parameters={"mode": "different"})
    save_context(changed)
    with pytest.raises(StaleUpstreamError):
        Orchestrator(registry, context.runs_dir).execute_plan(
            changed, _plan(registry, from_stage="gamma", to_stage="gamma")
        )
    assert runners["gamma"].calls == 1


def test_resume_reexecutes_partial_stage(tmp_path: Path) -> None:
    registry, _ = fixture_registry(gamma_outcome="partial")
    context = make_context(tmp_path)
    first = Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    healthy, runners = fixture_registry()
    plan = remaining_plan(_plan(healthy), first)
    resumed = Orchestrator(healthy, context.runs_dir).execute_plan(context, plan)
    assert runners["gamma"].calls == 1
    assert not resumed.halted


@pytest.mark.parametrize(
    "point",
    [
        "after-manifest",
        "after-catalog-write",
        "after-catalog-replace",
        "after-generation-write",
        "after-generation-replace",
    ],
)
def test_crash_keeps_a_coherent_pointer_and_resumes_without_work(
    tmp_path: Path, point: str
) -> None:
    registry, runners = fixture_registry()
    first = make_context(tmp_path)
    first_status = Orchestrator(registry, first.runs_dir).execute_plan(first, _plan(registry))
    assert finalize_status(first, first_status, FIXTURE_PROFILE)[1] == 0
    second = update_context(first)
    save_context(second)
    status = Orchestrator(registry, second.runs_dir).execute_plan(second, _plan(registry))

    def crash(actual: str) -> None:
        if actual == point:
            raise InjectedCrash(point)

    with pytest.raises(InjectedCrash):
        finalize_status(second, status, FIXTURE_PROFILE, injector=crash)
    pointer = load_active_generation(first.runs_dir)
    catalog = load_json(first.runs_dir / pointer["catalog"])
    assert catalog["generation_id"] == pointer["generation_id"]
    assert pointer["run_id"] == (
        second.run_id if point == "after-generation-replace" else first.run_id
    )
    assert finalize_status(second, status, FIXTURE_PROFILE)[1] == 0
    assert all(runners[name].calls == 1 for name in ("alpha", "beta", "gamma"))
    assert all(item.cache_hit for item in status.executions)


def test_cancellation_in_last_worker_cannot_activate(tmp_path: Path) -> None:
    from arxiv_int.pipeline.cancel import CancelToken

    token = CancelToken()
    registry, _ = fixture_registry(gamma_hook=lambda _: token.cancel())
    context = make_context(tmp_path)
    status = Orchestrator(registry, context.runs_dir, cancel=token).execute_plan(
        context, _plan(registry)
    )
    document, code = finalize_status(context, status, FIXTURE_PROFILE)
    assert code == 130
    assert not document.active


class MissingGlobalQuality(FixtureQuality):
    def checks(self):
        return ()


def test_missing_global_checks_never_start_workers(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path)
    status = Orchestrator(registry, context.runs_dir, quality=MissingGlobalQuality()).execute_plan(
        context, _plan(registry)
    )
    assert status.halted
    assert all(runner.calls == 0 for runner in runners.values())
    assert finalize_status(context, status, FIXTURE_PROFILE)[1] != 0


@pytest.mark.parametrize("outcome", ["partial", "failed"])
def test_progress_manifest_agrees_with_halted_stage(tmp_path: Path, outcome: str) -> None:
    registry, _ = fixture_registry(gamma_outcome=outcome)
    context = make_context(tmp_path)
    status = Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    assert status.halted
    observed = load_json(context.runs_dir / context.run_id / "logs" / "observability-manifest.json")
    assert observed["outcome"] == outcome
