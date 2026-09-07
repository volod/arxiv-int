"""CLI handlers for `arxiv-int transform parse|compile|build|test`."""

import argparse
import logging
from pathlib import Path

from arxiv_int.runtime.project_root import ProjectRootError, find_project_root
from arxiv_int.transformations.model import COMMANDS, DEFAULT_SELECT, TransformRequest, exit_status

_LOG = logging.getLogger(__name__)


def add_transform_parser(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register `arxiv-int transform` and its parse/compile/build/test commands."""
    transform = subcommands.add_parser(
        "transform",
        help="parse, compile, build, or test isolated derived dbt models",
    )
    commands = transform.add_subparsers(dest="transform_command", required=True)
    for action in COMMANDS:
        parser = commands.add_parser(action, help=f"{action} described dbt models")
        parser.add_argument("--run-id", required=True, help="run identifier for dbt evidence")
        parser.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
        parser.add_argument("--select", nargs="*", default=None, help="dbt --select arguments")
        parser.add_argument("--threads", type=int, default=2)
        parser.add_argument("--full-refresh", action="store_true")
        parser.add_argument("--policy-version", default="1")
        parser.add_argument("--activate", action="store_true")
        parser.add_argument("--publish", action="store_true")
        parser.add_argument("--runs-dir", type=Path, default=None)
        parser.add_argument("--fail-tests", action="store_true", help=argparse.SUPPRESS)


def run_transform_command(args: argparse.Namespace) -> int:
    """Run one transform command and write secret-free evidence under DATA_DIR."""
    try:
        root = find_project_root(args.project_root)
        from arxiv_int.transformations.runner import run_transform

        select = tuple(args.select) if args.select else DEFAULT_SELECT
        request = TransformRequest(
            command=args.transform_command,
            run_id=args.run_id,
            project_root=root,
            select=select,
            threads=args.threads,
            full_refresh=args.full_refresh,
            fail_tests=args.fail_tests,
            policy_version=args.policy_version,
            activate=args.activate,
            publish=args.publish,
            runs_dir=args.runs_dir,
        )
        result = run_transform(request)
    except (OSError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
        return 1
    _LOG.info(
        "transform %s status=%s generation=%s activatable=%s artifact=%s",
        result.command,
        result.status,
        result.generation_id,
        result.activatable,
        result.artifact_dir,
    )
    if result.status != "ok":
        _LOG.error("%s", result.detail)
    return exit_status(result)
