"""Bridge evolution policy to the owned Alembic revision workflow.

The revision graph, checksums, and contract-to-history drift are authoritative.
Ordering, approval markers, and dump-name substrings do not stand in for
migration checks.
"""

from pathlib import Path

from arxiv_int.contracts.migrations.check import MigrationCheckReport, check_migrations


def migration_report(project_root: Path, contracts_root: Path) -> MigrationCheckReport:
    """Return the offline migration check report for one project tree."""
    return check_migrations(project_root, contracts_root)


def migration_policy_findings(project_root: Path, contracts_root: Path | None = None) -> list[str]:
    """Aggregate revision graph, checksum, and pending-revision findings."""
    root = contracts_root or (project_root / "contracts")
    return list(check_migrations(project_root, root).findings)
