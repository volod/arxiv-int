"""Build contract-derived SQLAlchemy Core metadata for the owned PostgreSQL schemas."""

from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKeyConstraint,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    Table,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, JSONB, TIMESTAMP, VARCHAR
from sqlalchemy.types import TypeEngine

from arxiv_int.contracts.sqlalchemy.normalize import (
    NormalizedColumn,
    NormalizedTable,
    UnsupportedContractMappingError,
    is_floating,
)

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
}


def _column_type(column: NormalizedColumn, label: str) -> TypeEngine[Any]:
    logical = column.logical_type
    if logical == "string":
        return VARCHAR(column.max_length) if column.max_length else Text()
    if logical == "integer":
        return BigInteger()
    if logical == "number":
        if is_floating(column.physical_type):
            return DOUBLE_PRECISION()
        if column.precision is not None:
            return Numeric(precision=column.precision, scale=column.scale)
        return Numeric()
    if logical == "boolean":
        return Boolean()
    if logical == "timestamp":
        return TIMESTAMP(timezone=True)
    if logical == "date":
        return Date()
    if logical == "time":
        return Time()
    if logical in ("object", "array"):
        return JSONB()
    raise UnsupportedContractMappingError(f"{label}: no SQLAlchemy type for {logical!r}")


def _primary_key_columns(table: NormalizedTable) -> tuple[str, ...]:
    keyed = [
        (column.primary_key_position, column.name)
        for column in table.columns
        if column.primary_key_position is not None
    ]
    positions = [position for position, _ in keyed]
    if len(set(positions)) != len(positions):
        raise UnsupportedContractMappingError(
            f"{table.contract_id}: duplicate primaryKeyPosition values"
        )
    return tuple(name for _, name in sorted(keyed))


def _build_table(
    metadata: MetaData,
    table: NormalizedTable,
    schema_index: Mapping[str, NormalizedTable],
) -> Table:
    columns: list[Column[Any]] = []
    constraints: list[UniqueConstraint | ForeignKeyConstraint | PrimaryKeyConstraint] = []
    for column in table.columns:
        label = f"{table.qualified_name}.{column.name}"
        columns.append(
            Column(
                column.name,
                _column_type(column, label),
                nullable=column.nullable,
                comment=column.description,
            )
        )
        if column.unique:
            constraints.append(UniqueConstraint(column.name))
        if column.references is not None:
            target = schema_index.get(column.references.schema_name)
            if target is None:
                raise UnsupportedContractMappingError(
                    f"{label}: relationship target schema "
                    f"'{column.references.schema_name}' is not a registered contract"
                )
            if column.references.column not in {item.name for item in target.columns}:
                raise UnsupportedContractMappingError(
                    f"{label}: relationship target column "
                    f"'{column.references.schema_name}.{column.references.column}' does not exist"
                )
            constraints.append(
                ForeignKeyConstraint(
                    [column.name],
                    [f"{target.qualified_name}.{column.references.column}"],
                )
            )
    primary_key = _primary_key_columns(table)
    if not primary_key:
        raise UnsupportedContractMappingError(f"{table.contract_id}: no primary key is declared")
    constraints.insert(0, PrimaryKeyConstraint(*primary_key))
    return Table(
        table.table_name,
        metadata,
        *columns,
        *constraints,
        schema=table.schema_name,
        comment=table.description,
    )


def build_metadata(tables: Iterable[NormalizedTable]) -> MetaData:
    """Return one MetaData holding every owned schema-qualified contract table."""
    ordered = sorted(tables, key=lambda item: (item.schema_name, item.table_name))
    schema_index: dict[str, NormalizedTable] = {}
    qualified: set[str] = set()
    for table in ordered:
        if table.schema_id in schema_index:
            raise UnsupportedContractMappingError(
                f"duplicate ODCS schema identity '{table.schema_id}' in "
                f"{schema_index[table.schema_id].contract_id} and {table.contract_id}"
            )
        if table.qualified_name in qualified:
            raise UnsupportedContractMappingError(
                f"duplicate physical binding '{table.qualified_name}' for {table.contract_id}"
            )
        schema_index[table.schema_id] = table
        qualified.add(table.qualified_name)
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    for table in ordered:
        _build_table(metadata, table, schema_index)
    return metadata


def owned_schemas(tables: Iterable[NormalizedTable]) -> tuple[str, ...]:
    """Return the sorted PostgreSQL schemas owned by contract metadata."""
    return tuple(sorted({table.schema_name for table in tables}))
