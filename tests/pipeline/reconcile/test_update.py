"""Incremental update, rename, rebuild, and quality-gated activation fixtures."""

from pathlib import Path

from arxiv_int.pipeline.control.quality import QualityCheck, activation_decision
from arxiv_int.pipeline.dag.actions import fixture_plan, rebuild_context, update_context
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.publish.pointer import ActivationRefusedError
from arxiv_int.pipeline.reconcile.activate import executions_ready, require_quality_switch
from arxiv_int.pipeline.reconcile.commands import prepare_update, record_rebuild
from arxiv_int.pipeline.reconcile.lineage import lineage_matches
from arxiv_int.pipeline.reconcile.persist import load_manifest
from arxiv_int.pipeline.run.fixtures import (
    FIXTURE_OPTIONAL,
    FIXTURE_PROFILE_STAGES,
    fixture_registry,
)
from arxiv_int.pipeline.run.persist import save_context
from tests.pipeline.conftest import make_context


def _plan(registry: object) -> object:
    return fixture_plan(
        registry,  # type: ignore[arg-type]
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
    )


def test_noop_update_invokes_no_heavy_workers(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path, text="one")
    orchestrator = Orchestrator(registry, context.runs_dir)
    first = orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    assert not first.halted
    updated = update_context(context)
    save_context(updated)
    prepare_update(context, updated, orchestrator)
    second = orchestrator.execute_plan(updated, _plan(registry))  # type: ignore[arg-type]
    assert all(item.cache_hit and not item.worker_invoked for item in second.executions)
    assert runners["alpha"].calls == 1
    assert load_manifest(updated.runs_dir, updated.run_id) is not None


def test_additions_touch_only_new_shards(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path, text="one")
    orchestrator = Orchestrator(registry, context.runs_dir)
    orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    (context.silos[0].root / "extra.txt").write_text("two", encoding="utf-8")
    updated = update_context(context)
    save_context(updated)
    delta, _view = prepare_update(context, updated, orchestrator)
    assert [event.kind for event in delta.events] == ["add"]
    second = orchestrator.execute_plan(updated, _plan(registry))  # type: ignore[arg-type]
    invoked = [item for item in second.executions if item.worker_invoked]
    cached = [item for item in second.executions if item.cache_hit]
    assert invoked
    assert cached
    assert runners["alpha"].calls == 2


def test_path_only_rename_avoids_content_analysis(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path, text="one")
    orchestrator = Orchestrator(registry, context.runs_dir)
    orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    source = context.silos[0].root / "doc.txt"
    source.rename(context.silos[0].root / "renamed.txt")
    updated = update_context(context)
    save_context(updated)
    delta, _view = prepare_update(context, updated, orchestrator)
    assert [event.kind for event in delta.events] == ["path-rename"]
    second = orchestrator.execute_plan(updated, _plan(registry))  # type: ignore[arg-type]
    assert all(not item.worker_invoked for item in second.executions)
    assert runners["alpha"].calls == 1


def test_change_and_remove_retract_dependent_outputs(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path, text="one")
    (context.silos[0].root / "keep.txt").write_text("keep", encoding="utf-8")
    orchestrator = Orchestrator(registry, context.runs_dir)
    orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    (context.silos[0].root / "doc.txt").unlink()
    (context.silos[0].root / "keep.txt").write_text("changed", encoding="utf-8")
    updated = update_context(context)
    save_context(updated)
    delta, view = prepare_update(context, updated, orchestrator)
    kinds = {event.kind for event in delta.events}
    assert "remove" in kinds
    assert "content-change" in kinds
    second = orchestrator.execute_plan(updated, _plan(registry))  # type: ignore[arg-type]
    assert any(item.worker_invoked for item in second.executions)
    assert runners["alpha"].calls == 3
    assert view.retracted


def test_rebuild_matches_a_clean_baseline(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path, text="one")
    orchestrator = Orchestrator(registry, context.runs_dir)
    first = orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    rebuilt = rebuild_context(context)
    save_context(rebuilt)
    second = orchestrator.execute_plan(rebuilt, _plan(registry), force=True)  # type: ignore[arg-type]
    assert not first.halted
    assert not second.halted
    report = record_rebuild(context, rebuilt)
    assert report.baseline_match
    assert report.checksums
    assert (rebuilt.runs_dir / rebuilt.run_id / "rebuild" / "report.json").is_file()


def test_quality_failure_blocks_pointer_switch() -> None:
    decision = activation_decision(
        (QualityCheck("global.required", "not-run", "global", "error", True),),
        generation_id="gen-1",
    )
    assert not decision.allowed
    try:
        require_quality_switch(decision)
    except ActivationRefusedError as error:
        assert "quality blocking" in str(error)
    else:
        raise AssertionError("expected activation refusal")
    assert not executions_ready(())


def test_dbt_source_ref_lineage_covers_artifact_edges() -> None:
    parent_map = {
        "model.arxiv_int.int_active_documents": (
            "model.arxiv_int.stg_documents",
            "model.arxiv_int.stg_source_tombstones",
        ),
        "model.arxiv_int.stg_source_tombstones": (
            "source.arxiv_int.ctl_reconcile.source_tombstone",
        ),
    }
    aliases = {
        "alpha-key": "model.arxiv_int.stg_documents",
        "tomb-key": "model.arxiv_int.stg_source_tombstones",
        "active-key": "model.arxiv_int.int_active_documents",
    }
    edges = (
        ("alpha-key", "active-key"),
        ("tomb-key", "active-key"),
        ("source.arxiv_int.ctl_reconcile.source_tombstone", "tomb-key"),
    )
    assert lineage_matches(edges, parent_map, aliases)


def test_incomplete_scan_retracts_no_active_rows(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path, text="one")
    (context.silos[0].root / "keep.txt").write_text("keep", encoding="utf-8")
    orchestrator = Orchestrator(registry, context.runs_dir)
    orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    for path in sorted(context.silos[0].root.iterdir()):
        path.unlink()
    context.silos[0].root.rmdir()
    updated = update_context(context)
    save_context(updated)
    delta, view = prepare_update(context, updated, orchestrator)
    assert delta.of_kind("remove") == ()
    assert delta.withheld_removals
    assert view.retracted == ()
    assert len(view.rows) == 2
