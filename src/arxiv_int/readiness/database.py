"""Read-only database extension and migration readiness checks."""

from arxiv_int.readiness.probes import Probe
from arxiv_int.readiness.report import PreflightReport
from arxiv_int.runtime.compose import compose_base_command, compose_environment
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.service_plan import plan_services

_DEFAULT_DB_ROLE = "arxiv_int"
_EXTENSION_QUERY = (
    "SELECT name || '=' || default_version || '/' || COALESCE(installed_version, '-') "
    "FROM pg_available_extensions WHERE name IN ('age','pg_search','vector') ORDER BY name"
)


def check_database(
    report: PreflightReport,
    config: RuntimeConfig,
    profiles: tuple[str, ...],
    probe: Probe,
    timeout: float,
    *,
    database_healthy: bool,
) -> None:
    """Inspect installed extension versions and current migration applicability."""
    plan = plan_services(profiles, project_root=config.project_root)
    if not plan.database:
        return
    migrations = config.project_root / "db" / "migrations"
    if migrations.is_dir():
        report.add(
            "database.migrations",
            "degraded",
            "migration files exist but no shipped migration registry declares live state",
            action="implement the registered contract-governance migration task",
        )
    else:
        report.add("database.migrations", "ready", "no database migrations are shipped yet")
    if plan.graph and not plan.age_enabled:
        report.add(
            "database.extensions",
            "degraded",
            "graph profile selected but AGE compatibility gate is closed",
            action="run make postgres-image-probe WRITE_GATE=1 after a successful AGE suite",
        )
        return
    if not database_healthy:
        report.add(
            "database.extensions",
            "degraded",
            "extension versions unavailable while the database is not healthy",
            action="make services-up",
        )
        return
    values = dict(config.values)
    user = values.get("POSTGRES_USER", "").strip() or _DEFAULT_DB_ROLE
    database = values.get("POSTGRES_DB", "").strip() or _DEFAULT_DB_ROLE
    password = values.get("POSTGRES_PASSWORD", "")
    base = compose_base_command(config, plan.profiles)
    # The database container runs as RUNTIME_UID, so peer auth as that OS id fails.
    # Pass the configured role explicitly and inject the password only into the exec env.
    command = (
        *base,
        "exec",
        "-T",
        "-e",
        "PGPASSWORD",
        "database",
        "psql",
        "-U",
        user,
        "-d",
        database,
        "-v",
        "ON_ERROR_STOP=1",
        "-Atqc",
        _EXTENSION_QUERY,
    )
    result = probe.run(
        command,
        cwd=config.project_root,
        environment=dict(compose_environment(config), PGPASSWORD=password),
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = "extension version query failed"
        report.add(
            "database.extensions",
            "degraded",
            detail,
            action="make services-up && make readiness",
        )
        return
    _check_extensions(report, result.stdout, plan.extensions, password)


def _check_extensions(
    report: PreflightReport, output: str, required: frozenset[str], password: str
) -> None:
    versions = _extension_versions(output)
    missing = sorted(required - versions.keys())
    uninstalled = sorted(name for name in required & versions.keys() if not versions[name][1])
    if missing or uninstalled:
        detail = "required extension(s) unavailable: " + ", ".join(missing) if missing else ""
        if uninstalled:
            detail += (
                ("; " if detail else "")
                + "required extension(s) not installed: "
                + ", ".join(uninstalled)
            )
        report.add(
            "database.extensions",
            "blocked",
            detail,
            action="use the project-pinned database image and registered extension setup, then rerun make readiness",
        )
        return
    rendered = ", ".join(
        f"{name}={available}/{installed or '-'}"
        for name, (available, installed) in sorted(versions.items())
    )
    if password:
        rendered = rendered.replace(password, "[redacted]")
    report.add("database.extensions", "ready", f"available/installed versions: {rendered}")


def _extension_versions(output: str) -> dict[str, tuple[str, str | None]]:
    """Keep available and installed identities distinct; malformed rows are not evidence."""
    versions: dict[str, tuple[str, str | None]] = {}
    for line in output.splitlines():
        name, equals, identity = line.partition("=")
        available, slash, installed = identity.partition("/")
        if equals and slash and available and name in {"age", "pg_search", "vector"}:
            versions[name] = (available, installed if installed and installed != "-" else None)
    return versions
