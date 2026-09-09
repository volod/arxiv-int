"""Argument parsing for evaluate, fixtures, and proof commands."""

import argparse
from pathlib import Path


def add_evaluate_commands(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register evaluate, fixtures, and proof subcommands."""
    evaluate = commands.add_parser("evaluate", help="score frozen fixtures into a run bundle")
    evaluate.add_argument("--run-id", required=True)
    evaluate.add_argument("--fixture-root", type=Path, default=None)
    evaluate.add_argument("--runs-dir", type=Path, required=True)
    evaluate.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    evaluate.add_argument("--seed", type=int, default=13)
    fixtures = commands.add_parser("fixtures", help="generate or check frozen evaluation fixtures")
    fixture_commands = fixtures.add_subparsers(dest="fixtures_command", required=True)
    for action in ("generate", "check"):
        parser = fixture_commands.add_parser(action, help=f"{action} committed evaluation fixtures")
        parser.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    proof = commands.add_parser("proof", help="discover, publish, or check capability proofs")
    proof_commands = proof.add_subparsers(dest="proof_command", required=True)
    discover = proof_commands.add_parser("discover", help="list registered proof capabilities")
    discover.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    publish = proof_commands.add_parser("publish", help="publish one capability proof bundle")
    publish.add_argument("--capability", required=True)
    publish.add_argument("--run-id", required=True)
    publish.add_argument("--results-dir", type=Path, required=True)
    publish.add_argument("--runs-dir", type=Path, required=True)
    publish.add_argument("--fixture-root", type=Path, default=None)
    publish.add_argument("--archive-dir", type=Path, default=None)
    publish.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    check = proof_commands.add_parser("check", help="verify a published proof directory")
    check.add_argument("--proof-dir", type=Path, required=True)
    check.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    generate_proofs = proof_commands.add_parser(
        "generate-registry", help="write the committed proof capability registry"
    )
    generate_proofs.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
