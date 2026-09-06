"""Command-line entrypoint for arxiv-int."""

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from arxiv_int.features import inventory_lines
from arxiv_int.metadata import project_info
from arxiv_int.readiness.run import run_readiness
from arxiv_int.runtime import (
    ComposeConfigurationError,
    ConfigurationError,
    create_results_layout,
    load_runtime_config,
    run_compose,
    validate_runtime_paths,
)
from arxiv_int.runtime.service_plan import PROFILE_HELP

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
    for option in ("runs", "service-state", "model-cache", "tmp", "pg-wal"):
        show.add_argument(f"--{option}-dir", default=None)
    readiness = subcommands.add_parser("readiness", help="report workstation readiness")
    readiness.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    readiness.add_argument("--profiles", default="pipeline", help=PROFILE_HELP)
    readiness.add_argument(
        "--timeout", type=float, default=3.0, help="per-check timeout in seconds"
    )
    readiness.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="report path under RESULTS_DIR (default: reports/readiness.json)",
    )
    readiness.add_argument(
        "--no-json-report",
        action="store_true",
        help="do not persist the default JSON report",
    )
    services = subcommands.add_parser("services", help="operate the validated local services")
    service_commands = services.add_subparsers(dest="services_command", required=True)
    for action in ("config", "up", "status", "down"):
        service = service_commands.add_parser(action, help=f"{action} the selected services")
        service.add_argument("--profiles", default="pipeline", help=PROFILE_HELP)
        service.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    reset = service_commands.add_parser(
        "reset",
        help="stop services and erase service data roots (dry-run unless --apply)",
    )
    reset.add_argument("--profiles", default="pipeline", help=PROFILE_HELP)
    reset.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    reset.add_argument(
        "--apply",
        action="store_true",
        help="erase PGDATA, service-state, model-cache, and optional WAL/tablespace roots",
    )
    logs = service_commands.add_parser("logs", help="show bounded service logs")
    logs.add_argument("--profiles", default="pipeline", help=PROFILE_HELP)
    logs.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    logs.add_argument("--services", default="", help="comma- or whitespace-separated services")
    logs.add_argument("--follow", action="store_true")
    logs.add_argument("--tail", type=int, default=200)
    contracts = subcommands.add_parser("contracts", help="validate product ODCS contracts")
    contract_commands = contracts.add_subparsers(dest="contracts_command", required=True)
    lint = contract_commands.add_parser(
        "lint", help="lint ODCS schema, integrity, and Data Contract CLI"
    )
    lint.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    lint.add_argument(
        "--skip-datacontract",
        action="store_true",
        help="skip Data Contract CLI lint (official JSON Schema still runs)",
    )
    generate = contract_commands.add_parser(
        "generate", help="generate deterministic physical schemas from ODCS"
    )
    generate.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    check = contract_commands.add_parser(
        "check", help="fail when contracts/generated drifts from regeneration"
    )
    check.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    evolution = contract_commands.add_parser(
        "evolution",
        help="check reviewed baselines, migrations, and compatibility policy",
    )
    evolution.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    evolution.add_argument(
        "--skip-live-sql",
        action="store_true",
        help="skip disposable Postgres apply of baseline CREATE TABLE SQL",
    )
    ontology = subcommands.add_parser("ontology", help="validate versioned ontology assets")
    ontology_commands = ontology.add_subparsers(dest="ontology_command", required=True)
    ontology_check = ontology_commands.add_parser(
        "check",
        help="parse RDF/SHACL, verify bindings, generation drift, and evolution baseline",
    )
    ontology_check.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    ontology_generate = ontology_commands.add_parser(
        "generate", help="regenerate committed ontology.* bindings"
    )
    ontology_generate.add_argument(
        "--project-root", type=Path, default=None, help=argparse.SUPPRESS
    )
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
            apply=getattr(args, "apply", False),
        )
    except (ComposeConfigurationError, ConfigurationError, OSError, RuntimeError) as error:
        _LOG.error("%s", error)
        return 1


