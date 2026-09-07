"""Bind schema apply/inspect to the configured service database only."""

from urllib.parse import quote, unquote, urlsplit

from arxiv_int.contracts.migrations.runner import DATABASE_URL_VARIABLE, redact_url
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.setup.model import RETRY_COMMAND, PhaseResult, reused_or_ready
from arxiv_int.runtime.setup.state import fingerprint_for
from arxiv_int.stores.postgres.apply import apply_revisions, inspect_and_compare
from arxiv_int.stores.postgres.constants import CANONICAL_SCHEMAS, HEAD_REVISION

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class SchemaTargetError(ValueError):
    """The selected migration target is not the configured service database."""


def service_database_url(config: RuntimeConfig) -> str:
    """Derive the service URL privately from shared PostgreSQL settings."""
    values = dict(config.values)
    user = quote(values.get("POSTGRES_USER", "").strip() or "arxiv_int", safe="")
    password = quote(values.get("POSTGRES_PASSWORD", ""), safe="")
    port = values.get("POSTGRES_PORT", "").strip() or "5432"
    database = quote(values.get("POSTGRES_DB", "").strip() or "arxiv_int", safe="")
    return f"postgresql+psycopg://{user}:{password}@127.0.0.1:{port}/{database}"


def _identity(url: str) -> tuple[str, str, str, str]:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host == "localhost":
        host = "127.0.0.1"
    port = str(parsed.port or 5432)
    database = unquote(parsed.path.lstrip("/"))
    user = unquote(parsed.username or "")
    return host, port, database, user


def bound_service_url(config: RuntimeConfig, override: str | None) -> str:
    """Return the service URL, refusing a conflicting explicit migration target."""
    service = service_database_url(config)
    if not override:
        return service
    if _identity(override) != _identity(service):
        raise SchemaTargetError(
            "ARXIV_INT_MIGRATION_DATABASE_URL does not match the configured service "
            f"({redact_url(override)}); unset it or point it at the selected database"
        )
    service_host, _, _, _ = _identity(service)
    if service_host not in LOOPBACK_HOSTS:
        raise SchemaTargetError("setup schema requires a loopback service database")
    return service


def run_schema_phase(
    config: RuntimeConfig,
    *,
    override: str | None,
    run_id: str,
    verified: dict[str, str] | None = None,
) -> PhaseResult:
    """Apply eligible revisions to the configured service; never use a disposable store."""
    try:
        url = bound_service_url(config, override)
    except SchemaTargetError as error:
        return PhaseResult(
            "schema",
            "blocked",
            str(error),
            action=f"unset {DATABASE_URL_VARIABLE} or match POSTGRES_* in .env",
        )
    try:
        findings, payload, revision = inspect_and_compare(
            config.project_root, url, at_applied_revision=True
        )
    except Exception as error:
        return PhaseResult(
            "schema",
            "blocked",
            f"cannot inspect the configured service ({error.__class__.__name__})",
            action="make setup-wait, then " + RETRY_COMMAND,
        )
    schemas = {str(item) for item in payload.get("schemas") or []}
    canonical_present = bool(schemas.intersection(CANONICAL_SCHEMAS))
    digest = fingerprint_for(revision or "", str(config.pgdata_dir))
    if revision and findings:
        return PhaseResult(
            "schema",
            "blocked",
            "configured service catalog drifted from owned revisions",
            action="use the reviewed db adopt workflow; setup will not auto-adopt",
        )
    if not revision and canonical_present:
        return PhaseResult(
            "schema",
            "blocked",
            "nonempty unversioned or unknown catalog on the configured service",
            action="use the reviewed db adopt workflow; setup will not auto-adopt",
        )
    if revision == HEAD_REVISION and not findings:
        return PhaseResult(
            "schema",
            reused_or_ready(verified, "schema", digest),
            f"configured service schema is at revision {revision}",
            fingerprint=digest,
        )
    report = apply_revisions(config.project_root, url=url, revision="head", run_id=run_id)
    if not report.ok:
        detail = report.findings[0] if report.findings else report.outcome.detail
        return PhaseResult(
            "schema",
            "blocked",
            detail,
            action="inspect migration evidence, then " + RETRY_COMMAND,
        )
    applied = report.revision or "head"
    return PhaseResult(
        "schema",
        "ready",
        f"applied owned revisions at {applied} on the configured service",
        fingerprint=fingerprint_for(applied, str(config.pgdata_dir)),
    )
