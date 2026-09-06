"""Validate generated PostgreSQL SQL against a disposable parser or database."""

import logging
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

_LOG = logging.getLogger(__name__)


def _active_sql(text: str) -> str:
    lines = [
        line for line in text.splitlines() if line.strip() and not line.strip().startswith("--")
    ]
    return "\n".join(lines)


def parse_sql_statements(sql_texts: Sequence[str]) -> list[str]:
    """Parse SQL with sqlglot when available; return finding strings."""
    try:
        import sqlglot
        from sqlglot.errors import ParseError
    except ImportError as error:
        raise RuntimeError("sqlglot is required to parse generated SQL") from error
    findings: list[str] = []
    for index, text in enumerate(sql_texts):
        body = _active_sql(text)
        if not body:
            continue
        try:
            sqlglot.parse(body, read="postgres")
        except ParseError as error:
            findings.append(f"sql[{index}]: parse failed: {error}")
    return findings


def apply_baseline_on_disposable_postgres(baseline_sql: str) -> list[str]:
    """Apply the ordered baseline DDL on a disposable Docker Postgres when possible."""
    if shutil.which("docker") is None:
        return ["docker unavailable; disposable postgres apply was not run"]
    body = _active_sql(baseline_sql)
    if "CREATE TABLE" not in body.upper():
        return ["no CREATE TABLE statements found for disposable postgres apply"]
    combined = body + "\n"
    container = f"arxiv-int-sql-{os.getpid()}-{int(time.time() * 1000) % 100000}"
    with tempfile.TemporaryDirectory(prefix="arxiv-int-pg-sql-") as tmp:
        sql_file = Path(tmp) / "schema.sql"
        sql_file.write_text(combined, encoding="utf-8")
        run = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                container,
                "-e",
                "POSTGRES_HOST_AUTH_METHOD=trust",
                "-e",
                "POSTGRES_USER=postgres",
                "postgres:16-alpine",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if run.returncode != 0:
            return [f"failed to start disposable postgres: {run.stderr.strip()}"]
        try:
            for _ in range(60):
                ready = subprocess.run(
                    ["docker", "exec", container, "pg_isready", "-U", "postgres"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if ready.returncode == 0:
                    break
                time.sleep(0.25)
            else:
                return ["disposable postgres did not become ready"]
            time.sleep(0.5)
            subprocess.run(
                ["docker", "cp", str(sql_file), f"{container}:/tmp/schema.sql"],
                check=True,
                capture_output=True,
                text=True,
            )
            detail = "apply failed"
            for _ in range(8):
                apply = subprocess.run(
                    [
                        "docker",
                        "exec",
                        container,
                        "psql",
                        "-U",
                        "postgres",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-f",
                        "/tmp/schema.sql",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if apply.returncode == 0:
                    _LOG.info("disposable postgres accepted the generated baseline DDL")
                    return []
                detail = (apply.stderr or apply.stdout or "apply failed").strip()
                if "starting up" in detail.lower() or "shutting down" in detail.lower():
                    time.sleep(0.5)
                    continue
                break
            return [f"disposable postgres rejected SQL: {detail}"]
        finally:
            subprocess.run(
                ["docker", "rm", "-f", container],
                check=False,
                capture_output=True,
                text=True,
            )
