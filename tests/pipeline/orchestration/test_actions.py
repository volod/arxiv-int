"""Update, invalidate, rebuild, prune dry-run, and quality-boundary refusal."""

from pathlib import Path

import pytest

from arxiv_int.data_quality.model import STATUS_NOT_RUN
from arxiv_int.pipeline.actions import (
    apply_prune_plan,
    build_prune_plan,
    fixture_plan,
    rebuild_context,
    update_context,
)
from arxiv_int.pipeline.fixtures import FIXTURE_OPTIONAL, FIXTURE_PROFILE_STAGES, fixture_registry
from arxiv_int.pipeline.orchestrate import Orchestrator
from arxiv_int.pipeline.persist import save_context
from arxiv_int.pipeline.quality_bound import FixtureQuality
from tests.pipeline.orchestration.conftest import make_context


def _plan(registry: object) -> object:
    return fixture_plan(
        registry,  # type: ignore[arg-type]
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
    )


def test_update_reruns_changed_source_and_skips_unchanged(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path, text="one")
    orchestrator = Orchestrator(registry, context.runs_dir)
    first = orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    assert not first.halted
    (context.silos[0].root / "doc.txt").write_text("two", encoding="utf-8")
    updated = update_context(context)
    save_context(updated)
    second = orchestrator.execute_plan(updated, _plan(registry))  # type: ignore[arg-type]
    assert not second.halted
    assert not any(item.cache_hit for item in second.executions)
    assert runners["alpha"].calls == 2


def test_targeted_invalidate_marks_descendants_stale(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    marked = orchestrator.invalidate("beta")
    assert marked
    third = orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    rerun = [item.stage for item in third.executions if not item.cache_hit]
    assert "beta" in rerun
    assert "gamma" in rerun
    assert runners["beta"].calls == 2


def test_rebuild_uses_a_new_generation_without_cache(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    first = orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    rebuilt = rebuild_context(context)
    save_context(rebuilt)
    second = orchestrator.execute_plan(rebuilt, _plan(registry), force=True)  # type: ignore[arg-type]
    assert rebuilt.run_id != context.run_id
    assert rebuilt.generation_id != context.generation_id
    assert not any(item.cache_hit for item in second.executions)
    first_dir = first.executions[0].directory
    second_dir = second.executions[0].directory
    assert first_dir and second_dir and first_dir != second_dir
    assert Path(first_dir).joinpath("stage.json").is_file()


def test_prune_dry_run_lists_stale_bytes_and_apply_needs_a_plan(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    orchestrator.invalidate("alpha")
    plan = build_prune_plan(context.runs_dir)
    assert plan.bytes > 0
    assert plan.entries
    listed = [Path(entry.directory) for entry in plan.entries]
    assert all(path.is_dir() for path in listed)
    fake = context.runs_dir / "prune-plans" / "prune-missing.json"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_text('{"directories": [], "fingerprint": "nope"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        apply_prune_plan(context.runs_dir, "prune-missing")
    apply_prune_plan(context.runs_dir, plan.plan_id)
    assert all(path.is_dir() for path in listed)


def test_failed_and_not_run_quality_halt_downstream(tmp_path: Path) -> None:
    registry, runners = fixture_registry(validators=("documents",))
    context = make_context(tmp_path)
    quality = FixtureQuality(validation_status=STATUS_NOT_RUN)
    result = Orchestrator(registry, context.runs_dir, quality=quality).execute_plan(
        context,
        _plan(registry),  # type: ignore[arg-type]
    )
    assert result.halted
    assert quality.validated == ["documents"]
    assert runners["gamma"].calls == 0


def test_failed_dbt_selection_halts_downstream(tmp_path: Path) -> None:
    registry, runners = fixture_registry(dbt_select=("marts.example",))
    context = make_context(tmp_path)
    quality = FixtureQuality(transform_status="not-run")
    result = Orchestrator(registry, context.runs_dir, quality=quality).execute_plan(
        context,
        _plan(registry),  # type: ignore[arg-type]
    )
    assert result.halted
    assert quality.transformed == [("marts.example",)]
    assert runners["omega"].calls == 0
