"""Dispatch parsed pipeline CLI arguments to shared handlers."""

import argparse
import logging
import signal
from dataclasses import replace
from pathlib import Path

from arxiv_int.pipeline.actions import (
    apply_prune_plan,
    build_prune_plan,
    persist_new_context,
    rebuild_context,
    status_lines,
    update_context,
)
from arxiv_int.pipeline.cancel import CancelToken, install_signal_handler
from arxiv_int.pipeline.commands import (
    create_run_context,
    log_prune,
    require_frozen_context,
    run_dag,
)
from arxiv_int.pipeline.context import RunContext
from arxiv_int.pipeline.errors import PipelineError
from arxiv_int.pipeline.orchestrate import Orchestrator
from arxiv_int.pipeline.persist import load_context, load_status
from arxiv_int.pipeline.stages import production_registry
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
        return 1
    finally:
        signal.signal(signal.SIGINT, previous)


def _pipeline(args: argparse.Namespace, token: CancelToken) -> int:
    action = args.pipeline_command
    if action == "run":
        context = create_run_context(
            project_root=args.project_root,
            profile=args.profile,
            archive_dir=args.archive_dir,
            results_dir=args.results_dir,
            from_stage=args.from_stage,
            to_stage=args.to_stage,
        )
        return run_dag(
            context,
            from_stage=context.from_stage,
            to_stage=context.to_stage,
            force=bool(args.force),
            cancel=token,
        )
    previous_run = _previous_context(args)
    if action == "update":
        context = persist_new_context(update_context(previous_run))
        return run_dag(
            context,
            from_stage=args.from_stage,
            to_stage=args.to_stage,
            cancel=token,
        )
    if action == "rebuild":
        context = persist_new_context(rebuild_context(previous_run))
        return run_dag(
            context,
            from_stage=args.from_stage,
            to_stage=args.to_stage,
            force=True,
            cancel=token,
        )
    orchestrator = Orchestrator(production_registry(), previous_run.runs_dir)
    marked = orchestrator.invalidate(str(args.stage), document_id=args.document_id)
    _LOG.info("invalidated %s reuse key(s)", len(marked))
    for key in marked:
        _LOG.info("stale_reuse_key=%s", key)
    return 0


def _stage(args: argparse.Namespace, token: CancelToken) -> int:
    config = load_runtime_config(project_root=args.project_root)
    context = require_frozen_context(config.runs_dir, str(args.run_id))
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
        for line in status_lines(load_status(Path(runs_dir), run_id)):
            _LOG.info("%s", line)
        return 0
    context = load_context(Path(runs_dir), run_id)
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
