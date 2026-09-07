"""Environment-only dbt credentials parsed from a selected database URL."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from arxiv_int.contracts.migrations.runner import redact_url
from arxiv_int.transformations.model import DEFAULT_THREADS, MAX_THREADS

DATABASE_URL_VARIABLE = "ARXIV_INT_TRANSFORM_DATABASE_URL"
MIGRATION_URL_VARIABLE = "ARXIV_INT_MIGRATION_DATABASE_URL"
ENV_HOST = "ARXIV_INT_DBT_HOST"
ENV_USER = "ARXIV_INT_DBT_USER"
ENV_PASSWORD = "ARXIV_INT_DBT_PASSWORD"
ENV_PORT = "ARXIV_INT_DBT_PORT"
ENV_DBNAME = "ARXIV_INT_DBT_DBNAME"
ENV_THREADS = "ARXIV_INT_DBT_THREADS"
_GENERATION = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


@dataclass(frozen=True, slots=True)
class DbtCredentials:
    """Parsed PostgreSQL identity used only as process environment values."""

    host: str
    user: str
    password: str
    port: str
    dbname: str
    threads: int

    def env_mapping(self) -> dict[str, str]:
        """Return env_var names expected by the committed profiles.yml."""
        return {
            ENV_HOST: self.host,
            ENV_USER: self.user,
            ENV_PASSWORD: self.password,
            ENV_PORT: self.port,
            ENV_DBNAME: self.dbname,
            ENV_THREADS: str(self.threads),
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
            "DBT_USE_COLORS": "false",
        }


def bound_threads(value: int) -> int:
    """Clamp dbt threads into the documented bound."""
    if value < 1:
        return 1
    return min(value, MAX_THREADS)


def sanitize_generation_id(run_id: str) -> str:
    """Return a PostgreSQL-safe generation suffix derived from the run id."""
    lowered = re.sub(r"[^a-z0-9]+", "_", run_id.strip().lower()).strip("_")
    if not lowered:
        raise ValueError("run id must contain a letter or digit")
    if lowered[0].isdigit():
        lowered = f"g_{lowered}"
    candidate = lowered[:32]
    if not _GENERATION.match(candidate):
        raise ValueError(f"run id produced an invalid generation id: {run_id!r}")
    return candidate


def resolve_database_url(explicit: str | None = None) -> str | None:
    """Resolve the transform database URL from the argument or environment."""
    if explicit and explicit.strip():
        return explicit.strip()
    for name in (DATABASE_URL_VARIABLE, MIGRATION_URL_VARIABLE):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def parse_credentials(url: str, *, threads: int = DEFAULT_THREADS) -> DbtCredentials:
    """Parse a SQLAlchemy or libpq URL into dbt profile fields."""
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if not host:
        raise ValueError(f"database URL is missing a host: {redact_url(url)}")
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    dbname = unquote(parsed.path.lstrip("/").split("/", 1)[0])
    if not user or not dbname:
        raise ValueError(f"database URL is missing a user or database: {redact_url(url)}")
    port = str(parsed.port or 5432)
    return DbtCredentials(
        host=host,
        user=user,
        password=password,
        port=port,
        dbname=dbname,
        threads=bound_threads(threads),
    )


def apply_credential_env(credentials: DbtCredentials) -> Mapping[str, str | None]:
    """Install credential env vars and return prior values for restoration."""
    mapping = credentials.env_mapping()
    prior = {key: os.environ.get(key) for key in mapping}
    os.environ.update(mapping)
    return prior


def restore_credential_env(prior: Mapping[str, str | None]) -> None:
    """Restore credential env vars after a dbt invocation."""
    for key, value in prior.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
