"""Invoke Python dbt Core without embedding SQL or credentials in artifacts."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.features import MissingFeatureError, require_module
from arxiv_int.transformations.credentials import (
    DbtCredentials,
    apply_credential_env,
    restore_credential_env,
)


@dataclass(frozen=True, slots=True)
class InvokeOutcome:
    """Result of one dbtRunner invocation."""

    success: bool
    detail: str
    exception: str | None = None


def dbt_cli_args(
    command: str,
    *,
    project_dir: Path,
    profiles: Path,
    target_dir: Path,
    log_dir: Path,
    select: Sequence[str],
    vars_payload: str,
    full_refresh: bool,
    threads: int,
) -> list[str]:
    """Build a dbt Core CLI argument vector for one command."""
    args = [
        command,
        "--project-dir",
        str(project_dir),
        "--profiles-dir",
        str(profiles),
        "--target-path",
        str(target_dir),
        "--log-path",
        str(log_dir),
        "--no-use-colors",
        "--threads",
        str(threads),
        "--vars",
        vars_payload,
    ]
    if command in {"compile", "build", "test"} and select:
        args.append("--select")
        args.extend(select)
    if command in {"compile", "build"} and full_refresh:
        args.append("--full-refresh")
    return args


def invoke_dbt(args: Sequence[str], credentials: DbtCredentials | None) -> InvokeOutcome:
    """Run dbt Core through dbtRunner with environment-only credentials."""
    try:
        module = require_module("dbt.cli.main")
        require_module("dbt.adapters.postgres")
    except MissingFeatureError as error:
        return InvokeOutcome(False, str(error), exception=type(error).__name__)
    prior: dict[str, str | None] = {}
    if credentials is not None:
        prior = dict(apply_credential_env(credentials))
    try:
        runner = module.dbtRunner()
        result = runner.invoke(list(args))
    except Exception as error:
        return InvokeOutcome(False, "dbt invocation failed", exception=type(error).__name__)
    finally:
        if prior:
            restore_credential_env(prior)
    exception = result.exception
    detail = _result_detail(result)
    if exception is not None:
        return InvokeOutcome(False, detail or str(exception), exception=type(exception).__name__)
    if not result.success:
        return InvokeOutcome(False, detail or "dbt command failed")
    return InvokeOutcome(True, detail or "dbt command succeeded")


def _result_detail(result: object) -> str:
    exception = getattr(result, "exception", None)
    if exception is not None:
        return f"dbt command failed ({type(exception).__name__})"
    return "dbt command succeeded" if getattr(result, "success", False) else "dbt command failed"
