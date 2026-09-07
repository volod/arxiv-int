"""CLI handlers for aggregate and atomic setup commands."""

import argparse
import logging
import os
import signal
from pathlib import Path

from arxiv_int.runtime.project_root import ProjectRootError, find_project_root
from arxiv_int.runtime.setup.adapters import production_adapters
from arxiv_int.runtime.setup.coordinator import run_setup
from arxiv_int.runtime.setup.model import ATOMIC_PHASES
from arxiv_int.runtime.setup.report import console_lines

_LOG = logging.getLogger(__name__)


def add_setup_parser(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register `arxiv-int setup` and its independent phase selector."""
    setup = subcommands.add_parser(
        "setup",
        help="prepare environment, models, services and schema; retry after .env edits",
    )
    setup.add_argument(
        "--phase",
        choices=tuple(sorted(ATOMIC_PHASES)),
        default=None,
        help="run one atomic setup phase",
    )
    setup.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)


def run_setup_command(args: argparse.Namespace) -> int:
    """Run setup and print redacted per-phase status."""
    adapters = production_adapters()
    previous = signal.getsignal(signal.SIGINT)

    def _cancel(_signum: int, _frame: object) -> None:
        adapters.cancel.cancel()

    signal.signal(signal.SIGINT, _cancel)
    try:
        root = find_project_root(args.project_root)
        report = run_setup(
            project_root=root,
            phase=args.phase,
            environment=os.environ,
            adapters=adapters,
        )
    except (OSError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
        return 1
    finally:
        signal.signal(signal.SIGINT, previous)
    for line in console_lines(report):
        if line.startswith("[BLOCKED]") or line.startswith("[CANCELLED]"):
            _LOG.error("%s", line)
        elif line.startswith("[DEGRADED]"):
            _LOG.warning("%s", line)
        else:
            _LOG.info("%s", line)
    if report.report_path is not None:
        _LOG.info("JSON report: %s", report.report_path)
    return report.exit_code


def resolve_cli_profiles(explicit: str | None, project_root: Path | None) -> str:
    """Use an explicit --profiles value, otherwise SERVICE_PROFILES from config."""
    if explicit:
        return explicit
    from arxiv_int.runtime.setup.settings import load_setup_settings

    try:
        return load_setup_settings(project_root=project_root).service_profiles
    except (OSError, ValueError):
        return os.environ.get("SERVICE_PROFILES", "").strip() or "pipeline"
