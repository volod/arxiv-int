"""dbmate-style ordered SQL migrations and schema dump checks."""

import os
import re
import shutil
import subprocess
from pathlib import Path

MIGRATION_NAME = re.compile(r"^(?P<ts>\d{14})_(?P<slug>[a-z0-9_]+)\.sql$")
DESTRUCTIVE = re.compile(
    r"\b(DROP\s+TABLE|TRUNCATE\s+TABLE|ALTER\s+TABLE\s+\S+\s+DROP\s+COLUMN)\b",
    re.IGNORECASE,
)
APPROVAL_MARKER = "-- arxiv-int: destructive-approved"


def migrations_dir(project_root: Path) -> Path:
    return project_root / "db" / "migrations"


def schema_sql_path(project_root: Path) -> Path:
    return project_root / "db" / "schema.sql"


def list_migration_files(directory: Path) -> list[Path]:
    """Return migration files sorted by filename (dbmate order)."""
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.sql") if path.is_file())


def migration_order_findings(directory: Path) -> list[str]:
    """Fail closed on malformed names, duplicate timestamps, or unsorted order."""
    findings: list[str] = []
    seen_ts: dict[str, str] = {}
    files = list_migration_files(directory)
    names = [path.name for path in files]
    if names != sorted(names):
        findings.append("migration filenames are not sorted in dbmate order")
    previous = ""
    for path in files:
        matched = MIGRATION_NAME.match(path.name)
        if matched is None:
            findings.append(f"migration filename is not dbmate-shaped: {path.name}")
            continue
        stamp = matched.group("ts")
        if stamp in seen_ts:
            findings.append(
                f"duplicate migration timestamp {stamp}: {seen_ts[stamp]} and {path.name}"
            )
        else:
            seen_ts[stamp] = path.name
        if stamp < previous:
            findings.append(f"out-of-order migration timestamp: {path.name}")
        previous = stamp
    return findings


def destructive_migration_findings(directory: Path) -> list[str]:
    """Refuse destructive SQL unless an explicit approval marker is present."""
    findings: list[str] = []
    for path in list_migration_files(directory):
        text = path.read_text(encoding="utf-8")
        if DESTRUCTIVE.search(text) and APPROVAL_MARKER not in text:
            findings.append(
                f"destructive migration requires '{APPROVAL_MARKER}' approval: {path.name}"
            )
    return findings


def schema_dump_findings(project_root: Path) -> list[str]:
    """Require db/schema.sql and ensure it mentions every migrated CREATE TABLE."""
    schema_path = schema_sql_path(project_root)
    if not schema_path.is_file():
        return ["db/schema.sql is missing; dump migrations before accepting evolution"]
    schema_text = schema_path.read_text(encoding="utf-8")
    findings: list[str] = []
    for path in list_migration_files(migrations_dir(project_root)):
        for match in re.finditer(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_.]+)",
            path.read_text(encoding="utf-8"),
            re.IGNORECASE,
        ):
            table = match.group(1).split(".")[-1]
            if table.lower() not in schema_text.lower():
                findings.append(
                    f"db/schema.sql drifts from migration {path.name}: missing table {table}"
                )
    return findings


def dbmate_command() -> list[str] | None:
    """Return argv for dbmate when installed on PATH."""
    direct = shutil.which("dbmate")
    return [direct] if direct else None


def dbmate_status_findings(project_root: Path, database_url: str | None = None) -> list[str]:
    """Optionally invoke dbmate status when the binary and DATABASE_URL are available."""
    command = dbmate_command()
    if command is None:
        return []
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        return []
    completed = subprocess.run(
        [*command, "--migrations-dir", str(migrations_dir(project_root)), "status"],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "DATABASE_URL": url},
        cwd=project_root,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "dbmate status failed").strip()
        return [f"dbmate status failed: {detail}"]
    return []


def migration_policy_findings(project_root: Path) -> list[str]:
    """Aggregate migration naming, approval, dump, and optional dbmate checks."""
    directory = migrations_dir(project_root)
    if not directory.is_dir():
        return ["db/migrations directory is missing"]
    findings = migration_order_findings(directory)
    findings.extend(destructive_migration_findings(directory))
    findings.extend(schema_dump_findings(project_root))
    findings.extend(dbmate_status_findings(project_root))
    return findings
