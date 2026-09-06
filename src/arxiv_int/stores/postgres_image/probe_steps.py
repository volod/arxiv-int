"""Individual disposable PostgreSQL extension probe steps."""

import logging
import subprocess
import time

from arxiv_int.stores.postgres_image.pins import ImagePins, merge_shared_preload
from arxiv_int.stores.postgres_image.probe_model import ProbeReport
from arxiv_int.stores.postgres_image.probe_sql import (
    BM25_VECTOR_SQL,
    CYPHER_SQL,
    SQL_PROBES,
    TXN_SQL,
)

_LOG = logging.getLogger(__name__)

__all__ = [
    "BM25_VECTOR_SQL",
    "CYPHER_SQL",
    "TXN_SQL",
    "check_licenses",
    "probe_dump_restore",
    "probe_named",
    "probe_restart",
    "probe_versions",
    "wait_ready",
]


def check_licenses(project_root_notice: str, report: ProbeReport) -> None:
    required = ("AGPL-3.0", "Apache License", "PostgreSQL", "Apache AGE", "ParadeDB")
    missing = [name for name in required if name not in project_root_notice]
    report.add("licenses", not missing, "ok" if not missing else "missing: " + ", ".join(missing))


def wait_ready(container: str, user: str, database: str) -> bool:
    logs = ""
    for _ in range(120):
        logs_run = subprocess.run(
            ["docker", "logs", container], check=False, capture_output=True, text=True
        )
        logs = (logs_run.stdout or "") + (logs_run.stderr or "")
        initialized = (
            "arxiv-int AGE bootstrap completed" in logs
            or "ParadeDB bootstrap completed" in logs
            or "Skipping initialization" in logs
        )
        ready = subprocess.run(
            ["docker", "exec", container, "pg_isready", "-U", user, "-d", database],
            check=False,
            capture_output=True,
            text=True,
        )
        accepting = "database system is ready to accept connections" in logs
        if initialized and ready.returncode == 0 and accepting:
            if "shutting down" in logs[-800:] and "ready to accept connections" not in logs[-400:]:
                time.sleep(0.5)
                continue
            time.sleep(0.5)
            ready2 = subprocess.run(
                ["docker", "exec", container, "pg_isready", "-U", user, "-d", database],
                check=False,
                capture_output=True,
                text=True,
            )
            if ready2.returncode == 0:
                return True
        time.sleep(0.5)
    _LOG.error("readiness timed out; logs tail: %s", logs[-2000:])
    return False


def psql(
    container: str, user: str, database: str, password: str, sql: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={password}",
            "-i",
            container,
            "psql",
            "-U",
            user,
            "-d",
            database,
            "-v",
            "ON_ERROR_STOP=1",
            "-At",
        ],
        input=sql,
        check=False,
        capture_output=True,
        text=True,
    )


def probe_versions(
    container: str,
    user: str,
    database: str,
    password: str,
    pins: ImagePins,
    report: ProbeReport,
) -> None:
    result = psql(container, user, database, password, SQL_PROBES)
    if result.returncode != 0:
        report.add("versions", False, (result.stderr or result.stdout or "query failed").strip())
        return
    output = result.stdout
    preload = ""
    for line in output.splitlines():
        if "pg_search" in line and "pg_cron" in line:
            preload = line.strip()
            break
    expected_preload = merge_shared_preload("pg_search,pg_cron,pg_stat_statements", "age")
    if preload != expected_preload:
        report.add(
            "versions",
            False,
            f"shared_preload_libraries={preload!r} expected {expected_preload!r}",
        )
        return
    installed: dict[str, str] = {}
    for line in output.splitlines():
        name, sep, version = line.partition("=")
        if sep and "/" not in version and name in pins.expected_extensions():
            installed[name] = version
    expected = pins.expected_extensions()
    mismatches = [
        f"{name}: got {installed.get(name)!r} want {version!r}"
        for name, version in expected.items()
        if installed.get(name) != version
    ]
    report.add("versions", not mismatches, "ok" if not mismatches else "; ".join(mismatches))
    report.add("sql", True, "extension inventory query ok")


def probe_named(
    container: str,
    user: str,
    database: str,
    password: str,
    name: str,
    sql: str,
    report: ProbeReport,
) -> bool:
    result = psql(container, user, database, password, sql)
    ok = result.returncode == 0
    detail = "ok" if ok else (result.stderr or result.stdout or "failed").strip()
    report.add(name, ok, detail)
    return ok


def probe_restart(
    container: str,
    run_command: list[str],
    user: str,
    database: str,
    password: str,
    report: ProbeReport,
) -> None:
    subprocess.run(["docker", "rm", "-f", container], check=False, capture_output=True, text=True)
    started = subprocess.run(
        [*run_command[:-1], "-d", run_command[-1]], check=False, capture_output=True, text=True
    )
    if started.returncode != 0 or not wait_ready(container, user, database):
        report.add("restart", False, started.stderr.strip() or "restart failed")
        return
    result = psql(
        container,
        user,
        database,
        password,
        "SELECT extname FROM pg_extension WHERE extname IN ('age','pg_search','vector') ORDER BY 1;",
    )
    names = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    ok = result.returncode == 0 and names == {"age", "pg_search", "vector"}
    detail = "extensions survived restart" if ok else result.stderr.strip() or "missing"
    report.add("restart", ok, detail)


def probe_dump_restore(
    container: str, user: str, database: str, password: str, report: ProbeReport
) -> None:
    dump = subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={password}",
            container,
            "pg_dump",
            "-U",
            user,
            "-d",
            database,
            "--schema-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if dump.returncode != 0:
        report.add("dump_restore", False, dump.stderr.strip() or "pg_dump failed")
        return
    restore_db = "arxiv_int_restore_probe"
    create = psql(
        container,
        user,
        database,
        password,
        f"CREATE DATABASE {restore_db} TEMPLATE template0;",
    )
    if create.returncode != 0:
        report.add("dump_restore", False, create.stderr.strip() or "create restore db failed")
        return
    restore = subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={password}",
            "-i",
            container,
            "psql",
            "-U",
            user,
            "-d",
            restore_db,
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=dump.stdout,
        check=False,
        capture_output=True,
        text=True,
    )
    cleanup = psql(container, user, database, password, f"DROP DATABASE {restore_db};")
    ok = restore.returncode == 0 and cleanup.returncode == 0
    detail = (
        "schema dump/restore ok" if ok else (restore.stderr or restore.stdout or "restore failed")
    )
    report.add("dump_restore", ok, detail.strip())
