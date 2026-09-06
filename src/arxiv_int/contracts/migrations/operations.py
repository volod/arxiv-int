"""Translate frozen schema operations into literal Alembic Python statements."""

import json
import re
from typing import Any

from arxiv_int.contracts.migrations.state import (
    OP_ADD_COLUMN,
    OP_ALTER_COLUMN,
    OP_CREATE_TABLE,
    OP_DROP_COLUMN,
    OP_DROP_TABLE,
    SchemaOperation,
)

_SIMPLE_TYPES = {
    "TEXT": "sa.Text()",
    "BIGINT": "sa.BigInteger()",
    "NUMERIC": "sa.Numeric()",
    "BOOLEAN": "sa.Boolean()",
    "DATE": "sa.Date()",
    "TIME": "sa.Time()",
    "JSONB": "postgresql.JSONB()",
    "TIMESTAMP WITH TIME ZONE": "postgresql.TIMESTAMP(timezone=True)",
}
_VARCHAR = re.compile(r"^VARCHAR\((?P<length>\d+)\)$")
_NUMERIC = re.compile(r"^NUMERIC\((?P<precision>\d+)(?:,\s*(?P<scale>\d+))?\)$")


class UnrenderableOperationError(ValueError):
    """Raised when a frozen state uses a type with no reviewed Python literal."""


def type_expression(compiled: str) -> str:
    """Return the frozen Python literal for one compiled PostgreSQL type."""
    text = compiled.strip().upper()
    if text in _SIMPLE_TYPES:
        return _SIMPLE_TYPES[text]
    varchar = _VARCHAR.match(text)
    if varchar:
        return f"sa.String(length={varchar.group('length')})"
    numeric = _NUMERIC.match(text)
    if numeric:
        scale = numeric.group("scale")
        if scale is None:
            return f"sa.Numeric(precision={numeric.group('precision')})"
        return f"sa.Numeric(precision={numeric.group('precision')}, scale={scale})"
    raise UnrenderableOperationError(f"no reviewed Python literal for column type {compiled!r}")


def literal(value: Any) -> str:
    return "None" if value is None else json.dumps(str(value), ensure_ascii=True)


def _columnliteral(name: str, spec: dict[str, Any]) -> str:
    return (
        f'        sa.Column("{name}", {type_expression(str(spec["type"]))}, '
        f"nullable={bool(spec['nullable'])}, comment={literal(spec.get('comment'))}),"
    )


def _table_literals(name: str, table: dict[str, Any]) -> list[str]:
    names = table.get("constraintNames") or {}
    lines = ["    op.create_table(", f'        "{table["table"]}",']
    for column, spec in table["columns"].items():
        lines.append(_columnliteral(column, spec))
    primary_key = ", ".join(f'"{item}"' for item in table["primaryKey"])
    lines.append(
        f'        sa.PrimaryKeyConstraint({primary_key}, name="{names.get("primaryKey")}"),'
    )
    for column, constraint in (names.get("foreignKeys") or {}).items():
        target = (table["columns"][column].get("foreignKeys") or [""])[0]
        lines.append(
            f'        sa.ForeignKeyConstraint(["{column}"], ["{target}"], name="{constraint}"),'
        )
    lines.append(f'        schema="{table["schema"]}",')
    lines.append(f"        comment={literal(table.get('comment'))},")
    lines.append("    )")
    return lines


def _foreign_targets(table: dict[str, Any]) -> set[str]:
    return {
        ".".join(str(reference).split(".")[:2])
        for spec in table["columns"].values()
        for reference in (spec.get("foreignKeys") or [])
    }


def _creation_order(names: list[str], tables: dict[str, Any]) -> list[str]:
    """Order created tables so referenced owned tables exist first."""
    pending = sorted(names)
    ordered: list[str] = []
    while pending:
        ready = [
            name for name in pending if not (_foreign_targets(tables[name]) & set(pending)) - {name}
        ]
        if not ready:
            ordered.extend(pending)
            break
        ordered.extend(ready)
        pending = [name for name in pending if name not in set(ready)]
    return ordered


def upgrade_lines(operations: tuple[SchemaOperation, ...], after: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    tables = after["tables"]
    created = [op.qualified_name for op in operations if op.kind == OP_CREATE_TABLE]
    for schema in sorted({tables[name]["schema"] for name in created}):
        lines.append(f'    op.execute("CREATE SCHEMA IF NOT EXISTS {schema}")')
    for name in _creation_order(created, tables):
        lines.extend(_table_literals(name, tables[name]))
    for operation in operations:
        lines.extend(_single_upgrade_lines(operation, tables))
    return lines or ["    pass"]


def _single_upgrade_lines(operation: SchemaOperation, tables: dict[str, Any]) -> list[str]:
    schema, _, table = operation.qualified_name.partition(".")
    detail = dict(operation.detail)
    if operation.kind == OP_ADD_COLUMN:
        spec = tables[operation.qualified_name]["columns"][operation.column]
        column = _columnliteral(str(operation.column), spec).strip().rstrip(",")
        return [f'    op.add_column("{table}", {column}, schema="{schema}")']
    if operation.kind == OP_DROP_COLUMN:
        return [f'    op.drop_column("{table}", "{operation.column}", schema="{schema}")']
    if operation.kind == OP_DROP_TABLE:
        return [f'    op.drop_table("{table}", schema="{schema}")']
    if operation.kind == OP_ALTER_COLUMN:
        spec = tables[operation.qualified_name]["columns"][operation.column]
        return [
            "    op.alter_column(",
            f'        "{table}",',
            f'        "{operation.column}",',
            f"        type_={type_expression(str(spec['type']))},",
            f"        nullable={bool(spec['nullable'])},",
            f"        comment={literal(spec.get('comment'))},",
            f'        schema="{schema}",',
            f"    )  # changed: {', '.join(sorted(detail))}",
        ]
    return []


def downgrade_lines(operations: tuple[SchemaOperation, ...], before: dict[str, Any]) -> list[str]:
    if any(operation.data_losing for operation in operations):
        return ["    raise IrreversibleRevisionError(IRREVERSIBLE_REASON)"]
    lines: list[str] = []
    tables = before["tables"]
    for operation in reversed(operations):
        schema, _, table = operation.qualified_name.partition(".")
        if operation.kind == OP_CREATE_TABLE:
            lines.append(f'    op.drop_table("{table}", schema="{schema}")')
        elif operation.kind == OP_ADD_COLUMN:
            lines.append(f'    op.drop_column("{table}", "{operation.column}", schema="{schema}")')
        elif operation.kind == OP_ALTER_COLUMN:
            spec = tables[operation.qualified_name]["columns"][operation.column]
            lines.extend(
                [
                    "    op.alter_column(",
                    f'        "{table}",',
                    f'        "{operation.column}",',
                    f"        type_={type_expression(str(spec['type']))},",
                    f"        nullable={bool(spec['nullable'])},",
                    f"        comment={literal(spec.get('comment'))},",
                    f'        schema="{schema}",',
                    "    )",
                ]
            )
    return lines or ["    pass"]
