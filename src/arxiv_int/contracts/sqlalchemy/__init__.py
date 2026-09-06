"""Contract-derived SQLAlchemy Core schema metadata and review DDL."""

from arxiv_int.contracts.sqlalchemy.ddl import baseline_ddl, contract_ddl, create_schema_statements
from arxiv_int.contracts.sqlalchemy.metadata import (
    NAMING_CONVENTION,
    build_metadata,
    owned_schemas,
)
from arxiv_int.contracts.sqlalchemy.model import (
    ContractSchemaModel,
    load_schema_model,
    load_schema_model_from_root,
)
from arxiv_int.contracts.sqlalchemy.normalize import (
    ForeignKeyTarget,
    NormalizedColumn,
    NormalizedTable,
    UnsupportedContractMappingError,
    normalize_contract,
)

__all__ = [
    "NAMING_CONVENTION",
    "ContractSchemaModel",
    "ForeignKeyTarget",
    "NormalizedColumn",
    "NormalizedTable",
    "UnsupportedContractMappingError",
    "baseline_ddl",
    "build_metadata",
    "contract_ddl",
    "create_schema_statements",
    "load_schema_model",
    "load_schema_model_from_root",
    "normalize_contract",
    "owned_schemas",
]
