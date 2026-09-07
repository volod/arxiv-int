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
    resources = commands.add_parser("resources", help="show host GPU VRAM, power, and RAM")
    resources.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    fit = commands.add_parser("fit", help="estimate whether a model fits this host")
    _schedule_args(fit, HEALTH_TIMEOUT_SECONDS)
    schedule = commands.add_parser(
        "schedule", help="acquire the host GPU lease and record why a model ran or fell back"
    )
    _schedule_args(schedule, HEALTH_TIMEOUT_SECONDS)
    schedule.add_argument("--run-id", default="inference", help="run id for telemetry and leases")
    schedule.add_argument("--wait-seconds", type=float, default=30.0)
    schedule.add_argument(
        "--allow-service-control",
        action="store_true",
        help="start or stop the vLLM Compose profile when requested",
    )
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


def _schedule_args(parser: argparse.ArgumentParser, timeout: float) -> None:
    _endpoint_args(parser, timeout)
    parser.add_argument("--model", default=None, help="model id (default: GENERATION_MODEL)")
    parser.add_argument("--context", type=int, default=2048, help="context tokens for the fit")
    parser.add_argument("--batch", type=int, default=1, help="batch size for the fit")
    parser.add_argument(
        "--workload",
        default="generation",
        choices=("generation", "embedding", "rerank", "ocr"),
    )
    parser.add_argument("--allow-cpu", dest="allow_cpu", action="store_true")
    parser.add_argument("--no-allow-cpu", dest="allow_cpu", action="store_false")
    parser.set_defaults(
        allow_cpu=None,
        run_id="inference",
        wait_seconds=30.0,
        allow_service_control=False,
    )
