"""Read-only database extension and migration readiness checks."""

from arxiv_int.readiness.probes import Probe
from arxiv_int.readiness.report import PreflightReport
from arxiv_int.runtime.compose import compose_command, compose_environment
from arxiv_int.runtime.config_model import RuntimeConfig

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
    base = compose_command(config, "status", profiles)[:-2]
    # The database container runs as RUNTIME_UID, so peer auth as that OS id fails.
    # Pass the configured role explicitly and inject the password only into the exec env.
    command = (
        *base,
        "exec",
        "-T",
        "-e",
        f"PGPASSWORD={password}",
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
        environment=compose_environment(config),
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = "extension version query failed"
        stderr = result.stderr.strip()
        if stderr and password not in stderr:
            detail = f"{detail}: {stderr.splitlines()[-1]}"
        report.add(
            "database.extensions",
            "degraded",
            detail,
            action="make services-up && make readiness",
        )
        return
    versions = {
        line.partition("=")[0]: line.partition("=")[2]
        for line in result.stdout.splitlines()
        if "=" in line
    }
    required = {"pg_search", "vector"}
    if "graph" in profiles:
        required.add("age")
    missing = sorted(required - versions.keys())
    if missing:
        report.add(
            "database.extensions",
            "blocked",
            "required extension(s) unavailable: " + ", ".join(missing),
            action="use the project-pinned database image, then rerun make readiness",
        )
        return
    rendered = ", ".join(f"{name}={versions[name]}" for name in sorted(versions))
    report.add("database.extensions", "ready", f"available/installed versions: {rendered}")
