"""Knowledge-base publication, activation, crash recovery, and exit codes."""

from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.pipeline.actions import fixture_plan, remaining_plan
from arxiv_int.pipeline.cancel import CancelToken
from arxiv_int.pipeline.control.artifacts import InjectedCrash
from arxiv_int.pipeline.errors import PreflightRefusedError, StaleUpstreamError
from arxiv_int.pipeline.fixtures import FIXTURE_OPTIONAL, FIXTURE_PROFILE_STAGES, fixture_registry
from arxiv_int.pipeline.orchestrate import Orchestrator
from arxiv_int.pipeline.persist import load_status, save_context
from arxiv_int.pipeline.publish.finalize import finalize_status, write_report
from arxiv_int.pipeline.publish.model import EXIT_BY_STATUS
from arxiv_int.pipeline.publish.pointer import (
    ActivationRefusedError,
    activate_generation,
    load_active_generation,
    reconcile_orphans,
)
from arxiv_int.pipeline.publish.preflight import preflight_run
from arxiv_int.pipeline.publish.profiles import FIXTURE_PROFILE
from tests.pipeline.orchestration.conftest import make_context


def _plan(registry, **kwargs):
    return fixture_plan(
        registry,
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
        **kwargs,
    )


def _finalize(tmp_path: Path, **fixture_kwargs):
    registry, runners = fixture_registry(**fixture_kwargs)
    context = make_context(tmp_path)
    status = Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    document, code = finalize_status(context, status, FIXTURE_PROFILE)
    return context, status, document, code, runners


def test_complete_fixture_run_activates_and_exits_zero(tmp_path: Path) -> None:
    context, status, document, code, _runners = _finalize(tmp_path)
    assert not status.halted
    assert document.status == "succeeded"
    assert document.active
    assert code == 0
    assert EXIT_BY_STATUS[document.status] == 0
    pointer = load_active_generation(context.runs_dir)
    assert pointer is not None
    assert pointer["run_id"] == context.run_id
    assert (context.runs_dir / context.run_id / "reports" / "index.html").is_file()
    assert status.not_selected == ("omega",)
    omega = next(item for item in document.outputs if item.family == "omega")
    assert omega.outcome == "not-selected"


def test_valid_empty_required_family_still_succeeds(tmp_path: Path) -> None:
    _context, _status, document, code, _runners = _finalize(tmp_path, gamma_outcome="empty")
    assert document.status == "succeeded"
    assert code == 0
    assert document.active
    gamma = next(item for item in document.outputs if item.family == "gamma")
    assert gamma.outcome == "empty"


def test_partial_run_cannot_replace_complete_generation(tmp_path: Path) -> None:
    first, _status, _first_doc, first_code, _runners = _finalize(tmp_path / "complete")
    assert first_code == 0
    registry, _runners = fixture_registry(gamma_outcome="partial")
    second = make_context(tmp_path / "partial")
    second = replace(second, runs_dir=first.runs_dir)
    save_context(second)
    status = Orchestrator(registry, second.runs_dir).execute_plan(second, _plan(registry))
    document, code = finalize_status(second, status, FIXTURE_PROFILE)
    assert document.status == "partial"
    assert code == 2
    assert not document.active
    pointer = load_active_generation(first.runs_dir)
    assert pointer is not None
    assert pointer["run_id"] == first.run_id
    assert pointer["run_id"] != second.run_id
    with pytest.raises(ActivationRefusedError):
        activate_generation(first.runs_dir, document)


def test_failed_run_writes_diagnostic_without_activation(tmp_path: Path) -> None:
    _context, status, document, code, _runners = _finalize(tmp_path, fail_gamma=True)
    assert status.halted
    assert document.status == "failed"
    assert code == 1
    assert not document.active
    assert load_active_generation(_context.runs_dir) is None
    assert (_context.runs_dir / _context.run_id / "reports" / "report.json").is_file()


