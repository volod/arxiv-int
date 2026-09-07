"""Argument parsing for Git-bound proof identity export."""

import argparse
from pathlib import Path


def add_evaluation_parser(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register `arxiv-int evaluation` export and policy commands."""
    parser = subcommands.add_parser(
        "evaluation",
        help="verify evaluation bundles and export Git-bound proof copies",
    )
    commands = parser.add_subparsers(dest="evaluation_command", required=True)
    export_proof = commands.add_parser(
        "export-proof",
        help="write identity-obfuscated copies of selected proof artifacts",
    )
    export_proof.add_argument("--source-bundle", type=Path, required=True)
    export_proof.add_argument(
        "--map",
        action="append",
        required=True,
        metavar="ARTIFACT=DEST",
        help="source bundle artifact to Git-bound destination (repeatable)",
    )
    export_proof.add_argument("--run-id", required=True, help="diagnostic id under DATA_DIR")
    export_proof.add_argument(
        "--destination-root",
        type=Path,
        default=None,
        help="resolve relative destinations against this root (default: project root)",
    )
    export_proof.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help="optional identity-free receipt path",
    )
    export_proof.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    policy = commands.add_parser(
        "identity-policy",
        help="generate or check the committed proof-identity policy",
    )
    policy_commands = policy.add_subparsers(dest="identity_policy_command", required=True)
    generate = policy_commands.add_parser("generate", help="write the committed policy document")
    generate.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    check = policy_commands.add_parser("check", help="fail when the committed policy drifts")
    check.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    from arxiv_int.evaluation.eval_cli import add_evaluate_commands

    add_evaluate_commands(commands)


def parse_export_maps(values: list[str]) -> list[tuple[str, Path]]:
    """Parse repeatable ARTIFACT=DEST mappings."""
    mappings: list[tuple[str, Path]] = []
    for item in values:
        artifact, separator, raw_path = item.partition("=")
        if not separator or not artifact or not raw_path:
            raise ValueError(f"export map must be ARTIFACT=DEST, got {item!r}")
        mappings.append((artifact, Path(raw_path)))
    return mappings
