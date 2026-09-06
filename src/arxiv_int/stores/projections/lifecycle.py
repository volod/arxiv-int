"""Build, validate, switch, and clean versioned search and graph projections."""

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from arxiv_int.contracts.migrations.runner import resolve_database_url
from arxiv_int.stores.postgres_image.compatibility import load_age_compatibility
from arxiv_int.stores.projections.artifacts import publish_result, write_result
from arxiv_int.stores.projections.builder import build_kind
from arxiv_int.stores.projections.cleanup import apply_cleanup, plan_cleanup
from arxiv_int.stores.projections.ids import sanitize_version_id
from arxiv_int.stores.projections.lock import ProjectionLockError, exclusive_version
from arxiv_int.stores.projections.model import (
    RUN_FAILED,
    RUN_NOT_RUN,
    RUN_OK,
    KindBuild,
    ProjectionRequest,
    ProjectionResult,
)
from arxiv_int.stores.projections.paths import projection_artifact_dir
from arxiv_int.stores.projections.registry import ActivationRefusedError, switch_active

_LOG = logging.getLogger(__name__)


def _age_enabled(request: ProjectionRequest) -> bool:
    if request.age_enabled is not None:
        return request.age_enabled
    return load_age_compatibility(request.project_root).age_enabled


def _result(
    request: ProjectionRequest,
    artifact_dir: Path,
    *,
    status: str,
    version_id: str,
    detail: str,
    kinds: tuple[KindBuild, ...] = (),
    activated: bool = False,
    cleanup_plan: tuple[dict[str, str], ...] = (),
    published: Path | None = None,
) -> ProjectionResult:
    result = ProjectionResult(
        status=status,
        command="build",
        run_id=request.run_id,
        version_id=version_id,
        activatable=bool(kinds) and all(item.publishable for item in kinds),
        activated=activated,
        detail=detail,
        artifact_dir=str(artifact_dir),
        kinds=kinds,
        cleanup_plan=cleanup_plan,
        published_manifest_dir=str(published) if published else None,
    )
    write_result(artifact_dir, result)
    return result


def build_projections(request: ProjectionRequest) -> ProjectionResult:
    """Build staging projections, reconcile them, and optionally switch active pointers."""
    artifact_dir = projection_artifact_dir(request.project_root, request.run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    try:
        version_id = sanitize_version_id(request.run_id)
    except ValueError as error:
        return _result(request, artifact_dir, status=RUN_FAILED, version_id="", detail=str(error))
    url = resolve_database_url(request.database_url)
    if not url:
        return _result(
            request,
            artifact_dir,
            status=RUN_NOT_RUN,
            version_id=version_id,
            detail="no projection database selected",
        )
    try:
        with exclusive_version(request.project_root, version_id):
            result = _build_locked(request, artifact_dir, version_id, url)
    except ProjectionLockError as error:
        return _result(
            request, artifact_dir, status=RUN_FAILED, version_id=version_id, detail=str(error)
        )
    published = publish_result(request, artifact_dir)
    if published is None:
        return result
    return _result(
        request,
        artifact_dir,
        status=result.status,
        version_id=result.version_id,
        detail=result.detail,
        kinds=result.kinds,
        activated=result.activated,
        cleanup_plan=tuple(dict(item) for item in result.cleanup_plan),
        published=published,
    )


def _prepare_inputs(request: ProjectionRequest, url: str) -> str | None:
    if request.skip_dbt:
        return None
    from arxiv_int.transformations.model import TransformRequest
    from arxiv_int.transformations.runner import run_transform

    result = run_transform(
        TransformRequest(
            command="build",
            run_id=request.run_id,
            project_root=request.project_root,
            database_url=url,
            select=("tag:projections",),
            threads=request.threads,
            full_refresh=True,
        )
    )
    return None if result.ok else result.detail


def _build_locked(
    request: ProjectionRequest, artifact_dir: Path, version_id: str, url: str
) -> ProjectionResult:
    age_enabled = _age_enabled(request)
    prepare_error = _prepare_inputs(request, url)
    if prepare_error:
        return _result(
            request, artifact_dir, status=RUN_FAILED, version_id=version_id, detail=prepare_error
        )
    engine = create_engine(url, pool_pre_ping=True)
    kinds: list[KindBuild] = []
    planned: tuple[dict[str, str], ...] = ()
    activated = False
    try:
        with engine.begin() as connection:
            for kind in request.kinds:
                kinds.append(
                    build_kind(
                        connection,
                        request,
                        artifact_dir,
                        kind=kind,
                        version_id=version_id,
                        age_enabled=age_enabled,
                    )
                )
            activatable = bool(kinds) and all(item.publishable for item in kinds)
            if request.activate and activatable:
                for item in kinds:
                    switch_active(
                        connection,
                        kind=item.kind,
                        projection_id=item.projection_id,
                        publishable=True,
                    )
                activated = True
            planned = plan_cleanup(connection)
            if request.apply_cleanup:
                planned = apply_cleanup(connection, planned, age_enabled=age_enabled)
    except (ActivationRefusedError, LookupError, SQLAlchemyError, ValueError) as error:
        return _result(
            request, artifact_dir, status=RUN_FAILED, version_id=version_id, detail=str(error)
        )
    finally:
        engine.dispose()
    status = RUN_OK if kinds and all(item.publishable for item in kinds) else RUN_FAILED
    detail = "projection build complete" if status == RUN_OK else "projection validation failed"
    result = _result(
        request,
        artifact_dir,
        status=status,
        version_id=version_id,
        detail=detail,
        kinds=tuple(kinds),
        activated=activated,
        cleanup_plan=planned,
    )
    _LOG.info(
        "projection build status=%s version=%s activated=%s",
        result.status,
        version_id,
        result.activated,
    )
    return result
