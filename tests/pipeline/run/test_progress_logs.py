"""Fixture DAG runs emit progress JSONL without garbling concurrent lines."""

import json
from pathlib import Path

from arxiv_int.pipeline.dag.graph import select_plan
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.run.fixtures import fixture_registry
from tests.pipeline.conftest import make_context


def test_fixture_run_writes_progress_jsonl_and_manifest(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    registry, _runners = fixture_registry()
    plan = select_plan(
        registry.dependencies(),
        profile_stages=("alpha", "beta"),
        optional_stages=frozenset({"omega", "gamma"}),
    )
    report = Orchestrator(registry, context.runs_dir).execute_plan(context, plan)
    assert report.halted is False
    logs = context.runs_dir / context.run_id / "logs"
    progress = (logs / "progress.jsonl").read_text(encoding="utf-8")
    rows = [json.loads(line) for line in progress.splitlines() if line]
    assert rows
    assert all(row["schema"] == "arxiv-int.observability.v1" for row in rows)
    assert any(row["event"] == "stage-complete" for row in rows)
    assert (logs / "observability-manifest.json").is_file()
    console = (logs / "console.log").read_text(encoding="utf-8").splitlines()
    assert console
    assert all("\x00" not in line for line in console)
