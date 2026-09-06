"""Operator-facing migration actions kept separate from argument parsing."""

import logging
from pathlib import Path

from arxiv_int.contracts.migrations.adoption import adoption_findings, inventory_legacy_sql
from arxiv_int.contracts.migrations.authoring import generate_revision
from arxiv_int.contracts.migrations.check import check_migrations
from arxiv_int.contracts.migrations.paths import migration_artifact_dir
from arxiv_int.contracts.migrations.runner import (
    STATUS_NOT_RUN,
    current_revision,
    downgrade,
    offline_sql,
    upgrade,
)
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root

_LOG = logging.getLogger(__name__)


def run_revision(project_root: Path, contracts_root: Path, message: str) -> int:
    """Generate a candidate revision, or report that none is needed."""
    candidate = generate_revision(project_root, contracts_root, message=message)
    if not candidate.created:
        _LOG.info(
            "contract metadata matches revision %s; no revision generated", candidate.revision
        )
        return 0
    _LOG.info(
        "generated revision %s with %d operation(s): %s",
        candidate.revision,
        len(candidate.operations),
        candidate.path.name,
    )
    _LOG.info("review the revision and its notes before applying it to any database")
    return 0


def run_check(project_root: Path, contracts_root: Path) -> int:
    """Report offline migration status without touching a database."""
    report = check_migrations(project_root, contracts_root)
    for finding in report.findings:
        _LOG.error("%s", finding)
    if not report.ok:
        return 1
    _LOG.info(
        "migration check passed at head %s; live evidence: %s",
        report.head or "base",
        report.live_evidence,
    )
    return 0


def run_offline_sql(project_root: Path, contracts_root: Path, revision: str) -> int:
    """Print review SQL for a revision range without connecting to a database."""
    span = revision if ":" in revision else f"base:{revision}"
    destination = migration_artifact_dir(project_root) / "upgrade.sql"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        offline_sql(project_root, contracts_root, revision=span), encoding="utf-8"
    )
    _LOG.info("wrote offline review SQL for %s to %s; no database was contacted", span, destination)
    return 0


def run_apply(project_root: Path, contracts_root: Path, action: str, revision: str) -> int:
    """Run one live wrapper; a missing runner or database is not-run, never success."""
    if action == "status":
        outcome = current_revision(project_root, contracts_root)
    elif action == "upgrade":
        outcome = upgrade(project_root, contracts_root, revision=revision)
    else:
        outcome = downgrade(project_root, contracts_root, revision=revision)
    if outcome.status == STATUS_NOT_RUN:
        _LOG.warning("%s not-run: %s", action, outcome.detail)
        return 2
    if not outcome.ok:
        _LOG.error("%s", outcome.detail)
        return 1
    _LOG.info("%s", outcome.detail)
    return 0


def run_adopt(project_root: Path, contracts_root: Path) -> int:
    """Report why an existing database may or may not be stamped at a baseline."""
    model = load_schema_model_from_root(contracts_root)
    inventory = inventory_legacy_sql(project_root)
    _LOG.info(
        "legacy evidence: %d SQL file(s), %d declared table(s), schema export %s",
        len(inventory.files),
        len(inventory.declared_tables),
        "present" if inventory.schema_export else "absent",
    )
    findings = adoption_findings(project_root, model)
    for finding in findings:
        _LOG.error("%s", finding)
    _LOG.warning("adoption refused; stamping requires proved live catalog equivalence")
    return 2
