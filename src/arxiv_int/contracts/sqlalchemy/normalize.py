"""Normalize ODCS schema documents into typed physical table definitions.

The normalized model is the single intermediate shared by SQLAlchemy metadata,
review DDL, migration authoring, and live catalog comparison. Unsupported
metadata raises instead of being silently dropped.
"""

from dataclasses import dataclass
from typing import Any

from arxiv_int.contracts.catalog.odcs_ext import project_extension

DEFAULT_SCHEMA = "public"
PARTITION_KEY_ORIGIN = "partition-key"
PROPERTY_ORIGIN = "contract-property"

_KNOWN_PROPERTY_KEYS = frozenset(
    {
        "businessName",
        "customProperties",
        "description",
        "examples",
        "logicalType",
        "logicalTypeOptions",
        "name",
        "physicalType",
        "primaryKey",
        "primaryKeyPosition",
        "relationships",
        "required",
        "unique",
    }
)
_KNOWN_TYPE_OPTION_KEYS = frozenset({"maxLength", "precision", "scale"})
_SUPPORTED_LOGICAL_TYPES = frozenset(
    {"array", "boolean", "date", "integer", "number", "object", "string", "time", "timestamp"}
)
_SUPPORTED_RELATIONSHIP_TYPES = frozenset({"foreignKey"})


class UnsupportedContractMappingError(ValueError):
    """Raised when ODCS metadata has no reviewed physical mapping."""


@dataclass(frozen=True, slots=True)
class ForeignKeyTarget:
    """One resolved foreign-key target inside the owned schemas."""

    schema_name: str
    column: str


@dataclass(frozen=True, slots=True)
class NormalizedColumn:
    """One physical column with the metadata that must survive generation."""

    name: str
    logical_type: str
    physical_type: str | None
    nullable: bool
    primary_key_position: int | None
    description: str | None
    unique: bool
    max_length: int | None
    precision: int | None
    scale: int | None
    references: ForeignKeyTarget | None
    origin: str = PROPERTY_ORIGIN


@dataclass(frozen=True, slots=True)
class NormalizedTable:
    """One contract's schema-qualified physical table."""

    contract_id: str
    odcs_id: str
    version: str
    schema_name: str
    table_name: str
    schema_id: str
    description: str | None
    partition_key: str | None
    columns: tuple[NormalizedColumn, ...]

    @property
    def qualified_name(self) -> str:
        """Return the schema-qualified table identity."""
        return f"{self.schema_name}.{self.table_name}"


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise UnsupportedContractMappingError(f"{label} must be a mapping")
    return value


def _type_options(prop: dict[str, Any], label: str) -> tuple[int | None, int | None, int | None]:
    raw = prop.get("logicalTypeOptions")
    if raw is None:
        return None, None, None
    options = _require_mapping(raw, f"{label}: logicalTypeOptions")
    unknown = sorted(set(options) - _KNOWN_TYPE_OPTION_KEYS)
    if unknown:
        raise UnsupportedContractMappingError(
            f"{label}: unsupported logicalTypeOptions keys: {', '.join(unknown)}"
        )
    max_length = options.get("maxLength")
    precision = options.get("precision")
    scale = options.get("scale")
    for name, value in (("maxLength", max_length), ("precision", precision), ("scale", scale)):
        if value is not None and not isinstance(value, int):
            raise UnsupportedContractMappingError(f"{label}: {name} must be an integer")
    if scale is not None and precision is None:
        raise UnsupportedContractMappingError(f"{label}: scale requires an explicit precision")
    return max_length, precision, scale


def _relationship(prop: dict[str, Any], label: str) -> ForeignKeyTarget | None:
    relationships = prop.get("relationships") or []
    if not isinstance(relationships, list):
        raise UnsupportedContractMappingError(f"{label}: relationships must be a list")
    targets: list[ForeignKeyTarget] = []
    for item in relationships:
        entry = _require_mapping(item, f"{label}: relationship")
        kind = str(entry.get("type", ""))
        if kind not in _SUPPORTED_RELATIONSHIP_TYPES:
            raise UnsupportedContractMappingError(
                f"{label}: unsupported relationship type {kind!r}"
            )
        reference = str(entry.get("to", ""))
        schema_name, _, column = reference.partition(".")
        if not schema_name or not column or "." in column:
            raise UnsupportedContractMappingError(
                f"{label}: relationship target must be '<schema>.<field>': {reference!r}"
            )
        targets.append(ForeignKeyTarget(schema_name, column))
    if len(targets) > 1:
        raise UnsupportedContractMappingError(f"{label}: multiple foreign-key targets")
    return targets[0] if targets else None


