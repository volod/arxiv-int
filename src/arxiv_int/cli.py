"""Command-line entrypoint for arxiv-int."""

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from arxiv_int.features import inventory_lines
from arxiv_int.metadata import project_info
from arxiv_int.runtime import (
    ComposeConfigurationError,
    ConfigurationError,
    create_results_layout,
    load_runtime_config,
    run_compose,
    validate_runtime_paths,
)

_LOG = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser independently for tests and future subcommands."""
    parser = argparse.ArgumentParser(prog="arxiv-int")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("info", help="show the installed project identity")
    features = subcommands.add_parser("features", help="show optional feature groups")
    features.add_argument("--stage", default=None, help="only groups one pipeline stage needs")
    config = subcommands.add_parser("config", help="resolve and validate runtime configuration")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    show = config_commands.add_parser("show", help="show resolved runtime configuration")
    show.add_argument("--redact", action="store_true", help="mask secrets (always enabled)")
    show.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    show.add_argument("--archive-dir", default=None)
    show.add_argument("--results-dir", default=None)
    show.add_argument("--pgdata-dir", default=None)
    for option in ("runs", "dev-results", "service-state", "model-cache", "tmp", "pg-wal"):
        show.add_argument(f"--{option}-dir", default=None)
    services = subcommands.add_parser("services", help="operate the validated local services")
    service_commands = services.add_subparsers(dest="services_command", required=True)
    for action in ("config", "up", "status", "down"):
        service = service_commands.add_parser(action, help=f"{action} the selected services")
        service.add_argument("--profiles", default="core")
        service.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    logs = service_commands.add_parser("logs", help="show bounded service logs")
    logs.add_argument("--profiles", default="core")
    logs.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    logs.add_argument("--services", default="", help="comma- or whitespace-separated services")
    logs.add_argument("--follow", action="store_true")
    logs.add_argument("--tail", type=int, default=200)
    return parser


def _run_info() -> int:
    info = project_info()
    _LOG.info("%s %s (%s)", info.distribution, info.version, info.package)
    return 0


def _run_features(stage: str | None) -> int:
    try:
        lines = inventory_lines(stage)
    except LookupError as error:
        _LOG.error("%s", error)
        return 1
    for line in lines:
        _LOG.info("%s", line)
    return 0


def _run_config(args: argparse.Namespace) -> int:
    names = (
        "archive",
        "results",
        "pgdata",
        "runs",
        "dev_results",
        "service_state",
        "model_cache",
        "tmp",
        "pg_wal",
    )
    cli = {f"{name.upper()}_DIR": getattr(args, f"{name}_dir") for name in names}
    try:
        config = load_runtime_config(project_root=args.project_root, cli=cli)
        validation = validate_runtime_paths(config)
        created = create_results_layout(config, validation)
    except (ConfigurationError, OSError, RuntimeError) as error:
        _LOG.error("%s", error)
        return 1
    for line in config.rendered(redact=True):
        _LOG.info("%s", line)
    for finding in validation.report.findings:
        if finding.status == "degraded":
            _LOG.warning("%s: degraded: %s", finding.name, finding.detail)
    for placement, evidence in validation.placements:
        rotational = "unknown" if evidence.rotational is None else str(evidence.rotational).lower()
        _LOG.info(
            "%s: class=%s filesystem=%s device=%s rotational=%s free_bytes=%d",
            placement.variable,
            placement.storage_class,
            evidence.filesystem,
            evidence.device_id,
            rotational,
            evidence.free_bytes,
        )
    _LOG.info("runtime layout ready: %d directories", len(created))
    return 0


def _run_services(args: argparse.Namespace) -> int:
    try:
        config = load_runtime_config(project_root=args.project_root)
        service_names = tuple(
            name for name in getattr(args, "services", "").replace(",", " ").split() if name
        )
        return run_compose(
            config,
            args.services_command,
            args.profiles,
            services=service_names,
            follow=getattr(args, "follow", False),
            tail=getattr(args, "tail", 200),
        )
    except (ComposeConfigurationError, ConfigurationError, OSError, RuntimeError) as error:
        _LOG.error("%s", error)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command and return a process status."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args(argv)
    if args.command == "features":
        return _run_features(args.stage)
    if args.command == "config":
        return _run_config(args)
    if args.command == "services":
        return _run_services(args)
    return _run_info()


if __name__ == "__main__":
    raise SystemExit(main())
