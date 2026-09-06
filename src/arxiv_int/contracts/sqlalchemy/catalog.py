"""Compare a live PostgreSQL catalog to contract-derived metadata.

Comparison uses catalog definitions rather than SQL text: expected column types are
compiled with the PostgreSQL dialect and matched against reflected column types.
Only owned tables participate; dbt relations, extension internals, and other
applications stay outside the comparison unless they were previously owned.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, MetaData, inspect
from sqlalchemy.dialects import postgresql

from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel

_DIALECT = postgresql.dialect()

CatalogSnapshot = Mapping[str, Mapping[str, "CatalogColumn"]]


@dataclass(frozen=True, slots=True)
class CatalogColumn:
    """One catalog column definition reduced to compared attributes."""

    data_type: str
    nullable: bool
    primary_key: bool


def _compiled_type(type_: Any) -> str:
    return str(type_.compile(dialect=_DIALECT)).upper()


def expected_catalog(metadata: MetaData, qualified_names: Iterable[str]) -> CatalogSnapshot:
    """Return the expected owned catalog from contract-derived metadata."""
    snapshot: dict[str, dict[str, CatalogColumn]] = {}
    for name in sorted(set(qualified_names)):
        table = metadata.tables[name]
        primary_key = {column.name for column in table.primary_key.columns}
        snapshot[name] = {
            column.name: CatalogColumn(
                data_type=_compiled_type(column.type),
                nullable=bool(column.nullable),
                primary_key=column.name in primary_key,
            )
            for column in table.columns
        }
    return snapshot


def reflect_catalog(connection: Connection, qualified_names: Iterable[str]) -> CatalogSnapshot:
    """Reflect only owned tables from a live database."""
    inspector = inspect(connection)
    snapshot: dict[str, dict[str, CatalogColumn]] = {}
    for name in sorted(set(qualified_names)):
        schema_name, _, table_name = name.partition(".")
        if not inspector.has_table(table_name, schema=schema_name):
            continue
        constraint = inspector.get_pk_constraint(table_name, schema=schema_name)
        primary_key = set(constraint.get("constrained_columns") or ())
        snapshot[name] = {
            str(column["name"]): CatalogColumn(
                data_type=_compiled_type(column["type"]),
                nullable=bool(column["nullable"]),
                primary_key=str(column["name"]) in primary_key,
            )
            for column in inspector.get_columns(table_name, schema=schema_name)
        }
    return snapshot


def _column_findings(
    name: str, expected: Mapping[str, CatalogColumn], observed: Mapping[str, CatalogColumn]
) -> list[str]:
    findings: list[str] = []
    for column in sorted(set(expected) - set(observed)):
        findings.append(f"live catalog table '{name}' is missing column '{column}'")
    for column in sorted(set(observed) - set(expected)):
        findings.append(f"live catalog table '{name}' has unexpected column '{column}'")
    for column in sorted(set(expected) & set(observed)):
        want = expected[column]
        have = observed[column]
        if want.data_type != have.data_type:
            findings.append(
                f"live catalog '{name}.{column}' type is {have.data_type}, expected {want.data_type}"
            )
        if want.nullable != have.nullable:
            findings.append(
                f"live catalog '{name}.{column}' nullability is {have.nullable}, "
                f"expected {want.nullable}"
            )
        if want.primary_key != have.primary_key:
            findings.append(
                f"live catalog '{name}.{column}' primary-key membership is {have.primary_key}, "
                f"expected {want.primary_key}"
            )
    return findings


def catalog_findings(
    expected: CatalogSnapshot,
    observed: CatalogSnapshot,
    *,
    prior_owned: Iterable[str] = (),
) -> list[str]:
    """Diff expected and observed owned catalogs, keeping prior ownership for removals."""
    owned = set(expected) | set(prior_owned)
    findings: list[str] = []
    for name in sorted(set(expected) - set(observed)):
        findings.append(f"live catalog is missing owned table '{name}'")
    for name in sorted((set(observed) & owned) - set(expected)):
        findings.append(f"live catalog still holds previously owned table '{name}'")
    for name in sorted(set(expected) & set(observed)):
        findings.extend(_column_findings(name, expected[name], observed[name]))
    return findings


def compare_live_catalog(
    connection: Connection,
    model: ContractSchemaModel,
    *,
    prior_owned: Iterable[str] = (),
) -> list[str]:
    """Compare a live database to contract metadata over owned objects only."""
    names = set(model.qualified_names()) | set(prior_owned)
    expected = expected_catalog(model.metadata, model.qualified_names())
    observed = reflect_catalog(connection, names)
    return catalog_findings(expected, observed, prior_owned=prior_owned)
