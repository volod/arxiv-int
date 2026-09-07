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
from arxiv_int.runtime.setup.commands import (
    add_setup_parser,
    resolve_cli_profiles,
    run_setup_command,
)

_LOG = logging.getLogger(__name__)

DB_COMMAND_HELP = {
    "revision": "generate a candidate immutable revision from contract changes",
    "check": "check the revision graph, checksums, and pending contract changes",
    "status": "report the applied revision of an explicitly selected database",
    "upgrade": "apply revisions to an explicitly selected database",
    "downgrade": "reverse revisions on an explicitly selected database",
    "adopt": "report why stamping an existing database is refused",
}


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
    readiness.add_argument("--profiles", default=None, help=PROFILE_HELP)
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
        service.add_argument("--profiles", default=None, help=PROFILE_HELP)
        service.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    reset = service_commands.add_parser(
        "reset",
        help="stop services and erase service data roots (dry-run unless --apply)",
    )
    reset.add_argument("--profiles", default=None, help=PROFILE_HELP)
    reset.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    reset.add_argument(
        "--apply",
        action="store_true",
        help="erase PGDATA, service-state, model-cache, and optional WAL/tablespace roots",
    )
    logs = service_commands.add_parser("logs", help="show bounded service logs")
    logs.add_argument("--profiles", default=None, help=PROFILE_HELP)
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
    database = subcommands.add_parser(
        "db", help="author, check, and apply owned canonical schema revisions"
    )
    migration_commands = database.add_subparsers(dest="db_command", required=True)
    for action in ("revision", "check", "status", "upgrade", "downgrade", "adopt"):
        migration = migration_commands.add_parser(action, help=DB_COMMAND_HELP[action])
        migration.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
        if action == "revision":
            migration.add_argument(
                "--message", default="contract schema change", help="revision summary"
            )
        if action in ("upgrade", "downgrade"):
            migration.add_argument(
                "--revision",
                default="head" if action == "upgrade" else "-1",
                help="target revision for the explicitly selected database",
            )
        if action == "upgrade":
            migration.add_argument(
                "--sql",
                action="store_true",
                help="emit review SQL offline instead of applying it",
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
    store = subcommands.add_parser(
        "store", help="build, probe, and apply the pinned PostgreSQL store"
    )
    store_commands = store.add_subparsers(dest="store_command", required=True)
    store_build = store_commands.add_parser("build-image", help="build the ParadeDB+AGE image")
    store_build.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    store_build.add_argument(
        "--no-cache",
        action="store_true",
        help="build without the Docker layer cache",
    )
    store_probe = store_commands.add_parser(
        "probe-image",
        help="run disposable extension probes against PGDATA_DIR",
    )
    store_probe.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    store_probe.add_argument(
        "--pgdata-dir",
        type=Path,
        default=None,
        help="disposable PGDATA_DIR (default: $DATA_DIR/postgres-image-probe/<run-id>)",
    )
    store_probe.add_argument(
        "--write-gate",
        action="store_true",
        help="record docker/postgres/age-compatibility.json from probe results",
    )
    store_apply = store_commands.add_parser(
        "apply-schema",
        help="apply owned Alembic revisions on a selected or disposable database",
    )
    store_apply.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    store_apply.add_argument("--revision", default="head")
    store_apply.add_argument("--run-id", default=None, help="evidence id under DATA_DIR/migrations")
    store_apply.add_argument(
        "--pgdata-dir",
        type=Path,
        default=None,
        help="disposable PGDATA_DIR when no ARXIV_INT_MIGRATION_DATABASE_URL is set",
    )
    store_inspect = store_commands.add_parser(
        "inspect-schema",
        help="inspect live catalog conformance without applying revisions",
    )
    store_inspect.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    store_inspect.add_argument("--run-id", default=None)
    from arxiv_int.stores.projections.cli import add_projection_parsers

    add_projection_parsers(store_commands)

    quality = subcommands.add_parser(
        "data-quality", help="validate dataset contents against contracts"
    )
    quality_commands = quality.add_subparsers(dest="quality_command", required=True)
    check = quality_commands.add_parser("check", help="validate one dataset batch or snapshot")
    check.add_argument("dataset", help="contract dataset id")
    check.add_argument("--run-id", required=True, help="run identifier for quality evidence")
    check.add_argument("--input", type=Path, required=True, help="parquet, arrow, or JSON table")
    check.add_argument(
        "--related",
        action="append",
        default=[],
        metavar="DATASET=PATH",
        help="related dataset for relationship checks (repeatable)",
    )
    check.add_argument("--batch-rows", type=int, default=50000)
    check.add_argument("--spill-bytes", type=int, default=67108864)
    check.add_argument("--min-rows", type=int, default=0)
    check.add_argument("--failure-samples", type=int, default=5)
    check.add_argument("--skip-snapshot", action="store_true", help="leave global checks not-run")
    check.add_argument("--publish", action="store_true", help="copy evidence to RUNS_DIR")
    check.add_argument("--runs-dir", type=Path, default=None)
    check.add_argument("--project-root", type=Path, default=None, help=argparse.SUPPRESS)
    add_setup_parser(subcommands)
    from arxiv_int.transformations.commands import add_transform_parser

    add_transform_parser(subcommands)
    from arxiv_int.inference.cli import add_inference_parser

    add_inference_parser(subcommands)
    from arxiv_int.evaluation.export_cli import add_evaluation_parser

    add_evaluation_parser(subcommands)
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
            resolve_cli_profiles(args.profiles, args.project_root),
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
            profiles=resolve_cli_profiles(args.profiles, args.project_root),
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


def _run_db(args: argparse.Namespace) -> int:
    from arxiv_int.contracts.lint import contracts_root_for
    from arxiv_int.contracts.migrations import commands
    from arxiv_int.runtime.project_root import ProjectRootError, find_project_root

    try:
        root = find_project_root(args.project_root)
        contracts_root = contracts_root_for(root)
        command = args.db_command
        if command == "revision":
            return commands.run_revision(root, contracts_root, args.message)
        if command == "check":
            return commands.run_check(root, contracts_root)
        if command == "adopt":
            from arxiv_int.stores.postgres.commands import run_adopt_schema

            return run_adopt_schema(root, run_id="adopt")
        if command == "upgrade" and args.sql:
            return commands.run_offline_sql(root, contracts_root, args.revision)
        return commands.run_apply(root, contracts_root, command, getattr(args, "revision", "head"))
    except (OSError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
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


def _tool_data_dir(root: Path) -> Path:
    """Return the developer artifact root used for disposable store PGDATA."""
    data_root = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else root / ".data"
    if not data_root.is_absolute():
        data_root = (root / data_root).resolve()
    return data_root


def _run_store(args: argparse.Namespace) -> int:
    from arxiv_int.runtime.project_root import ProjectRootError, find_project_root
    from arxiv_int.stores.postgres.commands import run_apply_schema, run_inspect_schema
    from arxiv_int.stores.postgres_image.commands import run_build_command, run_probe_command

    try:
        root = find_project_root(args.project_root)
        if args.store_command == "build-image":
            return run_build_command(root, no_cache=args.no_cache)
        if args.store_command == "apply-schema":
            run_id = args.run_id or f"apply-{os.getpid()}"
            pgdata = args.pgdata_dir or _tool_data_dir(root) / "migrations" / run_id / "pgdata"
            return run_apply_schema(
                root,
                pgdata_dir=pgdata,
                run_id=run_id,
                revision=args.revision,
            )
        if args.store_command == "inspect-schema":
            run_id = args.run_id or f"inspect-{os.getpid()}"
            return run_inspect_schema(root, run_id=run_id)
        if args.store_command.startswith("projections-"):
            from arxiv_int.stores.projections.commands import run_projection_command

            return run_projection_command(args)
        pgdata = args.pgdata_dir
        if pgdata is None:
            run_id = f"probe-{os.getpid()}"
            pgdata = _tool_data_dir(root) / "postgres-image-probe" / run_id / "pgdata"
        return run_probe_command(root, pgdata, write_gate=args.write_gate)
    except (OSError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
        return 1


def _parse_related(values: list[str]) -> dict[str, Path]:
    related: dict[str, Path] = {}
    for item in values:
        dataset, separator, raw_path = item.partition("=")
        if not separator or not dataset or not raw_path:
            raise ValueError(f"related dataset must be DATASET=PATH, got {item!r}")
        related[dataset] = Path(raw_path)
    return related


def _run_data_quality(args: argparse.Namespace) -> int:
    from arxiv_int.data_quality.commands import run_check
    from arxiv_int.data_quality.model import ValidationLimits
    from arxiv_int.runtime.project_root import ProjectRootError

    try:
        related = _parse_related(args.related)
        return run_check(
            args.dataset,
            run_id=args.run_id,
            input_path=args.input,
            related=related,
            project_root=args.project_root,
            execute_snapshot=not args.skip_snapshot,
            publish=args.publish,
            runs_dir=args.runs_dir,
            limits=ValidationLimits(
                batch_rows=args.batch_rows,
                spill_bytes=args.spill_bytes,
                failure_samples=args.failure_samples,
                min_rows=args.min_rows,
            ),
        )
    except (OSError, ProjectRootError, RuntimeError, ValueError) as error:
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
    if args.command == "readiness":
        return _run_readiness(args)
    if args.command == "services":
        return _run_services(args)
    if args.command == "contracts":
        return _run_contracts(args)
    if args.command == "db":
        return _run_db(args)
    if args.command == "ontology":
        return _run_ontology(args)
    if args.command == "store":
        return _run_store(args)
    if args.command == "setup":
        return run_setup_command(args)
    if args.command == "data-quality":
        return _run_data_quality(args)
    if args.command == "transform":
        from arxiv_int.transformations.commands import run_transform_command

        return run_transform_command(args)
    if args.command == "inference":
        from arxiv_int.inference.commands import run_inference_command

        return run_inference_command(args)
    if args.command == "evaluation":
        from arxiv_int.evaluation.export_commands import run_evaluation_command

        return run_evaluation_command(args)
    return _run_info()


if __name__ == "__main__":
    raise SystemExit(main())
