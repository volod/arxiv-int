"""Apply owned revisions on an explicitly selected or disposable database."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.migrations.runner import (
    STATUS_FAILED,
    STATUS_NOT_RUN,
    RunnerOutcome,
    current_revision,
    downgrade,
    upgrade,
)
from arxiv_int.contracts.sqlalchemy.catalog import compare_live_catalog
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.stores.postgres.disposable import disposable_store, image_present
from arxiv_int.stores.postgres.evidence import catalog_as_dict, write_evidence
from arxiv_int.stores.postgres.inspect_live import inspect_store, store_findings
from arxiv_int.stores.postgres_image.pins import load_image_pins


@dataclass(frozen=True, slots=True)
class SchemaApplyReport:
    """Outcome of one empty-to-head or targeted upgrade plus catalog inspection."""

    outcome: RunnerOutcome
    findings: tuple[str, ...]
    evidence_path: Path | None
    revision: str | None
    row_counts: dict[str, int]

    @property
    def ok(self) -> bool:
        """Return whether apply and live overlay checks succeeded."""
        return self.outcome.ok and not self.findings


def _engine(url: str) -> Any:
    return create_engine(url, pool_pre_ping=True)


def row_counts(url: str, qualified_names: tuple[str, ...]) -> dict[str, int]:
    """Return COUNT(*) for each owned table, omitting relations that do not exist."""
    counts: dict[str, int] = {}
    engine = _engine(url)
    try:
        with engine.connect() as connection:
            for name in qualified_names:
                schema, _, table = name.partition(".")
                exists = connection.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_tables "
                        "WHERE schemaname = :schema AND tablename = :table)"
                    ),
                    {"schema": schema, "table": table},
                ).scalar()
                if not exists:
                    continue
                counts[name] = int(
                    connection.execute(text(f"SELECT count(*) FROM {schema}.{table}")).scalar() or 0
                )
    finally:
        engine.dispose()
    return counts


def inspect_and_compare(
    project_root: Path, url: str
) -> tuple[list[str], dict[str, Any], str | None]:
    """Compare contract metadata and inspect store overlay objects."""
    contracts_root = contracts_root_for(project_root)
    model = load_schema_model_from_root(contracts_root)
    engine = _engine(url)
    try:
        with engine.connect() as connection:
            catalog = inspect_store(connection)
            findings = compare_live_catalog(connection, model)
            findings.extend(store_findings(catalog))
            payload = catalog_as_dict(catalog)
            return findings, payload, catalog.revision
    finally:
        engine.dispose()


def apply_revisions(
    project_root: Path,
    *,
    url: str,
    revision: str = "head",
    run_id: str,
) -> SchemaApplyReport:
    """Upgrade the selected database and retain redacted live-schema evidence."""
    contracts_root = contracts_root_for(project_root)
    before = row_counts(url, load_schema_model_from_root(contracts_root).qualified_names())
    outcome = upgrade(project_root, contracts_root, url=url, revision=revision)
    if not outcome.ok:
        return SchemaApplyReport(outcome, (outcome.detail,), None, None, before)
    findings, payload, applied = inspect_and_compare(project_root, url)
    after = row_counts(url, load_schema_model_from_root(contracts_root).qualified_names())
    payload["row_counts_before"] = before
    payload["row_counts_after"] = after
    payload["url"] = url
    payload["apply_detail"] = outcome.detail
    evidence = write_evidence(project_root, payload, run_id=run_id)
    return SchemaApplyReport(outcome, tuple(findings), evidence, applied, after)


def apply_on_disposable(
    project_root: Path,
    pgdata_dir: Path,
    *,
    run_id: str,
    revision: str = "head",
) -> SchemaApplyReport:
    """Start the pinned image, apply revisions, inspect, and tear down."""
    pins = load_image_pins(project_root)
    if not image_present(pins.local_image_ref):
        detail = f"image {pins.local_image_ref} is not present; not-run"
        return SchemaApplyReport(RunnerOutcome(STATUS_NOT_RUN, detail), (detail,), None, None, {})
    try:
        with disposable_store(project_root, pgdata_dir, pins=pins) as store:
            return apply_revisions(project_root, url=store.url, revision=revision, run_id=run_id)
    except RuntimeError as error:
        return SchemaApplyReport(
            RunnerOutcome(STATUS_FAILED, str(error)), (str(error),), None, None, {}
        )


def downgrade_revisions(project_root: Path, *, url: str, revision: str = "-1") -> RunnerOutcome:
    """Downgrade the selected database, or refuse irreversible revisions."""
    return downgrade(project_root, contracts_root_for(project_root), url=url, revision=revision)


def status_revisions(project_root: Path, *, url: str) -> RunnerOutcome:
    """Report the applied revision of the selected database."""
    return current_revision(project_root, contracts_root_for(project_root), url=url)
