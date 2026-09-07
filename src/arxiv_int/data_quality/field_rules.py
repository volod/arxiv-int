"""Structural field rules derived from normalized contract columns."""

from arxiv_int.contracts.sqlalchemy.normalize import NormalizedColumn, NormalizedTable
from arxiv_int.data_quality.identity import UnsupportedQualityMappingError, describe, rule_id
from arxiv_int.data_quality.model import (
    BACKEND_DBT,
    BACKEND_DISK,
    BACKEND_PANDERA,
    KIND_BATCH_UNIQUE,
    KIND_DECIMAL,
    KIND_MAX_LENGTH,
    KIND_NULLABILITY,
    KIND_RELATIONSHIP,
    KIND_TYPE,
    KIND_UNIQUE,
    KIND_UNIT,
    SCOPE_BATCH,
    SCOPE_SNAPSHOT,
    SEVERITY_ERROR,
    QualityRule,
)


def column_rules(
    table: NormalizedTable, column: NormalizedColumn, tables: tuple[NormalizedTable, ...]
) -> tuple[QualityRule, ...]:
    """Return type, nullability, decimal, uniqueness, and relationship rules for one column."""
    rules: list[QualityRule] = [
        QualityRule(
            rule_id=rule_id(table.contract_id, column.name, KIND_TYPE),
            kind=KIND_TYPE,
            scope=SCOPE_BATCH,
            backend=BACKEND_PANDERA,
            severity=SEVERITY_ERROR,
            required=True,
            description=describe(
                column, f"{column.name} must match logical type {column.logical_type}."
            ),
            column=column.name,
            logical_type=column.logical_type,
            dbt_test="dbt_type",
        )
    ]
    if not column.nullable:
        rules.append(
            QualityRule(
                rule_id=rule_id(table.contract_id, column.name, KIND_NULLABILITY),
                kind=KIND_NULLABILITY,
                scope=SCOPE_BATCH,
                backend=BACKEND_PANDERA,
                severity=SEVERITY_ERROR,
                required=True,
                description=describe(column, f"{column.name} is required and must not be null."),
                column=column.name,
                dbt_test="not_null",
            )
        )
    if column.max_length is not None:
        rules.append(
            QualityRule(
                rule_id=rule_id(table.contract_id, column.name, KIND_MAX_LENGTH),
                kind=KIND_MAX_LENGTH,
                scope=SCOPE_BATCH,
                backend=BACKEND_PANDERA,
                severity=SEVERITY_ERROR,
                required=True,
                description=describe(
                    column, f"{column.name} length must be at most {column.max_length}."
                ),
                column=column.name,
                max_length=column.max_length,
                dbt_test="dbt_max_length",
            )
        )
    if column.logical_type == "number":
        precision_text = (
            f" with precision {column.precision} and scale {column.scale}."
            if column.precision is not None
            else "."
        )
        rules.append(
            QualityRule(
                rule_id=rule_id(table.contract_id, column.name, KIND_DECIMAL),
                kind=KIND_DECIMAL,
                scope=SCOPE_BATCH,
                backend=BACKEND_PANDERA,
                severity=SEVERITY_ERROR,
                required=True,
                description=describe(column, f"{column.name} must be decimal{precision_text}"),
                column=column.name,
                logical_type="number",
                precision=column.precision,
                scale=column.scale,
                dbt_test="dbt_decimal",
            )
        )
    if column.primary_key_position is not None or column.unique:
        rules.extend(_unique_rules(table, column))
    relationship = _relationship_rule(table, column, tables)
    if relationship is not None:
        rules.append(relationship)
    return tuple(rules)


def unit_rules(table: NormalizedTable) -> tuple[QualityRule, ...]:
    """Return amount/unit companion rules when a currency or unit column exists."""
    names = {column.name for column in table.columns}
    unit_column = next((name for name in ("currency", "unit") if name in names), None)
    if unit_column is None:
        return ()
    rules: list[QualityRule] = []
    for column in table.columns:
        if column.logical_type != "number":
            continue
        rules.append(
            QualityRule(
                rule_id=rule_id(table.contract_id, column.name, KIND_UNIT),
                kind=KIND_UNIT,
                scope=SCOPE_BATCH,
                backend=BACKEND_PANDERA,
                severity=SEVERITY_ERROR,
                required=True,
                description=describe(
                    column,
                    f"{column.name} requires a non-null {unit_column} when the amount is present.",
                ),
                column=column.name,
                unit_column=unit_column,
                dbt_test="dbt_unit",
            )
        )
    return tuple(rules)


def _unique_rules(table: NormalizedTable, column: NormalizedColumn) -> tuple[QualityRule, ...]:
    return (
        QualityRule(
            rule_id=rule_id(table.contract_id, column.name, KIND_BATCH_UNIQUE),
            kind=KIND_BATCH_UNIQUE,
            scope=SCOPE_BATCH,
            backend=BACKEND_PANDERA,
            severity=SEVERITY_ERROR,
            required=True,
            description=describe(column, f"{column.name} must be unique within each batch."),
            column=column.name,
            dbt_test="unique",
        ),
        QualityRule(
            rule_id=rule_id(table.contract_id, column.name, KIND_UNIQUE),
            kind=KIND_UNIQUE,
            scope=SCOPE_SNAPSHOT,
            backend=BACKEND_DBT,
            severity=SEVERITY_ERROR,
            required=True,
            description=describe(
                column, f"{column.name} must be unique across the whole snapshot."
            ),
            column=column.name,
            disk_backend=BACKEND_DISK,
            dbt_test="unique",
        ),
    )


def _relationship_rule(
    table: NormalizedTable,
    column: NormalizedColumn,
    tables: tuple[NormalizedTable, ...],
) -> QualityRule | None:
    target = column.references
    if target is None:
        return None
    matched = next((item for item in tables if item.schema_id == target.schema_name), None)
    if matched is None:
        raise UnsupportedQualityMappingError(
            f"{table.contract_id}.{column.name}: relationship target "
            f"'{target.schema_name}' is not a registered contract"
        )
    return QualityRule(
        rule_id=rule_id(table.contract_id, column.name, KIND_RELATIONSHIP),
        kind=KIND_RELATIONSHIP,
        scope=SCOPE_SNAPSHOT,
        backend=BACKEND_DBT,
        severity=SEVERITY_ERROR,
        required=True,
        description=describe(
            column,
            f"{column.name} must reference {matched.qualified_name}.{target.column}.",
        ),
        column=column.name,
        target_contract_id=matched.contract_id,
        target_schema=matched.schema_name,
        target_table=matched.table_name,
        target_column=target.column,
        disk_backend=BACKEND_DISK,
        dbt_test="relationships",
    )
