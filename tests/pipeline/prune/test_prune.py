"""Two-phase prune refuses protected derived data and deletes only eligible stale copies."""

from pathlib import Path

import pytest

from arxiv_int.pipeline.actions import fixture_plan, rebuild_context
from arxiv_int.pipeline.fixtures import FIXTURE_OPTIONAL, FIXTURE_PROFILE_STAGES, fixture_registry
from arxiv_int.pipeline.orchestrate import Orchestrator
from arxiv_int.pipeline.persist import save_context, write_json
from arxiv_int.pipeline.prune.apply import PruneRefusedError, apply_prune_plan
from arxiv_int.pipeline.prune.plan import build_prune_plan
from arxiv_int.pipeline.prune.protect import protections
from arxiv_int.pipeline.reuse_index import load_reuse_index, load_superseded
from tests.pipeline.orchestration.conftest import make_context


def _plan(registry: object) -> object:
    return fixture_plan(
        registry,  # type: ignore[arg-type]
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
    )


def test_prune_refuses_sole_recovery_and_stale_plan(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    orchestrator.invalidate("alpha")
    plan = build_prune_plan(context.runs_dir)
    assert plan.entries
    assert any(item.kind == "sole-recovery" for item in plan.blocked)
    listed = [Path(entry.directory) for entry in plan.entries]
    fake = context.runs_dir / "prune-plans" / "prune-missing.json"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_text('{"directories": [], "fingerprint": "nope"}\n', encoding="utf-8")
    with pytest.raises(PruneRefusedError, match="stale"):
        apply_prune_plan(context.runs_dir, "prune-missing")
    apply_prune_plan(context.runs_dir, plan.plan_id)
    assert all(path.is_dir() for path in listed)


def test_prune_refuses_active_pinned_reviewed_rollback_ledger_and_backup(
    tmp_path: Path,
) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    status = orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    directory = status.executions[0].directory
    assert directory
    write_json(
        context.runs_dir / "active-generation.json",
        {"run_id": context.run_id, "generation_id": context.generation_id},
    )
    write_json(context.runs_dir / "pins" / "keep.json", {"directory": directory})
    (context.runs_dir / context.run_id / "review").mkdir(parents=True)
    (context.runs_dir / context.run_id / "rollback").mkdir()
    (context.runs_dir / context.run_id / "ledgers").mkdir()
    (context.runs_dir / "backups").mkdir()
    index = load_reuse_index(context.runs_dir)
    live = {key: entry for key, entry in index.items() if not entry.stale}
    stale = tuple(index.values())
    kinds = {item.kind for item in protections(context.runs_dir, stale, live)}
    assert "active" in kinds
    plan = build_prune_plan(context.runs_dir)
    assert plan.eligible == ()


def test_rebuild_then_prune_removes_superseded_attempts(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    first = orchestrator.execute_plan(context, _plan(registry))  # type: ignore[arg-type]
    old_dirs = [Path(item.directory) for item in first.executions if item.directory]
    rebuilt = rebuild_context(context)
    save_context(rebuilt)
    orchestrator.execute_plan(rebuilt, _plan(registry), force=True)  # type: ignore[arg-type]
    assert load_superseded(context.runs_dir)
    plan = build_prune_plan(context.runs_dir)
    assert plan.eligible
    removed = apply_prune_plan(context.runs_dir, plan.plan_id)
    assert removed >= 1
    assert any(not path.is_dir() for path in old_dirs)
    live = load_reuse_index(context.runs_dir)
    assert live
    assert all(Path(entry.directory).is_dir() for entry in live.values())
