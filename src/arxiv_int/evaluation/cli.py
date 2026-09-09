"""Argument parsing for evaluation bundle, fixture, and proof commands."""

import argparse

from arxiv_int.evaluation.evaluate.cli import add_evaluate_commands


def add_evaluation_parser(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register `arxiv-int evaluation` subcommands."""
    parser = subcommands.add_parser(
        "evaluation",
        help="score frozen fixtures and publish or verify capability proofs",
    )
    commands = parser.add_subparsers(dest="evaluation_command", required=True)
    add_evaluate_commands(commands)
