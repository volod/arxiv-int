"""Dependency-light argument parsing for artifact inspection."""

import argparse
from pathlib import Path

from arxiv_int.inspect.model import DEFAULT_LIMIT


def add_inspect_parser(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register ``arxiv-int inspect DATASET|RUN|latest``."""
    parser = subcommands.add_parser(
        "inspect",
        help="summarize published stage artifacts without recomputing them",
    )
    parser.add_argument(
        "target",
        help="run id from arxiv-int run create, dataset id, or latest",
    )
    _inspect_flags(parser)


def add_run_artifacts_parser(parser: argparse.ArgumentParser) -> None:
    """Register flags shared with ``arxiv-int run artifacts RUN_ID``."""
    _inspect_flags(parser)


def _inspect_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="bounded sample size for partitions, quality rows, and anchors",
    )
    parser.add_argument("--json", action="store_true", help="write JSON to stdout")
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--results-dir", type=Path, default=None)
    parser.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