def _column(prop: dict[str, Any], schema_id: str) -> NormalizedColumn:
    name = prop.get("name")
    if not isinstance(name, str) or not name:
        raise UnsupportedContractMappingError(f"schema '{schema_id}' has a property without a name")
    label = f"{schema_id}.{name}"
    unknown = sorted(set(prop) - _KNOWN_PROPERTY_KEYS)
    if unknown:
        raise UnsupportedContractMappingError(
            f"{label}: unsupported property keys: {', '.join(unknown)}"
        )
    logical_type = str(prop.get("logicalType", ""))
    if logical_type not in _SUPPORTED_LOGICAL_TYPES:
        raise UnsupportedContractMappingError(f"{label}: unsupported logicalType {logical_type!r}")
    max_length, precision, scale = _type_options(prop, label)
    position = prop.get("primaryKeyPosition") if prop.get("primaryKey") else None
    if prop.get("primaryKey") and not isinstance(position, int):
        raise UnsupportedContractMappingError(f"{label}: primaryKey requires primaryKeyPosition")
    physical_type = prop.get("physicalType")
    if physical_type is not None and not isinstance(physical_type, str):
        raise UnsupportedContractMappingError(f"{label}: physicalType must be a string")
    return NormalizedColumn(
        name=name,
        logical_type=logical_type,
        physical_type=physical_type,
        nullable=not bool(prop.get("required", False)),
        primary_key_position=position,
        description=prop.get("description"),
        unique=bool(prop.get("unique", False)),
        max_length=max_length,
        precision=precision,
        scale=scale,
        references=_relationship(prop, label),
    )


def _partition_column(partition_key: str, present: set[str]) -> tuple[NormalizedColumn, ...]:
    if partition_key in present:
        return ()
    return (
        NormalizedColumn(
            name=partition_key,
            logical_type="string",
            physical_type=None,
            nullable=True,
            primary_key_position=None,
            description="Declared physical partition key from x-arxiv-int.partitionKey.",
            unique=False,
            max_length=None,
            precision=None,
            scale=None,
            references=None,
            origin=PARTITION_KEY_ORIGIN,
        ),
    )


def normalize_contract(odcs: dict[str, Any], contract_id: str) -> NormalizedTable:
    """Normalize one ODCS document into a schema-qualified physical table."""
    schemas = odcs.get("schema")
    if not isinstance(schemas, list) or len(schemas) != 1:
        raise UnsupportedContractMappingError(
            f"{contract_id}: exactly one ODCS schema object is supported"
        )
    schema = _require_mapping(schemas[0], f"{contract_id}: schema")
    schema_id = str(schema.get("name") or "")
    if not schema_id:
        raise UnsupportedContractMappingError(f"{contract_id}: schema object requires a name")
    extension = project_extension(odcs.get("customProperties")) or {}
    properties = schema.get("properties")
    if not isinstance(properties, list) or not properties:
        raise UnsupportedContractMappingError(f"{contract_id}: schema '{schema_id}' has no fields")
    columns = [
        _column(_require_mapping(item, f"{schema_id}: property"), schema_id) for item in properties
    ]
    names = [column.name for column in columns]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise UnsupportedContractMappingError(
            f"{contract_id}: duplicate field names: {', '.join(duplicates)}"
        )
    partition_key = extension.get("partitionKey")
    partition_name = str(partition_key) if partition_key else None
    if partition_name:
        columns.extend(_partition_column(partition_name, set(names)))
    description = (odcs.get("description") or {}).get("purpose")
    return NormalizedTable(
        contract_id=contract_id,
        odcs_id=str(odcs.get("id", contract_id)),
        version=str(odcs.get("version", "")),
        schema_name=str(extension.get("schema") or DEFAULT_SCHEMA),
        table_name=str(extension.get("table") or schema.get("physicalName") or schema_id),
        schema_id=schema_id,
        description=str(description) if description else None,
        partition_key=partition_name,
        columns=tuple(columns),
    )