def test_unreadable_archive_is_blocked_preflight(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    missing = tmp_path / "gone"
    silos = replace(context.silos[0], root=missing)
    context = replace(context, silos=(silos,))
    with pytest.raises(PreflightRefusedError):
        preflight_run(context)


def test_interrupted_run_is_resumable_and_does_not_activate(tmp_path: Path) -> None:
    token = CancelToken()
    registry, runners = fixture_registry()
    runners["alpha"]._hook = lambda _context: token.cancel()
    context = make_context(tmp_path)
    plan = _plan(registry)
    first = Orchestrator(registry, context.runs_dir, cancel=token).execute_plan(context, plan)
    document, code = finalize_status(context, first, FIXTURE_PROFILE)
    assert first.halt_reason == "interrupted"
    assert document.status == "interrupted"
    assert code == 130
    assert not document.active
    remaining = remaining_plan(plan, load_status(context.runs_dir, context.run_id))
    resumed = Orchestrator(registry, context.runs_dir).execute_plan(context, remaining)
    document, code = finalize_status(
        context, load_status(context.runs_dir, context.run_id), FIXTURE_PROFILE
    )
    assert not resumed.halted
    assert document.status == "succeeded"
    assert code == 0
    assert document.active


def test_stale_dependency_still_refuses_before_finalize(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    with pytest.raises(StaleUpstreamError):
        Orchestrator(registry, context.runs_dir).execute_plan(
            context, _plan(registry, from_stage="gamma", to_stage="gamma")
        )


def test_crash_after_manifest_keeps_prior_complete_generation(tmp_path: Path) -> None:
    first, _status, _doc, code, _runners = _finalize(tmp_path / "first")
    assert code == 0
    registry, _runners = fixture_registry()
    second = make_context(tmp_path / "second")
    second = replace(second, runs_dir=first.runs_dir)
    save_context(second)
    status = Orchestrator(registry, second.runs_dir).execute_plan(second, _plan(registry))

    def boom(point: str) -> None:
        if point == "after-manifest":
            raise InjectedCrash(point)

    with pytest.raises(InjectedCrash):
        finalize_status(second, status, FIXTURE_PROFILE, injector=boom)
    pointer = load_active_generation(first.runs_dir)
    assert pointer is not None
    assert pointer["run_id"] == first.run_id


def test_crash_after_catalog_write_reconciles_orphans(tmp_path: Path) -> None:
    first, _status, _doc, code, _runners = _finalize(tmp_path / "first")
    assert code == 0
    registry, _runners = fixture_registry()
    second = make_context(tmp_path / "second")
    second = replace(second, runs_dir=first.runs_dir)
    save_context(second)
    status = Orchestrator(registry, second.runs_dir).execute_plan(second, _plan(registry))

    def boom(point: str) -> None:
        if point == "after-catalog-write":
            raise InjectedCrash(point)

    with pytest.raises(InjectedCrash):
        finalize_status(second, status, FIXTURE_PROFILE, injector=boom)
    pointer = load_active_generation(first.runs_dir)
    assert pointer is not None
    assert pointer["run_id"] == first.run_id
    removed = reconcile_orphans(first.runs_dir)
    assert removed >= 1
    assert not list(first.runs_dir.glob(".*.tmp"))


def test_report_rendering_cannot_activate_a_generation(tmp_path: Path) -> None:
    context, _status, _document, _code, _runners = _finalize(tmp_path / "complete")
    registry, _runners = fixture_registry(fail_gamma=True)
    failed = make_context(tmp_path / "failed")
    failed = replace(failed, runs_dir=context.runs_dir)
    save_context(failed)
    failed_status = Orchestrator(registry, failed.runs_dir).execute_plan(failed, _plan(registry))
    failed_doc, code = finalize_status(failed, failed_status, FIXTURE_PROFILE)
    assert code == 1
    write_report(failed.runs_dir, failed_doc)
    pointer = load_active_generation(context.runs_dir)
    assert pointer is not None
    assert pointer["run_id"] == context.run_id
    assert (failed.runs_dir / failed.run_id / "reports" / "index.html").is_file()


def test_aggregate_and_atomic_finalize_to_the_same_logical_state(tmp_path: Path) -> None:
    _agg_ctx, agg_status, agg_doc, agg_code, _runners = _finalize(tmp_path / "agg")
    registry, _runners = fixture_registry()
    atomic = make_context(tmp_path / "atomic")
    orchestrator = Orchestrator(registry, atomic.runs_dir)
    for name in ("alpha", "beta", "gamma"):
        result = orchestrator.execute_plan(atomic, _plan(registry, from_stage=name, to_stage=name))
        assert not result.halted
    atomic_status = load_status(atomic.runs_dir, atomic.run_id)
    atomic_doc, atomic_code = finalize_status(atomic, atomic_status, FIXTURE_PROFILE)
    assert agg_code == atomic_code == 0
    assert [item.outcome for item in agg_doc.outputs] == [
        item.outcome for item in atomic_doc.outputs
    ]
    assert agg_doc.coverage == atomic_doc.coverage
    assert agg_status.lineage
    assert atomic_status.lineage
