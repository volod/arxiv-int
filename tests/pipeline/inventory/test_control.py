"""Production registration, cache integrity and reconciliation integration."""

from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.pipeline.dag.actions import plan_for
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.inventory.snapshot import inventory_snapshot
from arxiv_int.pipeline.reconcile.diff import diff_manifests, tombstones_for
from arxiv_int.pipeline.reconcile.persist import load_manifest
from arxiv_int.pipeline.reconcile.scan import scan_silos
from tests.pipeline.conftest import make_context


def test_production_inventory_runs_once_and_checks_external_cache(tmp_path: Path) -> None:
    context = make_context(tmp_path, profile="investigation")
    (context.silos[0].root / "second").write_text("different")
    context = replace(
        context, project_root=Path.cwd(), source_snapshot=inventory_snapshot(context.silos)
    )
    registry = production_registry()
    plan = plan_for(registry, context, to_stage="inventory")
    orchestrator = Orchestrator(registry, context.runs_dir)
    result = orchestrator.execute_plan(context, plan)
    assert not result.halted, result.halt_reason
    assert [item.stage for item in result.executions] == ["preflight", "inventory"]
    repeat = orchestrator.execute_plan(context, plan)
    assert all(item.cache_hit for item in repeat.executions)
    manifest = load_manifest(context.runs_dir, context.run_id)
    assert manifest is not None and manifest.comparable
    assert len(manifest.silos[0].occurrences) == 2
    parquet = next(context.results_dir.rglob("*.parquet"))
    parquet.write_bytes(b"corrupt")
    repaired = Orchestrator(registry, context.runs_dir).execute_plan(context, plan)
    assert not repaired.halted
    assert not repaired.executions[-1].cache_hit


def test_link_replacement_withholds_removal_and_tombstone(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    before = scan_silos(context.silos)
    path = context.silos[0].root / "doc.txt"
    path.unlink()
    path.symlink_to(tmp_path / "missing")
    after = scan_silos(context.silos)
    assert not after.comparable
    assert after.silos[0].occurrences[0].relative_path == "doc.txt"
    assert not after.silos[0].occurrences[0].readable
    delta = diff_manifests(before, after)
    assert not delta.of_kind("remove")
    assert not tombstones_for(delta, before, after, "generation")


def test_cancel_interrupts_chunked_hash(tmp_path: Path) -> None:
    from arxiv_int.pipeline.dag.cancel import CancelToken, cancellation_scope
    from arxiv_int.pipeline.inventory.model import InventoryPolicy
    from arxiv_int.pipeline.inventory.read import observe
    from arxiv_int.pipeline.inventory.walk import walk
    from arxiv_int.pipeline.run.errors import InterruptedPipelineError

    (tmp_path / "file").write_bytes(b"bytes")
    token = CancelToken()
    token.cancel()
    with cancellation_scope(token), pytest.raises(InterruptedPipelineError):
        list(observe(tmp_path, "one", next(walk(tmp_path)), InventoryPolicy()))


def test_inspection_excludes_unsealed_inventory_scratch(tmp_path: Path) -> None:
    from arxiv_int.inspect.lake import lake_partitions
    from arxiv_int.interfaces.pipeline import StageContext
    from arxiv_int.interfaces.sources import SiloRoot
    from arxiv_int.pipeline.inventory.stage import InventoryStage

    source = tmp_path / "source"
    source.mkdir()
    (source / "doc").write_text("text")
    results = tmp_path / "results"
    context = StageContext(
        "inventory",
        "scan",
        "scan",
        (SiloRoot("one", source),),
        results,
        {"project_root": str(Path.cwd())},
    )
    InventoryStage().run(context)
    unsealed = results / "normalized/inventory/unsealed"
    unsealed.mkdir()
    (unsealed / "bad.parquet").write_bytes(b"not a dataset")
    rows = lake_partitions(results, {"source-occurrences": "1.0.0"}, "source-occurrences", 100)
    assert len(rows) == 1
    assert rows[0].dataset == "source-occurrences"
    assert rows[0].conformance == "matching"
