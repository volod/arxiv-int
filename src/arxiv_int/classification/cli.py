"""Dependency-light argument parsing for ``arxiv-int classification`` commands."""

import argparse
from pathlib import Path

DEFAULT_TREE_DEPTH = 3


def _run_options(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument(
        "--run-id", required=required, default=None, help="run owning $RUNS_DIR/<run-id>/"
    )
    parser.add_argument("--runs-dir", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)


def _scheme_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scheme",
        type=Path,
        default=None,
        help="scheme snapshot directory (default: $RUNS_DIR/<run-id>/classification/scheme)",
    )


def add_classification_parser(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register the scheme freeze, check, inspect, tree and label commands."""
    parser = subcommands.add_parser(
        "classification", help="freeze, check and inspect the subject taxonomy scheme"
    )
    commands = parser.add_subparsers(dest="classification_command", required=True)
    build = commands.add_parser(
        "build-scheme", help="validate the packaged taxonomy and freeze a checksummed snapshot"
    )
    _run_options(build, required=True)
    check = commands.add_parser(
        "check-scheme", help="re-verify checksums, closure, coverage, licence and staleness"
    )
    _run_options(check, required=False)
    _scheme_option(check)
    check.add_argument("--expect-scheme-id", default=None, help="fail unless this scheme id")
    show = commands.add_parser(
        "show", help="print one class with its path, captions, crosswalk and scheme version"
    )
    _run_options(show, required=False)
    _scheme_option(show)
    show.add_argument("target", help="class id (tax:04.02, ext:NAME, unclassified) or a code")
    tree = commands.add_parser(
        "tree", help="print taxonomy codes and English captions (packaged taxonomy by default)"
    )
    _run_options(tree, required=False)
    _scheme_option(tree)
    tree.add_argument("--root", default=None, help="start below this taxonomy code")
    tree.add_argument("--depth", type=int, default=DEFAULT_TREE_DEPTH, help="levels to print")
    labels = commands.add_parser(
        "freeze-labels", help="validate gold labels and freeze deterministic evaluation splits"
    )
    _run_options(labels, required=True)
    _scheme_option(labels)
    labels.add_argument("--labels", type=Path, required=True, help="gold label JSONL file")
    labels.add_argument("--label-set", required=True, help="stable label set id")
    evaluate = commands.add_parser(
        "evaluate", help="score one classification snapshot against frozen held-out labels"
    )
    _run_options(evaluate, required=True)
    evaluate.add_argument("--classification", type=Path, required=True, help="classify manifest")
    evaluate.add_argument("--labels", type=Path, required=True, help="frozen labels JSONL")
    evaluate.add_argument("--label-set", required=True, help="stable label set id")
    evaluate.add_argument("--split", default="test", help="frozen split name or all")
