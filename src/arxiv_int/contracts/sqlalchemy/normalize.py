"""Re-export the contract physical model for SQLAlchemy metadata builders."""

from arxiv_int.contracts.catalog.normalize import (
    DEFAULT_SCHEMA,
    FLOATING_PHYSICAL_TYPES,
    PARTITION_KEY_ORIGIN,
    PROPERTY_ORIGIN,
    ForeignKeyTarget,
    NormalizedColumn,
    NormalizedTable,
    UnsupportedContractMappingError,
    is_floating,
    normalize_contract,
)

__all__ = [
    "DEFAULT_SCHEMA",
    "FLOATING_PHYSICAL_TYPES",
    "PARTITION_KEY_ORIGIN",
    "PROPERTY_ORIGIN",
    "ForeignKeyTarget",
    "NormalizedColumn",
    "NormalizedTable",
    "UnsupportedContractMappingError",
    "is_floating",
    "normalize_contract",
]
