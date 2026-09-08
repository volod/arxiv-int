"""Application handlers for run create, DAG walk, resume, and prune commands."""

import logging
from collections.abc import Callable, Mapping
from pathlib import Path

from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.dag.actions import (
    PrunePlan,
    apply_prune_plan,
    build_prune_plan,
    persist_new_context,
    plan_for,
    rebuild_context,
    remaining_plan,
    status_lines,
    update_context,
)
from arxiv_int.pipeline.dag.cancel import CancelToken
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.dag.registry import StageRegistry
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.quality.bound import QualityBoundary
from arxiv_int.pipeline.run.context import (
    RunContext,
    allocate_run_id,
    config_fingerprint,
    secret_free_values,
    snapshot_silos,
)
from arxiv_int.pipeline.run.errors import ConfigDriftError, PipelineError, StaleUpstreamError
from arxiv_int.pipeline.run.persist import load_context, load_status, run_dir
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.setup.settings import load_setup_settings

_LOG = logging.getLogger(__name__)


def create_run_context(
    *,
    project_root: Path | None = None,
    profile: str | None = None,
    archive_dir: Path | None = None,
    results_dir: Path | None = None,
    environment: Mapping[str, str] | None = None,
    from_stage: str | None = None,
    to_stage: str | None = None,
    parameters: Mapping[str, str] | None = None,
) -> RunContext:
    """Allocate a unique run id and freeze secret-free configuration."""
    config = _load_config(project_root, archive_dir, results_dir, environment)
    settings = load_setup_settings(project_root=config.project_root, environment=environment)
    chosen = profile or settings.pipeline_profile
    silos = tuple(SiloRoot(silo.silo_id, silo.root) for silo in config.archive_silos)
    secret_free = secret_free_values(dict(config.values))
    run_id = allocate_run_id()
    context = RunContext(
        run_id=run_id,
        generation_id=run_id,
        profile=chosen,
        config_fingerprint=config_fingerprint(chosen, secret_free),
        source_snapshot=snapshot_silos(silos),
        silos=silos,
        results_dir=config.results_dir,
        runs_dir=config.runs_dir,
        project_root=config.project_root,
        secret_free=secret_free,
        parameters=dict(parameters or {}),
        from_stage=from_stage,
        to_stage=to_stage,
    )
    persist_new_context(context)
    _LOG.info(
        "run_id=%s generation_id=%s profile=%s", context.run_id, context.generation_id, chosen
    )
    _LOG.info("status: arxiv-int run status %s", context.run_id)
    _LOG.info("resume: arxiv-int run resume %s", context.run_id)
    return context


def run_dag(
    context: RunContext,
    registry: StageRegistry | None = None,
    *,
    from_stage: str | None = None,
    to_stage: str | None = None,
    force: bool = False,
    quality: QualityBoundary | None = None,
    cancel: CancelToken | None = None,
    resume: bool = False,
    space_guard: Callable[[str], None] | None = None,
) -> int:
    """Execute or resume a resolved plan against one frozen run."""
    selected = registry or production_registry()
    plan = plan_for(selected, context, from_stage=from_stage, to_stage=to_stage)
    if resume:
        status_path = run_dir(context.runs_dir, context.run_id) / "status.json"
        previous = load_status(context.runs_dir, context.run_id) if status_path.is_file() else None
        plan = remaining_plan(plan, previous)
    guard: Callable[[str], None] | None = space_guard
    if guard is None:
        from arxiv_int.pipeline.forecast.commands import bind_forecast

        config = load_runtime_config(project_root=context.project_root)
        _document, guard = bind_forecast(context, selected, plan, config, force=force)
    orchestrator = Orchestrator(
        selected,
        context.runs_dir,
        quality=quality,
        cancel=cancel,
        space_guard=guard,
    )
    try:
        report = orchestrator.execute_plan(context, plan, force=force)
    except PipelineError as error:
        _LOG.error("%s", error)
        return int(getattr(error, "exit_code", 1))
    for line in status_lines(report):
        _LOG.info("%s", line)
    if report.halt_reason == "interrupted":
        return 130
    return 1 if report.halted else 0


def require_frozen_context(
    runs_dir: Path,
    run_id: str,
    *,
    project_root: Path | None = None,
    archive_dir: Path | None = None,
    results_dir: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> RunContext:
    """Load a run and refuse configuration drift or a changed archive snapshot."""
    context = load_context(runs_dir, run_id)
    config = _load_config(project_root, archive_dir, results_dir, environment)
    secret_free = secret_free_values(dict(config.values))
    current = config_fingerprint(context.profile, secret_free)
    if current != context.config_fingerprint:
        raise ConfigDriftError(
            f"run {run_id} configuration drifted; create a new run or invalidate"
        )
    if snapshot_silos(context.silos) != context.source_snapshot:
        raise StaleUpstreamError("archive snapshot changed; use pipeline update or resume")
    return context


def _load_config(
    project_root: Path | None,
    archive_dir: Path | None,
    results_dir: Path | None,
    environment: Mapping[str, str] | None,
) -> RuntimeConfig:
    cli: dict[str, str | None] = {}
    if archive_dir is not None:
        cli["ARCHIVE_DIR"] = str(archive_dir)
    if results_dir is not None:
        cli["RESULTS_DIR"] = str(results_dir)
    return load_runtime_config(project_root=project_root, environment=environment, cli=cli)


def log_prune(plan: PrunePlan) -> None:
    """Log a dry-run prune plan."""
    _LOG.info(
        "prune_plan=%s bytes=%s blocked=%s",
        plan.plan_id,
        plan.bytes,
        len(plan.blocked),
    )
    _LOG.info("apply: arxiv-int artifacts prune --stale --apply --plan %s", plan.plan_id)


__all__ = [
    "apply_prune_plan",
    "build_prune_plan",
    "create_run_context",
    "log_prune",
    "rebuild_context",
    "require_frozen_context",
    "run_dag",
    "update_context",
]
