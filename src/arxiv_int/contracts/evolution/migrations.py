"""Bridge evolution policy to the owned Alembic revision workflow.

Legacy dbmate-shaped SQL under `db/` is retained as adoption evidence only. Ordering,
approval markers, and dump-name substrings no longer stand in for migration checks;
the revision graph, checksums, and contract-to-history drift are authoritative.
"""

from pathlib import Path

from arxiv_int.contracts.migrations.adoption import inventory_legacy_sql
from arxiv_int.contracts.migrations.check import MigrationCheckReport, check_migrations


def migration_report(project_root: Path, contracts_root: Path) -> MigrationCheckReport:
    """Return the offline migration check report for one project tree."""
    return check_migrations(project_root, contracts_root)


def migration_policy_findings(project_root: Path, contracts_root: Path | None = None) -> list[str]:
    """Aggregate revision graph, checksum, and pending-revision findings."""
    root = contracts_root or (project_root / "contracts")
    return list(check_migrations(project_root, root).findings)


def legacy_evidence_findings(project_root: Path) -> list[str]:
    """Require the retained legacy SQL evidence to remain readable for adoption."""
    inventory = inventory_legacy_sql(project_root)
    if not inventory.present:
        return ["legacy migration evidence is missing; adoption cannot be reviewed"]
    return []
