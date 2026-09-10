"""Inspect summaries cover empty, partial, quarantined, and drifted artifacts."""

import hashlib
from dataclasses import replace
from pathlib import Path

from arxiv_int.data_quality.engine.model import STATUS_NOT_RUN, STATUS_PASS, STATUS_WARNING
from arxiv_int.inspect.lookup import InspectError, resolve_target
from arxiv_int.inspect.model import CONFORMANCE_DRIFTED, KIND_RUN, LATEST_TOKEN
from arxiv_int.inspect.render import json_document
from arxiv_int.inspect.summarize import inspect_run, inspect_target
from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.interfaces.stores import DatasetRef
from arxiv_int.pipeline.control.quality import GLOBAL_SCOPE, QualityCheck
from arxiv_int.pipeline.dag.actions import fixture_plan
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.quality.bound import FixtureQuality
from arxiv_int.pipeline.run.fixtures import (
    FIXTURE_OPTIONAL,
    FIXTURE_PROFILE_STAGES,
    fixture_registry,
)
from arxiv_int.pipeline.run.persist import save_context
from arxiv_int.runtime.project_root import find_project_root
from tests.pipeline.conftest import make_context


def _plan(registry):
    return fixture_plan(
        registry,
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
    )


def _checksums(root: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records[path.relative_to(root).as_posix()] = digest
    return records


def test_inspect_fixture_run_reports_counts_and_is_read_only(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    assert (
        not Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry)).halted
    )
    before = _checksums(context.runs_dir)
    summary = inspect_run(
        context.runs_dir,
        context.run_id,
        results_dir=context.results_dir,
        project_root=find_project_root(),
    )
    assert summary.kind == KIND_RUN
    assert summary.run_id == context.run_id
    assert [item.stage for item in summary.stages] == ["alpha", "beta", "gamma"]
    assert all(item.tree_valid for item in summary.stages)
    assert all(item.files for item in summary.stages)
    assert all("home/" not in item.directory for item in summary.stages)
    assert summary.run_id != "local"
    assert _checksums(context.runs_dir) == before


def test_empty_partial_quarantined_and_failed_summaries(tmp_path: Path) -> None:
    empty_registry, _empty = fixture_registry(gamma_outcome="empty")
    empty_context = make_context(tmp_path / "empty")
    Orchestrator(empty_registry, empty_context.runs_dir).execute_plan(
        empty_context, _plan(empty_registry)
    )
    empty = inspect_run(
        empty_context.runs_dir,
        empty_context.run_id,
        results_dir=empty_context.results_dir,
        project_root=find_project_root(),
    )
    gamma_empty = next(item for item in empty.stages if item.stage == "gamma")
    assert gamma_empty.outcome == "empty"

    partial_registry, _partial = fixture_registry(gamma_outcome="partial")
    partial_context = make_context(tmp_path / "partial")
    Orchestrator(partial_registry, partial_context.runs_dir).execute_plan(
        partial_context, _plan(partial_registry)
    )
    partial = inspect_run(
        partial_context.runs_dir,
        partial_context.run_id,
        results_dir=partial_context.results_dir,
        project_root=find_project_root(),
    )
    gamma_partial = next(item for item in partial.stages if item.stage == "gamma")
    assert gamma_partial.outcome == "partial"
    assert partial.halted

    class WarningQuality(FixtureQuality):
        def checks(self) -> tuple[QualityCheck, ...]:
            return (
                QualityCheck("global.fixture", STATUS_PASS, GLOBAL_SCOPE, "error", True),
                QualityCheck("batch.nulls", STATUS_WARNING, "batch", "warning", True),
            )

    quarantined_registry, _ok = fixture_registry()
    quarantined_context = make_context(tmp_path / "quarantine")
    Orchestrator(
        quarantined_registry, quarantined_context.runs_dir, quality=WarningQuality()
    ).execute_plan(quarantined_context, _plan(quarantined_registry))
    quarantined = inspect_run(
        quarantined_context.runs_dir,
        quarantined_context.run_id,
        results_dir=quarantined_context.results_dir,
        project_root=find_project_root(),
    )
    assert all(item.status == "quarantined" for item in quarantined.stages)
    assert any("batch.nulls" in item.quarantines for item in quarantined.stages)

    failed_registry, _fail = fixture_registry(fail_gamma=True)
    failed_context = make_context(tmp_path / "failed")
    Orchestrator(failed_registry, failed_context.runs_dir).execute_plan(
        failed_context, _plan(failed_registry)
    )
    failed = inspect_run(
        failed_context.runs_dir,
        failed_context.run_id,
        results_dir=failed_context.results_dir,
        project_root=find_project_root(),
    )
    gamma_failed = next(item for item in failed.stages if item.stage == "gamma")
    assert gamma_failed.status == "failed"
    assert gamma_failed.failures


