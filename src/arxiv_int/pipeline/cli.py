"""Argument parsers for pipeline, stage, run, and artifacts commands."""

import argparse
from pathlib import Path

PRECEDENCE_HELP = "CLI overrides process environment, then checkout .env, then documented defaults"
_RANGE_HELP = "dependency-closure endpoint; missing/stale upstream inputs are refused"
_DEFAULT_HELP = f"default from .env ({PRECEDENCE_HELP})"


def add_pipeline_parsers(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register pipeline, stage, run, and artifacts prune commands."""
    pipeline = subcommands.add_parser(
        "pipeline",
        help="forecast, run, update, rebuild, or invalidate a stage DAG",
    )
    pipeline_commands = pipeline.add_subparsers(dest="pipeline_command", required=True)
    _add_forecast_parser(pipeline_commands)
    _add_run_parser(pipeline_commands)
    _add_range_parser(
        pipeline_commands,
        "update",
        "inventory the archive and rerun the changed lineage closure",
    )
    _add_range_parser(
        pipeline_commands,
        "rebuild",
        "create a fresh generation without cache reuse",
    )
    invalidate = pipeline_commands.add_parser(
        "invalidate", help="mark a stage and its descendants logically stale"
    )
    invalidate.add_argument("stage")
    invalidate.add_argument("--document-id", default=None)
    invalidate.add_argument("--run-id", required=True)
    invalidate.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    stage = subcommands.add_parser("stage", help="run one registered stage for a frozen run")
    stage.add_argument("stage")
    stage.add_argument("--run-id", required=True)
    stage.add_argument(
        "--force", action="store_true", help="new attempt without overwriting evidence"
    )
    stage.add_argument("--document-id", default=None)
    stage.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    _add_run_group(subcommands)
    artifacts = subcommands.add_parser(
        "artifacts", help="plan or apply derived-artifact maintenance"
    )
    artifact_commands = artifacts.add_subparsers(dest="artifacts_command", required=True)
    prune = artifact_commands.add_parser(
        "prune", help="plan stale derived deletion (dry-run default)"
    )
    prune.add_argument("--stale", action="store_true", required=True)
    prune.add_argument("--apply", action="store_true", help="apply a previously written plan")
    prune.add_argument("--plan", dest="plan_id", default=None)
    prune.add_argument("--runs-dir", type=Path, default=None)
    prune.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)


def _add_forecast_parser(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    parser = commands.add_parser(
        "forecast",
        help="read-only time, storage, and free-space forecast before heavy work",
    )
    parser.add_argument("--archive-dir", type=Path, default=None, help=_DEFAULT_HELP)
    parser.add_argument("--results-dir", type=Path, default=None, help=_DEFAULT_HELP)
    parser.add_argument(
        "--run-id",
        default=None,
        help="use a created run's frozen inputs; retain the forecast under that run",
    )
    parser.add_argument("--from", dest="from_stage", default=None, help=_RANGE_HELP)
    parser.add_argument("--to", dest="to_stage", default=None, help=_RANGE_HELP)
    parser.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)


def _add_run_parser(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    parser = commands.add_parser("run", help="create a run and execute the selected DAG")
    parser.add_argument("--archive-dir", type=Path, default=None, help=_DEFAULT_HELP)
    parser.add_argument("--results-dir", type=Path, default=None, help=_DEFAULT_HELP)
    parser.add_argument(
        "--profile",
        default=None,
        help="investigation|lexical; default PIPELINE_PROFILE from .env (investigation)",
    )
    parser.add_argument("--from", dest="from_stage", default=None, help=_RANGE_HELP)
    parser.add_argument("--to", dest="to_stage", default=None, help=_RANGE_HELP)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)


def _add_range_parser(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
    name: str,
    help_text: str,
) -> None:
    parser = commands.add_parser(name, help=help_text)
    parser.add_argument("--archive-dir", type=Path, default=None, help=_DEFAULT_HELP)
    parser.add_argument("--results-dir", type=Path, default=None, help=_DEFAULT_HELP)
    parser.add_argument(
        "--run-id", default=None, help="previous run to clone; default is the latest"
    )
    parser.add_argument("--from", dest="from_stage", default=None, help=_RANGE_HELP)
    parser.add_argument("--to", dest="to_stage", default=None, help=_RANGE_HELP)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)


def _add_run_group(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    run = subcommands.add_parser("run", help="create, inspect, or resume a frozen generation")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    create = run_commands.add_parser(
        "create", help="allocate a unique run id and freeze configuration"
    )
    create.add_argument("--archive-dir", type=Path, default=None, help=_DEFAULT_HELP)
    create.add_argument("--results-dir", type=Path, default=None, help=_DEFAULT_HELP)
    create.add_argument("--profile", default=None, help="default PIPELINE_PROFILE from .env")
    create.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    status = run_commands.add_parser("status", help="show per-stage progress for one run")
    status.add_argument("run_id")
    status.add_argument("--runs-dir", type=Path, default=None)
    status.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    resume = run_commands.add_parser("resume", help="continue a halted run by id")
    resume.add_argument("run_id")
    resume.add_argument("--force", action="store_true")
    resume.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    resume.add_argument("--runs-dir", type=Path, default=None)
    finalize = run_commands.add_parser(
        "finalize", help="seal knowledge-base.json; only a complete profile activates"
    )
    finalize.add_argument("run_id")
    finalize.add_argument("--runs-dir", type=Path, default=None)
    finalize.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
