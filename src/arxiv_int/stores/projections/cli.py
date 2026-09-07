"""Dependency-free projection argument parsing for the base CLI."""

import argparse
from pathlib import Path


def add_projection_parsers(
    store_commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register store projections-build, projections-status, and projections-cleanup."""
    build = store_commands.add_parser(
        "projections-build",
        help="build, validate, and optionally activate search and graph projections",
    )
    _add_common(build)
    build.add_argument("--activate", action="store_true")
    build.add_argument("--publish", action="store_true")
    build.add_argument("--runs-dir", type=Path, default=None)
    build.add_argument("--skip-dbt", action="store_true")
    build.add_argument("--age-enabled", dest="age_enabled", action="store_true")
    build.add_argument("--age-disabled", dest="age_enabled", action="store_false")
    build.set_defaults(age_enabled=None)
    status = store_commands.add_parser(
        "projections-status", help="show active projection pointers without building"
    )
    _add_common(status, kinds=False)
    cleanup = store_commands.add_parser(
        "projections-cleanup", help="plan or drop retired and failed projection objects"
    )
    _add_common(cleanup)
    cleanup.add_argument("--apply", action="store_true")


def _add_common(parser: argparse.ArgumentParser, *, kinds: bool = True) -> None:
    parser.add_argument("--run-id", required=True, help="run identifier for projection evidence")
    parser.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    if kinds:
        parser.add_argument("--kind", action="append", dest="kinds", default=None)
