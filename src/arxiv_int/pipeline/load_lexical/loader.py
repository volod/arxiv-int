"""Contract-validated binary-COPY staging load into canonical corpus tables."""

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Table

from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.contracts.sqlalchemy import load_schema_model
from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.resources.paths import contracts_root
from arxiv_int.stores.postgres.load import (
    copy_binary,
    fill_buckets,
    truncate_staging,
    upsert_rows,
)
from arxiv_int.stores.projections.ids import logical_checksum

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LoadCounts:
    """Reconcilable evidence for one contract loaded into the canonical store."""

    contract: str
    table: str
    rows: int
    batches: int
    checksum: str
    identities: tuple[str, ...] = ()

    def as_json_dict(self) -> dict[str, object]:
        """Return a secret-free load summary."""
        return {
            "batches": self.batches,
            "checksum": self.checksum,
            "contract": self.contract,
            "rows": self.rows,
            "table": self.table,
        }


def schema_model(project_root: Path) -> ContractSchemaModel:
    """Load the contract-derived SQLAlchemy metadata for canonical tables."""
    return load_schema_model(FileRegistry(contracts_root(project_root)))


def canonical_table(model: ContractSchemaModel, contract: str) -> Table:
    """Return the canonical table one contract binds to."""
    return model.metadata.tables[model.by_contract(contract).qualified_name]


def load_contract(
    connection: Connection,
    *,
    model: ContractSchemaModel,
    validator: SnapshotValidator,
    contract: str,
    key: str,
    batches: Iterable[list[dict[str, Any]]],
) -> LoadCounts:
    """Validate each batch, COPY it into staging, then upsert the canonical rows."""
    table = canonical_table(model, contract)
    qualified = f"{table.schema}.{table.name}"
    identities: list[str] = []
    rows = 0
    count = 0
    truncate_staging(connection, table.name)
    for batch in batches:
        prepared = _prepared(qualified, batch)
        validator[contract].batch(prepared)
        copy_binary(connection, table, prepared)
        rows += upsert_rows(connection, table, prepared)
        identities.extend(str(row[key]) for row in prepared)
        truncate_staging(connection, table.name)
        count += 1
    _LOG.info("load-lexical loaded contract=%s table=%s rows=%d", contract, qualified, rows)
    return LoadCounts(
        contract,
        qualified,
        rows,
        count,
        logical_checksum(identities),
        tuple(identities),
    )


def _prepared(qualified: str, batch: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return fill_buckets(qualified, list(batch))
