"""Load the registered contract set as one owned SQLAlchemy schema model."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import MetaData

from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.contracts.sqlalchemy.metadata import build_metadata, owned_schemas
from arxiv_int.contracts.sqlalchemy.normalize import NormalizedTable, normalize_contract


@dataclass(frozen=True)
class ContractSchemaModel:
    """Normalized tables plus the SQLAlchemy metadata compiled from them."""

    tables: tuple[NormalizedTable, ...]
    metadata: MetaData

    @property
    def schemas(self) -> tuple[str, ...]:
        """Return the owned PostgreSQL schema names."""
        return owned_schemas(self.tables)

    def qualified_names(self) -> tuple[str, ...]:
        """Return every owned schema-qualified table identity."""
        return tuple(sorted(table.qualified_name for table in self.tables))

    def by_contract(self, contract_id: str) -> NormalizedTable:
        """Return the normalized table for one registered contract."""
        for table in self.tables:
            if table.contract_id == contract_id:
                return table
        raise KeyError(f"Unknown contract id: {contract_id}")


def load_schema_model(registry: FileRegistry) -> ContractSchemaModel:
    """Normalize every registered contract and build one shared MetaData."""
    tables = tuple(
        normalize_contract(registry.load_odcs(contract_id), contract_id)
        for contract_id in registry.contract_ids()
    )
    return ContractSchemaModel(tables, build_metadata(tables))


def load_schema_model_from_root(contracts_root: Path) -> ContractSchemaModel:
    """Load the owned schema model from a contracts tree root."""
    return load_schema_model(FileRegistry(contracts_root))
