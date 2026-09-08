"""Re-export the contract physical model for SQLAlchemy metadata builders."""

from arxiv_int.contracts.catalog.normalize import (
    DEFAULT_SCHEMA,
    PARTITION_KEY_ORIGIN,
    PROPERTY_ORIGIN,
    ForeignKeyTarget,
    NormalizedColumn,
    NormalizedTable,
    UnsupportedContractMappingError,
    normalize_contract,
)

__all__ = [
    "DEFAULT_SCHEMA",
    "PARTITION_KEY_ORIGIN",
    "PROPERTY_ORIGIN",
    "ForeignKeyTarget",
    "NormalizedColumn",
    "NormalizedTable",
    "UnsupportedContractMappingError",
    "normalize_contract",
]
