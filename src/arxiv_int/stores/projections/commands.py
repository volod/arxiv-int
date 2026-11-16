"""CLI handlers for projection build, status, and cleanup."""

import argparse
import logging
from pathlib import Path

from sqlalchemy import create_engine, select

from arxiv_int.runtime.project_root import ProjectRootError, find_project_root
from arxiv_int.stores.postgres.selection import optional_store_url
from arxiv_int.stores.projections.lifecycle import build_projections
from arxiv_int.stores.projections.model import (
    ProjectionRequest,
    exit_status,
    requested_kinds,
)
from arxiv_int.stores.projections.tables import ACTIVE, PROJECTIONS

_LOG = logging.getLogger(__name__)


def run_projection_command(args: argparse.Namespace) -> int:
    """Dispatch one projection command and return a process status."""
    try:
        root = find_project_root(args.project_root)
        if args.store_command == "projections-status":
            return _run_status(root)
        kinds = requested_kinds(args.kinds)
        if args.store_command == "projections-cleanup":
            return _run_cleanup(root, args.run_id, apply=args.apply, kinds=kinds)
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
    url = optional_store_url(project_root)
    if not url:
        _LOG.warning("projection status not-run: no canonical store is configured")
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


def _run_cleanup(project_root: Path, run_id: str, *, apply: bool, kinds: tuple[str, ...]) -> int:
    from arxiv_int.stores.postgres_image.compatibility import load_age_compatibility
    from arxiv_int.stores.projections.artifacts import write_result
    from arxiv_int.stores.projections.cleanup import apply_cleanup, plan_cleanup
    from arxiv_int.stores.projections.model import ProjectionResult
    from arxiv_int.stores.projections.paths import projection_artifact_dir

    url = optional_store_url(project_root)
    if not url:
        _LOG.warning("projection cleanup not-run: no canonical store is configured")
        return 2
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            planned = plan_cleanup(connection, kinds=kinds)
            if apply:
                planned = apply_cleanup(
                    connection,
                    planned,
                    age_enabled=load_age_compatibility(project_root).age_enabled,
                )
    finally:
        engine.dispose()
    artifact_dir = projection_artifact_dir(project_root, run_id)
    result = ProjectionResult(
        status="ok",
        command="cleanup",
        run_id=run_id,
        version_id="",
        activatable=False,
        activated=False,
        detail="cleanup executed" if apply else "cleanup planned",
        artifact_dir=str(artifact_dir),
        cleanup_plan=planned,
    )
    write_result(artifact_dir, result)
    _LOG.info("projection cleanup count=%s apply=%s artifact=%s", len(planned), apply, artifact_dir)
    return 0
