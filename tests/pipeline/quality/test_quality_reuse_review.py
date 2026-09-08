"""Returned stage references and present policy cannot bypass quality on reuse."""

from dataclasses import replace
from pathlib import Path

from arxiv_int.interfaces.stores import ValidationResultRef
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.run.fixtures import fixture_registry
from tests.pipeline.conftest import make_context
from tests.pipeline.publish.test_boundary_review import MissingGlobalQuality
from tests.pipeline.publish.test_publish import _plan


def test_index_cache_hit_cannot_bypass_missing_global_checks(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path)
    assert (
        not Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry)).halted
    )
    status = Orchestrator(registry, context.runs_dir, quality=MissingGlobalQuality()).execute_plan(
        context, _plan(registry)
    )
    assert status.halted
    assert all(runners[name].calls == 1 for name in ("alpha", "beta", "gamma"))


def test_failed_stage_supplied_validation_blocks_publication(tmp_path: Path, monkeypatch) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path)
    original = runners["alpha"].run

    def run(stage_context):
        result = original(stage_context)
        ref = ValidationResultRef("alpha", context.generation_id, "catalog", "fail", False)
        return replace(result, validations=(ref,))

    monkeypatch.setattr(runners["alpha"], "run", run)
    status = Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    assert status.halted
    assert runners["beta"].calls == 0
