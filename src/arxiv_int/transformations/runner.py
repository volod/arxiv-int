"""Orchestrate parse/compile/build/test with isolated generations and activation."""

import logging
from pathlib import Path

from arxiv_int.transformations.activation import ActivationRefusedError, activate_generation
from arxiv_int.transformations.artifacts import (
    compiled_sql_fingerprint,
    load_json,
    relation_names,
    rule_outcomes_from_run_results,
    sanitize_log_files,
)
from arxiv_int.transformations.credentials import (
    DbtCredentials,
    parse_credentials,
    resolve_database_url,
    sanitize_generation_id,
)
from arxiv_int.transformations.invoke import InvokeOutcome, dbt_cli_args, invoke_dbt
from arxiv_int.transformations.lock import GenerationLockError, exclusive_generation
from arxiv_int.transformations.model import (
    COMMANDS,
    STATUS_FAILED,
    STATUS_NOT_RUN,
    STATUS_OK,
    TransformRequest,
    TransformResult,
    required_database,
)
from arxiv_int.transformations.paths import dbt_artifact_dir
from arxiv_int.transformations.persist import (
    build_result,
    publish_result,
    sanitize_target,
    vars_payload,
    write_result,
)
from arxiv_int.transformations.project import ProjectAssemblyError, assemble_working_project

_LOG = logging.getLogger(__name__)


def _placeholder_credentials(threads: int) -> DbtCredentials:
    return DbtCredentials(
        host="127.0.0.1",
        user="arxiv_int",
        password="unused",
        port="5432",
        dbname="arxiv_int",
        threads=threads,
    )


def _row_counts(url: str, names: tuple[str, ...]) -> dict[str, int]:
    from arxiv_int.stores.postgres.apply import row_counts

    return row_counts(url, names)


def _fail(
    request: TransformRequest, artifact_dir: Path, detail: str, generation_id: str
) -> TransformResult:
    result = build_result(
        request,
        status=STATUS_FAILED,
        detail=detail,
        generation_id=generation_id,
        artifact_dir=artifact_dir,
    )
    write_result(artifact_dir, result)
    return result


def run_transform(request: TransformRequest) -> TransformResult:
    """Parse, compile, build, or test models into an isolated derived generation."""
    artifact_dir = dbt_artifact_dir(request.project_root, request.run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if request.command not in COMMANDS:
        return _fail(request, artifact_dir, f"unknown transform command '{request.command}'", "")
    try:
        generation_id = sanitize_generation_id(request.run_id)
    except ValueError as error:
        return _fail(request, artifact_dir, str(error), "")
    url = resolve_database_url(request.database_url)
    if required_database(request.command) and not url:
        result = build_result(
            request,
            status=STATUS_NOT_RUN,
            detail="no transform database selected",
            generation_id=generation_id,
            artifact_dir=artifact_dir,
        )
        write_result(artifact_dir, result)
        return result
    try:
        with exclusive_generation(request.project_root, generation_id):
            project_dir = assemble_working_project(request.project_root, artifact_dir)
            credentials = parse_credentials(url, threads=request.threads) if url else None
            resolved = credentials or _placeholder_credentials(request.threads)
            return _invoke_locked(request, artifact_dir, project_dir, generation_id, url, resolved)
    except GenerationLockError as error:
        return _fail(request, artifact_dir, str(error), generation_id)
    except (OSError, ProjectAssemblyError, ValueError) as error:
        return _fail(request, artifact_dir, str(error), generation_id)


def _invoke_locked(
    request: TransformRequest,
    artifact_dir: Path,
    project_dir: Path,
    generation_id: str,
    url: str | None,
    credentials: DbtCredentials,
) -> TransformResult:
    target_dir = artifact_dir / "target"
    log_dir = artifact_dir / "logs"
    args = dbt_cli_args(
        request.command,
        project_dir=project_dir,
        profiles=artifact_dir / "profiles",
        target_dir=target_dir,
        log_dir=log_dir,
        select=request.select,
        vars_payload=vars_payload(request, generation_id),
        full_refresh=request.full_refresh,
        threads=credentials.threads,
    )
    outcome: InvokeOutcome = invoke_dbt(args, credentials)
    sanitize_target(artifact_dir)
    secrets = (credentials.password,) if credentials.password else ()
    sanitize_log_files(log_dir, secrets)
    rules = rule_outcomes_from_run_results(
        load_json(artifact_dir / "manifests" / "run_results.json")
    )
    model_fp = compiled_sql_fingerprint(target_dir)
    relations = relation_names(generation_id) if request.command in {"build", "test"} else ()
    counts = _row_counts(url, relations) if url and outcome.success and relations else {}
    activatable = outcome.success and request.command in {"build", "test"}
    status = STATUS_OK if outcome.success else STATUS_FAILED
    result = build_result(
        request,
        status=status,
        detail=outcome.detail,
        generation_id=generation_id,
        artifact_dir=artifact_dir,
        activatable=activatable,
        model_fp=model_fp,
        rules=rules,
        relations=relations,
        counts=counts,
    )
    write_result(artifact_dir, result)
    if request.activate:
        try:
            activate_generation(request.project_root, result)
        except ActivationRefusedError as error:
            return _fail(request, artifact_dir, str(error), generation_id)
    published, quality = publish_result(request, artifact_dir)
    if published is not None:
        result = build_result(
            request,
            status=result.status,
            detail=result.detail,
            generation_id=generation_id,
            artifact_dir=artifact_dir,
            activatable=result.activatable,
            model_fp=model_fp,
            rules=rules,
            relations=relations,
            counts=result.row_counts,
            published=published,
            quality=quality,
        )
        write_result(artifact_dir, result)
    _LOG.info(
        "transform %s status=%s generation=%s activatable=%s",
        request.command,
        result.status,
        generation_id,
        result.activatable,
    )
    return result
