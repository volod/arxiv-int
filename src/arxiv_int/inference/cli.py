"""Dependency-light inference argument parsing for the base CLI."""

import argparse
from pathlib import Path

from arxiv_int.inference.client import HEALTH_TIMEOUT_SECONDS


def add_inference_parser(
    subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Register `arxiv-int inference` health, models, identity, and schema commands."""
    parser = subcommands.add_parser(
        "inference",
        help="call the configured local Ollama or vLLM endpoint",
    )
    commands = parser.add_subparsers(dest="inference_command", required=True)
    health = commands.add_parser("health", help="check that the local inference API responds")
    _endpoint_args(health, HEALTH_TIMEOUT_SECONDS)
    models = commands.add_parser("models", help="list models served by the local inference API")
    _endpoint_args(models, HEALTH_TIMEOUT_SECONDS)
    identity = commands.add_parser("identity", help="show digest and capabilities for one model")
    _endpoint_args(identity, HEALTH_TIMEOUT_SECONDS)
    identity.add_argument("--model", default=None, help="model id (default: GENERATION_MODEL)")
    schemas = commands.add_parser("schemas", help="generate or check structured-output schemas")
    schema_commands = schemas.add_subparsers(dest="schemas_command", required=True)
    generate = schema_commands.add_parser("generate", help="write committed JSON Schema files")
    generate.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    check = schema_commands.add_parser("check", help="fail when committed schemas drift")
    check.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)


def _endpoint_args(parser: argparse.ArgumentParser, timeout: float) -> None:
    parser.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--timeout",
        type=float,
        default=timeout,
        help="per-request timeout in seconds",
    )
    parser.set_defaults(timeout=timeout)