def _run_readiness(args: argparse.Namespace) -> int:
    try:
        result = run_readiness(
            project_root=args.project_root,
            profiles=args.profiles,
            timeout=args.timeout,
            report_path=args.json_report,
            persist=not args.no_json_report,
        )
    except ValueError as error:
        _LOG.error("%s", error)
        return 1
    color = sys.stderr.isatty() and "NO_COLOR" not in os.environ
    for line in result.report.console_lines(color=color):
        if "[BLOCKED]" in line:
            _LOG.error("%s", line)
        elif "[DEGRADED]" in line:
            _LOG.warning("%s", line)
        else:
            _LOG.info("%s", line)
    if result.report_path is not None:
        _LOG.info("JSON report: %s", result.report_path)
    return result.report.exit_code


def _log_findings(findings: list[str] | tuple[str, ...]) -> None:
    for finding in findings:
        _LOG.error("%s", finding)


def _run_contracts(args: argparse.Namespace) -> int:
    from arxiv_int.contracts.evolution import check_evolution_policy
    from arxiv_int.contracts.generate import check_generation_drift, generate_all_contracts
    from arxiv_int.contracts.lint import contracts_root_for, lint_contracts
    from arxiv_int.runtime.project_root import ProjectRootError, find_project_root

    try:
        root = find_project_root(args.project_root)
        contracts_root = contracts_root_for(root)
        command = args.contracts_command
        if command == "generate":
            result = generate_all_contracts(contracts_root)
            _LOG.info(
                "generated %d artifact(s); manifest=%s",
                len(result.files),
                result.manifest_fingerprint[:12],
            )
            return 0
        if command == "check":
            findings = check_generation_drift(contracts_root)
            if findings:
                _log_findings(findings)
                return 1
            _LOG.info("contracts generation drift check passed")
            return 0
        if command == "evolution":
            report = check_evolution_policy(
                contracts_root,
                project_root=root,
                include_live_sql=not args.skip_live_sql,
            )
            if report.findings:
                _log_findings(report.findings)
                return 1
            _LOG.info(
                "contracts evolution policy passed: %d contract(s)",
                report.checked_contracts,
            )
            return 0
        lint_report = lint_contracts(
            contracts_root,
            run_datacontract=not args.skip_datacontract,
        )
    except (OSError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
        return 1
    if lint_report.ok:
        _LOG.info(
            "contracts lint passed: %d dataset(s); datacontract=%s",
            lint_report.checked_datasets,
            lint_report.datacontract_ran,
        )
        return 0
    _log_findings(lint_report.findings)
    return 1


def _run_ontology(args: argparse.Namespace) -> int:
    from arxiv_int.ontology.check import check_ontology
    from arxiv_int.ontology.generate import generate_ontology_bindings
    from arxiv_int.ontology.paths import ontology_root_for
    from arxiv_int.runtime.project_root import ProjectRootError, find_project_root

    try:
        root = find_project_root(args.project_root)
        ontology_root = ontology_root_for(root)
        if args.ontology_command == "generate":
            files = generate_ontology_bindings(ontology_root)
            _LOG.info("generated %d ontology binding artifact(s)", len(files))
            return 0
        report = check_ontology(ontology_root, project_root=root)
    except (OSError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
        return 1
    if report.ok:
        _LOG.info(
            "ontology check passed: %d class(es), %d predicate(s)",
            report.checked_classes,
            report.checked_predicates,
        )
        return 0
    _log_findings(report.findings)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command and return a process status."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args(argv)
    if args.command == "features":
        return _run_features(args.stage)
    if args.command == "config":
        return _run_config(args)
    if args.command == "readiness":
        return _run_readiness(args)
    if args.command == "services":
        return _run_services(args)
    if args.command == "contracts":
        return _run_contracts(args)
    if args.command == "ontology":
        return _run_ontology(args)
    return _run_info()


if __name__ == "__main__":
    raise SystemExit(main())
