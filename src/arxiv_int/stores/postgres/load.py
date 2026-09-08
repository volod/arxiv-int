"""COPY staging, contract quality checks, and bound canonical upserts."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Table, text
from sqlalchemy.dialects.postgresql import insert

from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel
from arxiv_int.data_quality.engine.model import KIND_TYPE
from arxiv_int.data_quality.rules.pandera_schema import polars_dtype
from arxiv_int.resources.paths import contracts_root
from arxiv_int.stores.postgres.constants import STAGING_SCHEMA
from arxiv_int.stores.postgres.hashing import partition_bucket

PRIMARY_KEY_COLUMNS: dict[str, tuple[str, ...]] = {
    "corpus.chunks": ("chunk_id",),
    "corpus.documents": ("document_id",),
    "corpus.source_occurrences": ("occurrence_id",),
    "corpus.spans": ("span_id",),
    "ctl.domain_artifact_registry": ("artifact_id",),
    "eval.anomaly_findings": ("finding_id",),
    "eval.evaluation_items": ("evaluation_item_id",),
    "kg.aliases": ("alias_id",),
    "kg.bom_lines": ("bom_line_id",),
    "kg.catalog_entries": ("catalog_entry_id",),
    "kg.facts": ("fact_id",),
    "kg.invoice_payment_rows": ("row_id",),
    "kg.mentions": ("mention_id",),
    "kg.objects": ("object_id",),
    "kg.relationship_edges": ("edge_id",),
    "kg.supply_chain_edges": ("edge_id",),
    "kg.transactions": ("transaction_id",),
    "ontology.terms": ("term_id",),
    "search.embeddings": ("embedding_id",),
    "search.topic_assignments": ("topic_assignment_id",),
}


class StagingRejectedError(ValueError):
    """Raised when staged rows fail contract quality or constraint checks."""


def fill_buckets(qualified_name: str, rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Copy rows and set ``bucket`` from the logical primary key when present."""
    keys = PRIMARY_KEY_COLUMNS[qualified_name]
    filled: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if item.get(keys[0]) is not None:
            item["bucket"] = partition_bucket(str(item[keys[0]]))
        filled.append(item)
    return filled


def _column_names(table: Table) -> tuple[str, ...]:
    return tuple(column.name for column in table.columns)


def quality_frame(catalog: Any, rows: Sequence[Mapping[str, Any]]) -> Any:
    """Build an eager Polars frame with contract dtypes, including omitted nulls."""
    from arxiv_int.features import require_module

    polars = require_module("polars")
    schema = {
        rule.column: polars_dtype(rule)
        for rule in catalog.rules
        if rule.kind == KIND_TYPE and rule.column is not None
    }
    if not schema:
        return polars.DataFrame(list(rows))
    aligned = [{name: row.get(name) for name in schema} for row in rows]
    return polars.DataFrame(aligned, schema=schema)


def truncate_staging(connection: Connection, table_name: str) -> None:
    """Empty one staging table inside the current transaction."""
    connection.execute(text(f"TRUNCATE {STAGING_SCHEMA}.{table_name}"))


def copy_binary(connection: Connection, table: Table, rows: Sequence[Mapping[str, Any]]) -> None:
    """Stream rows into a staging table with PostgreSQL binary COPY."""
    names = _column_names(table)
    quoted = ", ".join(names)
    sql = f"COPY {STAGING_SCHEMA}.{table.name} ({quoted}) FROM STDIN WITH (FORMAT binary)"
    raw: Any = connection.connection.dbapi_connection
    if raw is None:
        raise RuntimeError("database connection is closed")
    with raw.cursor() as cursor, cursor.copy(sql) as copy:
        for row in rows:
            copy.write_row(tuple(row.get(name) for name in names))


def upsert_rows(connection: Connection, table: Table, rows: Sequence[Mapping[str, Any]]) -> int:
    """Apply a bound INSERT ... ON CONFLICT DO UPDATE for one canonical table."""
    if not rows:
        return 0
    qualified = f"{table.schema}.{table.name}"
    keys = list(PRIMARY_KEY_COLUMNS[qualified])
    names = _column_names(table)
    statement = insert(table)
    assigned = {name: getattr(statement.excluded, name) for name in names if name not in set(keys)}
    statement = statement.on_conflict_do_update(index_elements=keys, set_=assigned)
    connection.execute(statement, [dict(row) for row in rows])
    return len(rows)


def validate_rows(
    model: ContractSchemaModel,
    contract_id: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    project_root: Path,
    run_id: str,
) -> None:
    """Run shared contract quality checks on the staged batch."""
    from arxiv_int.data_quality.engine import ValidationRequest, validate_dataset
    from arxiv_int.data_quality.engine.model import SCOPE_BATCH, STATUS_FAIL
    from arxiv_int.data_quality.generate import compile_catalogs

    registry = FileRegistry(contracts_root(project_root))
    odcs = {item: registry.load_odcs(item) for item in registry.contract_ids()}
    catalogs = {item.contract_id: item for item in compile_catalogs(model, odcs)}
    catalog = catalogs[contract_id]
    frame = quality_frame(catalog, rows)
    result = validate_dataset(
        ValidationRequest(
            catalog=catalog,
            source=frame,
            execute_snapshot=False,
            run_id=run_id,
            project_root=project_root,
        )
    )
    failed = [
        item
        for item in result.checks
        if item.scope == SCOPE_BATCH and item.status == STATUS_FAIL and item.severity == "error"
    ]
    if failed:
        table = model.by_contract(contract_id)
        raise StagingRejectedError(
            f"{table.qualified_name} staging failed quality: {failed[0].rule_id}"
        )


def load_canonical_batch(
    connection: Connection,
    model: ContractSchemaModel,
    contract_id: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    project_root: Path,
    run_id: str,
) -> int:
    """Validate the batch, COPY into staging, upsert into the canonical table, then truncate."""
    table = model.metadata.tables[model.by_contract(contract_id).qualified_name]
    prepared = fill_buckets(f"{table.schema}.{table.name}", rows)
    validate_rows(model, contract_id, prepared, project_root=project_root, run_id=run_id)
    truncate_staging(connection, table.name)
    try:
        copy_binary(connection, table, prepared)
        return upsert_rows(connection, table, prepared)
    finally:
        truncate_staging(connection, table.name)
