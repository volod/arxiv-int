"""Live adoption: relocate verified legacy tables, then stamp only equivalent catalogs."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, create_engine, text

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.migrations.adoption import adoption_findings, require_safe_adoption
from arxiv_int.contracts.migrations.errors import UnsafeAdoptionError
from arxiv_int.contracts.migrations.runner import (
    STATUS_FAILED,
    STATUS_NOT_RUN,
    STATUS_OK,
    RunnerOutcome,
    resolve_database_url,
    stamp,
)
from arxiv_int.contracts.sqlalchemy.catalog import compare_live_catalog
from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel, load_schema_model_from_root
from arxiv_int.stores.postgres.catalog_boundary import catalog_boundary_findings
from arxiv_int.stores.postgres.constants import HEAD_REVISION, INITIAL_REVISION
from arxiv_int.stores.postgres.evidence import catalog_as_dict, write_evidence
from arxiv_int.stores.postgres.inspect_live import LiveStoreCatalog, inspect_store, store_findings


@dataclass(frozen=True, slots=True)
class AdoptionReport:
    """Result of one live adoption attempt."""

    outcome: RunnerOutcome
    findings: tuple[str, ...]
    stamped_revision: str | None
    relocated: tuple[str, ...]
    row_counts: dict[str, int]
    evidence_path: Path | None

    @property
    def ok(self) -> bool:
        """Return whether the database was stamped after proved equivalence."""
        return self.outcome.ok and not self.findings and self.stamped_revision is not None


def _has_table(connection: Connection, schema: str, table: str) -> bool:
    return bool(
        connection.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_tables "
                "WHERE schemaname = :schema AND tablename = :table)"
            ),
            {"schema": schema, "table": table},
        ).scalar()
    )


def _row_count(connection: Connection, schema: str, table: str) -> int:
    return int(connection.execute(text(f"SELECT count(*) FROM {schema}.{table}")).scalar() or 0)


def relocate_public_tables(connection: Connection, model: ContractSchemaModel) -> list[str]:
    """Move unqualified public tables into owned schemas when the destination is empty."""
    relocated: list[str] = []
    for schema in ("corpus", "ctl", "eval", "kg", "ontology", "search"):
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    for name in model.qualified_names():
        schema, _, table = name.partition(".")
        public_present = _has_table(connection, "public", table)
        owned_present = _has_table(connection, schema, table)
        if public_present and owned_present:
            raise UnsafeAdoptionError(
                f"refusing to relocate public.{table} because {name} already exists"
            )
        if public_present:
            connection.execute(text(f"ALTER TABLE public.{table} SET SCHEMA {schema}"))
            relocated.append(name)
    return relocated


def _overlay_for_stamp(catalog: LiveStoreCatalog) -> tuple[list[str], str | None]:
    head = store_findings(catalog, require_head=False, require_ledger=True)
    if not head:
        return [], HEAD_REVISION
    base = store_findings(catalog, require_head=False, require_ledger=False)
    if not base:
        return [], INITIAL_REVISION
    return head, None


def adopt_database(
    project_root: Path,
    *,
    url: str | None = None,
    run_id: str = "adopt",
) -> AdoptionReport:
    """Stamp a live database only after catalog equivalence is proved."""
    contracts_root = contracts_root_for(project_root)
    model = load_schema_model_from_root(contracts_root)
    resolved = resolve_database_url(url)
    if not resolved:
        missing = adoption_findings(project_root, model)
        return AdoptionReport(
            RunnerOutcome(STATUS_NOT_RUN, missing[0]),
            tuple(missing),
            None,
            (),
            {},
            None,
        )
    engine = create_engine(resolved, pool_pre_ping=True)
    relocated: list[str] = []
    counts: dict[str, int] = {}
    catalog: LiveStoreCatalog | None = None
    target: str | None = None
    try:
        with engine.begin() as connection:
            relocated = relocate_public_tables(connection, model)
            catalog_issues = compare_live_catalog(connection, model)
            require_safe_adoption(project_root, model, catalog_findings=catalog_issues)
            catalog = inspect_store(connection)
            overlay, target = _overlay_for_stamp(catalog)
            if target is None:
                raise UnsafeAdoptionError(
                    "refusing to stamp a partial store overlay: " + "; ".join(overlay)
                )
            definition_issues = catalog_boundary_findings(project_root, connection, target)
            if definition_issues:
                raise UnsafeAdoptionError(
                    "refusing drifted or partial catalog: " + "; ".join(definition_issues)
                )
            if catalog.revision and catalog.revision != target:
                raise UnsafeAdoptionError(
                    f"database is already stamped at {catalog.revision}, not {target}"
                )
            for name in model.qualified_names():
                schema, _, table = name.partition(".")
                if _has_table(connection, schema, table):
                    counts[name] = _row_count(connection, schema, table)
        already = catalog is not None and catalog.revision == target
        if already:
            outcome = RunnerOutcome(STATUS_OK, f"already stamped at {target}")
        else:
            outcome = stamp(project_root, contracts_root, url=resolved, revision=str(target))
        payload: dict[str, Any] = catalog_as_dict(catalog) if catalog else {}
        payload["url"] = resolved
        payload["relocated"] = relocated
        payload["row_counts"] = counts
        payload["stamped_revision"] = target
        evidence = write_evidence(project_root, payload, run_id=run_id)
        stamp_findings: tuple[str, ...] = () if outcome.ok else (outcome.detail,)
        stamped = target if outcome.ok else None
        return AdoptionReport(outcome, stamp_findings, stamped, tuple(relocated), counts, evidence)
    except UnsafeAdoptionError as error:
        return AdoptionReport(
            RunnerOutcome(STATUS_FAILED, str(error)),
            (str(error),),
            None,
            tuple(relocated),
            counts,
            None,
        )
    finally:
        engine.dispose()
