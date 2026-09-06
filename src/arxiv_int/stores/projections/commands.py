"""CLI handlers for projection build, status, and cleanup."""

import argparse
import logging
from pathlib import Path

from sqlalchemy import create_engine, select

from arxiv_int.contracts.migrations.runner import resolve_database_url
from arxiv_int.runtime.project_root import ProjectRootError, find_project_root
from arxiv_int.stores.projections.lifecycle import build_projections
from arxiv_int.stores.projections.model import (
    ProjectionRequest,
    exit_status,
    requested_kinds,
)
from arxiv_int.stores.projections.tables import ACTIVE, PROJECTIONS

_LOG = logging.getLogger(__name__)


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


def run_projection_command(args: argparse.Namespace) -> int:
    """Dispatch one projection command and return a process status."""
    try:
        root = find_project_root(args.project_root)
        if args.store_command == "projections-status":
            return _run_status(root)
        kinds = requested_kinds(args.kinds)
        request = ProjectionRequest(
            run_id=args.run_id,
            project_root=root,
            kinds=kinds,
            activate=bool(getattr(args, "activate", False)),
            publish=bool(getattr(args, "publish", False)),
            runs_dir=getattr(args, "runs_dir", None),
            skip_dbt=bool(getattr(args, "skip_dbt", False)),
            apply_cleanup=bool(getattr(args, "apply", False)),
            age_enabled=getattr(args, "age_enabled", None),
        )
        result = build_projections(request)
    except (OSError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
        return 1
    _LOG.info(
        "projections %s status=%s version=%s activated=%s artifact=%s",
        args.store_command,
        result.status,
        result.version_id,
        result.activated,
        result.artifact_dir,
    )
    if result.status != "ok" and result.detail:
        _LOG.error("%s", result.detail)
    return exit_status(result)


def _run_status(project_root: Path) -> int:
    url = resolve_database_url()
    if not url:
        _LOG.warning("projection status not-run: no migration database selected")
        return 2
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                select(ACTIVE.c.kind, ACTIVE.c.projection_id, PROJECTIONS.c.status).join(
                    PROJECTIONS, PROJECTIONS.c.projection_id == ACTIVE.c.projection_id
                )
            ).fetchall()
    finally:
        engine.dispose()
    if not rows:
        _LOG.info("no active projections")
        return 0
    for row in rows:
        _LOG.info("active %s %s status=%s", row[0], row[1], row[2])
    return 0