def test_schema_drift_and_not_run_quality_without_transforms(
    tmp_path: Path, monkeypatch: object
) -> None:
    registry, runners = fixture_registry(dbt_select=("stg_documents",))
    context = make_context(tmp_path)
    original = runners["alpha"].run

    def drifted(stage_context: StageContext) -> StageResult:
        result = original(stage_context)
        output = DatasetRef("documents", "0.9.0", stage_context.generation_id, {"shard": "default"})
        return StageResult(result.stage, result.outcome, result.detail, outputs=(output,))

    monkeypatch.setattr(runners["alpha"], "run", drifted)

    class MixedQuality(FixtureQuality):
        def checks(self) -> tuple[QualityCheck, ...]:
            return (
                QualityCheck("global.fixture", STATUS_PASS, GLOBAL_SCOPE, "error", True),
                QualityCheck("snapshot.unexecuted", STATUS_NOT_RUN, "snapshot", "error", False),
            )

    def refuse_transform(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("inspection must not execute transformations")

    monkeypatch.setattr("arxiv_int.transformations.runner.run_transform", refuse_transform)
    Orchestrator(registry, context.runs_dir, quality=MixedQuality()).execute_plan(
        context, _plan(registry)
    )
    summary = inspect_run(
        context.runs_dir,
        context.run_id,
        results_dir=context.results_dir,
        project_root=find_project_root(),
    )
    alpha = next(item for item in summary.stages if item.stage == "alpha")
    assert alpha.schema_drifted
    assert any(part.conformance == CONFORMANCE_DRIFTED for part in alpha.partitions)
    gamma = next(item for item in summary.stages if item.stage == "gamma")
    assert any(check.status == STATUS_NOT_RUN for check in gamma.quality)
    assert any(item.command == "build" for item in gamma.lineage)


def test_malformed_quality_is_stable_and_does_not_rewrite(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    quality_path = next(
        path for path in (context.runs_dir / context.run_id / "manifests").rglob("quality.json")
    )
    quality_path.write_text('{"unexpected": true}\n', encoding="utf-8")
    before = _checksums(context.runs_dir)
    summary = inspect_run(
        context.runs_dir,
        context.run_id,
        results_dir=context.results_dir,
        project_root=find_project_root(),
    )
    drifted = next(item for item in summary.stages if item.schema_drifted)
    assert not drifted.tree_valid
    assert _checksums(context.runs_dir) == before


def test_redacts_secrets_paths_and_refuses_developer_alias(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path)

    def noisy(stage_context: StageContext) -> StageResult:
        del stage_context
        detail = 'password=super-secret /home/operator/archive/doc.pdf "' + ("corpus " * 80) + '"'
        return StageResult("alpha", "failed", detail)

    runners["alpha"].run = noisy
    Orchestrator(registry, context.runs_dir).execute_plan(context, _plan(registry))
    summary = inspect_run(
        context.runs_dir,
        context.run_id,
        results_dir=context.results_dir,
        project_root=find_project_root(),
    )
    rendered = json_document(summary)
    alpha = next(item for item in summary.stages if item.stage == "alpha")
    assert all("super-secret" not in detail for detail in alpha.failures)
    assert "super-secret" not in rendered
    assert "/home/operator" not in rendered
    assert "corpus " not in rendered or "<redacted" in rendered
    assert summary.run_id != "local"
    try:
        resolve_target("local", context.runs_dir)
    except InspectError as error:
        assert "developer alias" in str(error)
    else:
        raise AssertionError("expected InspectError")


def test_latest_and_lake_dataset_lookup(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    shared_runs = tmp_path / "shared-runs"
    first = replace(make_context(tmp_path / "first"), runs_dir=shared_runs)
    save_context(first)
    Orchestrator(registry, shared_runs).execute_plan(first, _plan(registry))
    second = replace(make_context(tmp_path / "second", text="two"), runs_dir=shared_runs)
    save_context(second)
    Orchestrator(registry, shared_runs).execute_plan(second, _plan(registry))
    target = resolve_target(LATEST_TOKEN, shared_runs)
    summary = inspect_target(
        target,
        runs_dir=shared_runs,
        results_dir=second.results_dir,
        project_root=find_project_root(),
    )
    assert summary.run_id == second.run_id
    lake_dir = (
        second.results_dir / "normalized" / "documents" / "contract_version=1.0.0" / "bucket=ab"
    )
    lake_dir.mkdir(parents=True)
    (lake_dir / "part.json").write_text("[]\n", encoding="utf-8")
    dataset = inspect_target(
        resolve_target("documents", shared_runs),
        runs_dir=shared_runs,
        results_dir=second.results_dir,
        project_root=find_project_root(),
        limit=2,
    )
    assert dataset.lake
    assert dataset.lake[0].dataset == "documents"
    assert len(dataset.lake) <= 2


def test_bounded_source_anchors() -> None:
    from arxiv_int.inspect.artifacts import anchor_summaries

    payload = {
        "anchors": [
            {
                "silo_id": "archive",
                "relative_path": "notes/doc.pdf",
                "scan_id": "scan-1",
                "kind": "page",
                "page": 2,
            },
            {
                "silo_id": "archive",
                "relative_path": "sheet.xlsx",
                "scan_id": "scan-1",
                "kind": "cell",
                "sheet": "Budget",
                "cell_range": "B2",
            },
            {
                "silo_id": "archive",
                "relative_path": "extra.pdf",
                "scan_id": "scan-1",
                "kind": "page",
                "page": 9,
            },
        ]
    }
    rows = anchor_summaries(payload, Path("."), limit=2)
    assert len(rows) == 2
    assert rows[0].relative_path == "notes/doc.pdf"
    assert rows[0].page == 2
    assert rows[1].sheet == "Budget"
    assert "/" not in rows[0].silo_id


def test_superseded_attempt_never_borrows_the_accepted_attempt_identity(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    orchestrator = Orchestrator(registry, context.runs_dir)
    assert not orchestrator.execute_plan(context, _plan(registry)).halted
    assert not orchestrator.execute_plan(context, _plan(registry), force=True).halted
    summary = inspect_run(
        context.runs_dir,
        context.run_id,
        results_dir=context.results_dir,
        project_root=find_project_root(),
    )
    rows = [row for row in summary.stages if row.stage == FIXTURE_PROFILE_STAGES[0]]
    assert len(rows) == 2
    by_directory = {row.directory.rsplit("/", 1)[-1]: row for row in rows}
    assert set(by_directory) == {"attempt-1", "attempt-2"}
    assert by_directory["attempt-2"].attempt == 2
    assert by_directory["attempt-2"].status == "succeeded"
    assert by_directory["attempt-1"].attempt == 1
    assert by_directory["attempt-1"].status == "unknown"
