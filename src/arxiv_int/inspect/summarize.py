"""Build a read-only inspection summary from retained artifacts."""

from collections.abc import Mapping
from pathlib import Path

from arxiv_int.inspect.artifacts import missing_attempt, stage_summary
from arxiv_int.inspect.lake import lake_partitions
from arxiv_int.inspect.lookup import (
    InspectError,
    InspectionTarget,
    attempt_locations,
)
from arxiv_int.inspect.model import (
    DEFAULT_LIMIT,
    KIND_DATASET,
    KIND_RUN,
    SCHEMA_ID,
    InspectionSummary,
    StageSummary,
)
from arxiv_int.inspect.quality import contract_versions, published_lineage, published_quality
from arxiv_int.observability.logging.redact import extra_secrets_from_env, redact_text
from arxiv_int.pipeline.run.persist import RunStatus, load_context, load_status


def inspect_run(
    runs_dir: Path,
    run_id: str,
    *,
    results_dir: Path,
    project_root: Path,
    limit: int = DEFAULT_LIMIT,
    dataset: str = "",
) -> InspectionSummary:
    """Summarize one frozen run's published attempts and matching lake files."""
    if limit < 1:
        raise InspectError("inspect --limit must be >= 1")
    context = load_context(runs_dir, run_id)
    versions = contract_versions(project_root)
    status = _status(runs_dir, run_id)
    stages = _stage_rows(runs_dir, run_id, status, versions, limit, dataset)
    return InspectionSummary(
        SCHEMA_ID,
        KIND_DATASET if dataset else KIND_RUN,
        dataset or run_id,
        run_id,
        context.generation_id,
        context.profile,
        bool(status.halted) if status else False,
        _safe_reason(status.halt_reason if status else ""),
        stages,
        lake_partitions(results_dir, versions, dataset, limit),
        status.not_selected if status else (),
        published_quality(runs_dir, run_id, limit=limit),
        published_lineage(runs_dir, run_id, limit=limit),
        limit,
    )


def inspect_target(
    target: InspectionTarget,
    *,
    runs_dir: Path,
    results_dir: Path,
    project_root: Path,
    limit: int = DEFAULT_LIMIT,
) -> InspectionSummary:
    """Inspect a resolved run, dataset, or latest generation."""
    if target.kind == KIND_DATASET and not target.run_id:
        versions = contract_versions(project_root)
        lake = lake_partitions(results_dir, versions, target.dataset, limit)
        if not lake:
            raise InspectError(f"no artifacts for dataset {target.dataset}")
        return InspectionSummary(
            SCHEMA_ID,
            KIND_DATASET,
            target.dataset,
            "",
            "",
            "",
            False,
            "",
            (),
            lake,
            (),
            (),
            (),
            limit,
        )
    if not target.run_id:
        raise InspectError("no run to inspect; create a run first")
    summary = inspect_run(
        runs_dir,
        target.run_id,
        results_dir=results_dir,
        project_root=project_root,
        limit=limit,
        dataset=target.dataset,
    )
    if target.kind == KIND_DATASET and not summary.stages and not summary.lake:
        raise InspectError(f"no artifacts for dataset {target.dataset}")
    return summary


def _status(runs_dir: Path, run_id: str) -> RunStatus | None:
    path = runs_dir / run_id / "status.json"
    return load_status(runs_dir, run_id) if path.is_file() else None


def _stage_rows(
    runs_dir: Path,
    run_id: str,
    status: RunStatus | None,
    versions: Mapping[str, str],
    limit: int,
    dataset: str,
) -> tuple[StageSummary, ...]:
    executions = {item.stage: item for item in status.executions} if status else {}
    stages: list[StageSummary] = []
    for directory in attempt_locations(runs_dir, run_id):
        stage_name = directory.parent.parent.name
        summary = stage_summary(
            directory,
            runs_dir,
            executions.get(stage_name),
            versions,
            limit,
            dataset,
            stage_name,
        )
        if summary is not None:
            stages.append(summary)
    covered = {row.stage for row in stages}
    for item in status.executions if status else ():
        if item.stage in covered:
            continue
        summary = missing_attempt(item, dataset)
        if summary is not None:
            stages.append(summary)
    return tuple(stages)


def _safe_reason(reason: str) -> str:
    if not reason:
        return ""
    return redact_text(reason, extra_secrets_from_env())
