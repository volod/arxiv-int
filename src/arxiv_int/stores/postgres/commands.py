"""Operator commands for applying, inspecting, and adopting the canonical schema."""

import logging
from pathlib import Path

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.migrations.commands import run_adopt as run_offline_adopt
from arxiv_int.contracts.migrations.runner import STATUS_NOT_RUN, resolve_database_url
from arxiv_int.stores.postgres.adopt import adopt_database
from arxiv_int.stores.postgres.apply import (
    apply_on_disposable,
    apply_revisions,
    inspect_and_compare,
)
from arxiv_int.stores.postgres.evidence import write_evidence

_LOG = logging.getLogger(__name__)


def _not_run_exit(detail: str) -> int:
    _LOG.warning("schema apply not-run: %s", detail)
    return 2


def run_apply_schema(
    project_root: Path,
    *,
    url: str | None = None,
    pgdata_dir: Path | None = None,
    run_id: str,
    revision: str = "head",
) -> int:
    """Apply owned revisions to a selected URL or a disposable pinned store."""
    selected = resolve_database_url(url)
    if selected:
        report = apply_revisions(project_root, url=selected, revision=revision, run_id=run_id)
    elif pgdata_dir is not None:
        report = apply_on_disposable(project_root, pgdata_dir, run_id=run_id, revision=revision)
    else:
        return _not_run_exit("no migration database selected and no disposable PGDATA_DIR")
    if report.outcome.status == STATUS_NOT_RUN:
        return _not_run_exit(report.outcome.detail)
    for finding in report.findings:
        _LOG.error("%s", finding)
    if report.evidence_path is not None:
        _LOG.info("wrote live schema evidence to %s", report.evidence_path)
    if not report.ok:
        return 1
    _LOG.info("canonical schema applied at revision %s", report.revision)
    return 0


def run_inspect_schema(project_root: Path, *, url: str | None = None, run_id: str) -> int:
    """Inspect a live catalog without applying revisions."""
    selected = resolve_database_url(url)
    if not selected:
        return _not_run_exit("no migration database selected")
    findings, payload, revision = inspect_and_compare(project_root, selected)
    payload["url"] = selected
    evidence = write_evidence(project_root, payload, run_id=run_id)
    for finding in findings:
        _LOG.error("%s", finding)
    _LOG.info("inspected revision %s; evidence %s", revision, evidence)
    return 0 if not findings else 1


def run_adopt_schema(project_root: Path, *, url: str | None = None, run_id: str) -> int:
    """Adopt a live database or report not-run when no URL is selected."""
    if resolve_database_url(url) is None:
        return run_offline_adopt(project_root, contracts_root_for(project_root))
    report = adopt_database(project_root, url=url, run_id=run_id)
    for finding in report.findings:
        _LOG.error("%s", finding)
    if report.evidence_path is not None:
        _LOG.info("wrote adoption evidence to %s", report.evidence_path)
    if report.outcome.status == STATUS_NOT_RUN:
        return 2
    if not report.ok:
        return 1
    _LOG.info(
        "stamped revision %s; relocated %d table(s)",
        report.stamped_revision,
        len(report.relocated),
    )
    return 0
