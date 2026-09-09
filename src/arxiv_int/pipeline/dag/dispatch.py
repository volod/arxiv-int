"""Dispatch parsed pipeline CLI arguments to shared handlers."""

import argparse
import logging
import signal
from dataclasses import replace
from pathlib import Path

from arxiv_int.observability.logging.format import format_progress
from arxiv_int.observability.sinks import FileProgressStore
from arxiv_int.pipeline.commands import (
    create_run_context,
    log_prune,
    require_frozen_context,
    run_dag,
)
from arxiv_int.pipeline.dag.actions import (
    apply_prune_plan,
    build_prune_plan,
    persist_new_context,
    rebuild_context,
    status_lines,
    update_context,
)
from arxiv_int.pipeline.dag.cancel import CancelToken, install_signal_handler
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.publish.finalize import finalize_run
from arxiv_int.pipeline.publish.preflight import preflight_run
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.errors import PipelineError
from arxiv_int.pipeline.run.persist import load_context, load_status
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.project_root import ProjectRootError

_LOG = logging.getLogger(__name__)


def run_pipeline_command(args: argparse.Namespace) -> int:
    """Dispatch ``arxiv-int pipeline|stage|run|artifacts``."""
    command = args.command
    token = CancelToken()
    previous = signal.getsignal(signal.SIGINT)
    install_signal_handler(token)
    try:
        if command == "pipeline":
            return _pipeline(args, token)
        if command == "stage":
            return _stage(args, token)
        if command == "run":
            return _run(args, token)
        return _artifacts(args)
    except (OSError, PipelineError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
        return int(getattr(error, "exit_code", 1))
    finally:
        signal.signal(signal.SIGINT, previous)


def _pipeline(args: argparse.Namespace, token: CancelToken) -> int:
    action = args.pipeline_command
    if action == "forecast":
        from arxiv_int.pipeline.forecast.commands import run_forecast_command

        return run_forecast_command(args)
    if action == "run":
        context = create_run_context(
            project_root=args.project_root,
            profile=args.profile,
            archive_dir=args.archive_dir,
            results_dir=args.results_dir,
            from_stage=args.from_stage,
            to_stage=args.to_stage,
        )
        return _run_profile(context, token, force=bool(args.force))
    previous_run = _previous_context(args)
    if action == "update":
        context = persist_new_context(update_context(previous_run))
        from arxiv_int.pipeline.reconcile.commands import prepare_update

        prepare_update(previous_run, context, Orchestrator(production_registry(), context.runs_dir))
        return _run_profile(context, token, from_stage=args.from_stage, to_stage=args.to_stage)
    if action == "rebuild":
        context = persist_new_context(rebuild_context(previous_run))
        code = _run_profile(
            context, token, from_stage=args.from_stage, to_stage=args.to_stage, force=True
        )
        from arxiv_int.pipeline.reconcile.commands import record_rebuild

        record_rebuild(previous_run, context)
        return code
    orchestrator = Orchestrator(production_registry(), previous_run.runs_dir)
    marked = orchestrator.invalidate(str(args.stage), document_id=args.document_id)
    _LOG.info("invalidated %s reuse key(s)", len(marked))
    for key in marked:
        _LOG.info("stale_reuse_key=%s", key)
    return 0


def _stage(args: argparse.Namespace, token: CancelToken) -> int:
    config = load_runtime_config(project_root=args.project_root)
    context = require_frozen_context(
        config.runs_dir, str(args.run_id), project_root=config.project_root
    )
    if args.document_id:
        parameters = dict(context.parameters)
        parameters["document_id"] = str(args.document_id)
        context = replace(context, parameters=parameters)
    return run_dag(
        context,
        from_stage=str(args.stage),
        to_stage=str(args.stage),
        force=bool(args.force),
        cancel=token,
    )


def _run(args: argparse.Namespace, token: CancelToken) -> int:
    action = args.run_command
    if action == "create":
        create_run_context(
            project_root=args.project_root,
            profile=args.profile,
            archive_dir=args.archive_dir,
            results_dir=args.results_dir,
        )
        return 0
    run_id = str(args.run_id)
    runs_dir = args.runs_dir
    if runs_dir is None:
        runs_dir = load_runtime_config(project_root=args.project_root).runs_dir
    if action == "status":
        require_frozen_context(Path(runs_dir), run_id, project_root=args.project_root)
        for line in status_lines(load_status(Path(runs_dir), run_id)):
            _LOG.info("%s", line)
        latest = FileProgressStore(Path(runs_dir) / run_id).load_latest()
        if latest is not None:
            _LOG.info("%s", format_progress(latest))
            _LOG.info("worker_state=%s", latest.worker_state)
        return 0
    if action == "artifacts":
        from arxiv_int.inspect.commands import run_inspect_command

        return run_inspect_command(args)
    if action == "finalize":
        return finalize_run(load_context(Path(runs_dir), run_id))
    context = require_frozen_context(Path(runs_dir), run_id, project_root=args.project_root)
    return run_dag(context, force=bool(args.force), cancel=token, resume=True)


def _artifacts(args: argparse.Namespace) -> int:
    runs_dir = args.runs_dir
    if runs_dir is None:
        runs_dir = load_runtime_config(project_root=args.project_root).runs_dir
    if args.apply:
        plan_id = args.plan_id
        if not plan_id:
            raise ValueError("prune --apply requires --plan PLAN_ID")
        removed = apply_prune_plan(Path(runs_dir), str(plan_id))
        _LOG.info("removed %s stale attempt director(y/ies)", removed)
        return 0
    log_prune(build_prune_plan(Path(runs_dir)))
    return 0


def _previous_context(args: argparse.Namespace) -> RunContext:
    run_id = args.run_id
    config = load_runtime_config(project_root=args.project_root, cli=_cli_paths(args))
    if run_id:
        return load_context(config.runs_dir, str(run_id))
    latest = _latest_run(config.runs_dir)
    if latest is None:
        raise ValueError("no previous run to update; run arxiv-int run create first")
    return load_context(config.runs_dir, latest)


def _cli_paths(args: argparse.Namespace) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {}
    if args.archive_dir is not None:
        mapping["ARCHIVE_DIR"] = str(args.archive_dir)
    if args.results_dir is not None:
        mapping["RESULTS_DIR"] = str(args.results_dir)
    return mapping


def _latest_run(runs_dir: Path) -> str | None:
    found = list(runs_dir.glob("run-*/run-context.json"))
    if not found:
        return None
    return max(found, key=lambda path: path.stat().st_mtime).parent.name


def _run_profile(
    context: RunContext,
    token: CancelToken,
    *,
    from_stage: str | None = None,
    to_stage: str | None = None,
    force: bool = False,
) -> int:
    preflight_run(context)
    _refresh_forecast(context, force=force)
    code = run_dag(
        context,
        from_stage=from_stage if from_stage is not None else context.from_stage,
        to_stage=to_stage if to_stage is not None else context.to_stage,
        force=force,
        cancel=token,
    )
    return finalize_run(context, fallback_exit=code)


def _refresh_forecast(context: RunContext, *, force: bool = False) -> None:
    from arxiv_int.pipeline.forecast.commands import forecast_or_refuse

    config = load_runtime_config(project_root=context.project_root)
    forecast_or_refuse(context, config, production_registry(), force=force)
