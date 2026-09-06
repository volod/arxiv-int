"""Alembic configuration and separated generate/check/status/apply wrappers."""

import io
import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData

from arxiv_int.contracts.migrations.errors import MigrationRunnerUnavailableError
from arxiv_int.contracts.migrations.paths import script_location, versions_dir
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root

_LOG = logging.getLogger(__name__)
# Alembic logs one INFO line per plugin at import time; operator output stays readable.
logging.getLogger("alembic.runtime.plugins").setLevel(logging.WARNING)

DATABASE_URL_VARIABLE = "ARXIV_INT_MIGRATION_DATABASE_URL"
OFFLINE_URL = "postgresql+psycopg://offline/offline"
CONTRACTS_ROOT_VARIABLE = "ARXIV_INT_CONTRACTS_ROOT"
STATUS_NOT_RUN = "not-run"
STATUS_OK = "ok"
STATUS_FAILED = "failed"
_CREDENTIALS = re.compile(r"//[^/@\s]*:[^/@\s]*@")


@dataclass(frozen=True)
class RunnerOutcome:
    """Result of one live migration wrapper call."""

    status: str
    detail: str

    @property
    def ok(self) -> bool:
        """Return whether the wrapper completed successfully."""
        return self.status == STATUS_OK


def redact_url(url: str) -> str:
    """Remove credentials before a database URL reaches a log or report."""
    return _CREDENTIALS.sub("//<redacted>@", url)


def target_metadata() -> MetaData:
    """Return contract-derived metadata for the Alembic environment."""
    root = os.environ.get(CONTRACTS_ROOT_VARIABLE)
    if not root:
        raise MigrationRunnerUnavailableError(
            f"{CONTRACTS_ROOT_VARIABLE} must name the contracts root for Alembic comparison"
        )
    return load_schema_model_from_root(Path(root)).metadata


def owned_object_filter(metadata: MetaData) -> Callable[..., bool]:
    """Restrict autogeneration to owned schemas and tables."""
    owned = set(metadata.tables)
    schemas = {table.schema for table in metadata.tables.values() if table.schema}

    def include_object(
        object_: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
    ) -> bool:
        schema = getattr(object_, "schema", None)
        if type_ == "table":
            if schema not in schemas:
                return False
            return f"{schema}.{name}" in owned
        return True

    return include_object


def resolve_database_url(explicit: str | None = None) -> str | None:
    """Resolve the explicitly selected migration database URL, if any."""
    return explicit or os.environ.get(DATABASE_URL_VARIABLE) or None


def alembic_config(project_root: Path, contracts_root: Path, url: str) -> Any:
    """Build an Alembic Config for the owned script directory."""
    try:
        from alembic.config import Config
    except ImportError as error:  # pragma: no cover - exercised through require_runner
        raise MigrationRunnerUnavailableError("alembic is not installed") from error
    os.environ[CONTRACTS_ROOT_VARIABLE] = str(contracts_root)
    config = Config()
    config.set_main_option("script_location", str(script_location(project_root)))
    config.set_main_option("path_separator", "os")
    config.set_main_option("version_locations", str(versions_dir(project_root)))
    config.set_main_option("sqlalchemy.url", url)
    return config


def runner_available() -> bool:
    """Return whether Alembic is importable in this environment."""
    try:
        import alembic  # noqa: F401
    except ImportError:
        return False
    return True


def _command(
    project_root: Path,
    contracts_root: Path,
    url: str | None,
    action: str,
    apply_: Callable[[Any], None],
) -> RunnerOutcome:
    if not runner_available():
        return RunnerOutcome(STATUS_NOT_RUN, "alembic is not installed; install the store extra")
    resolved = resolve_database_url(url)
    if not resolved:
        return RunnerOutcome(
            STATUS_NOT_RUN,
            f"no migration database selected; set {DATABASE_URL_VARIABLE}",
        )
    config = alembic_config(project_root, contracts_root, resolved)
    safe = redact_url(resolved)
    try:
        apply_(config)
    except Exception as error:  # reported as a failed outcome, never a silent pass
        return RunnerOutcome(STATUS_FAILED, f"{action} failed against {safe}: {error}")
    _LOG.info("migration %s completed against %s", action, safe)
    return RunnerOutcome(STATUS_OK, f"{action} completed against {safe}")


def offline_sql(
    project_root: Path,
    contracts_root: Path,
    *,
    revision: str = "base:head",
    url: str = OFFLINE_URL,
) -> str:
    """Emit review SQL for a revision range without connecting to a database."""
    from alembic import command

    buffer = io.StringIO()
    config = alembic_config(project_root, contracts_root, url)
    config.output_buffer = buffer
    command.upgrade(config, revision, sql=True)
    return buffer.getvalue()


def upgrade(
    project_root: Path, contracts_root: Path, *, url: str | None = None, revision: str = "head"
) -> RunnerOutcome:
    """Upgrade an explicitly selected database to the given revision."""
    from alembic import command

    return _command(
        project_root,
        contracts_root,
        url,
        f"upgrade to {revision}",
        lambda config: command.upgrade(config, revision),
    )


def downgrade(
    project_root: Path, contracts_root: Path, *, url: str | None = None, revision: str = "-1"
) -> RunnerOutcome:
    """Downgrade an explicitly selected database; irreversible revisions refuse."""
    from alembic import command

    return _command(
        project_root,
        contracts_root,
        url,
        f"downgrade to {revision}",
        lambda config: command.downgrade(config, revision),
    )


def current_revision(
    project_root: Path, contracts_root: Path, *, url: str | None = None
) -> RunnerOutcome:
    """Report the applied revision of an explicitly selected database."""
    from alembic import command

    return _command(
        project_root,
        contracts_root,
        url,
        "status",
        lambda config: command.current(config, verbose=False),
    )
