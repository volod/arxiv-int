"""Frozen owned-schema state and the reviewed operation diff between two states."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table
from sqlalchemy.dialects import postgresql

from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel

_DIALECT = postgresql.dialect()

STATE_VERSION = 1
OP_CREATE_TABLE = "create_table"
OP_DROP_TABLE = "drop_table"
OP_ADD_COLUMN = "add_column"
OP_DROP_COLUMN = "drop_column"
OP_ALTER_COLUMN = "alter_column"
DATA_LOSING_OPS = frozenset({OP_DROP_TABLE, OP_DROP_COLUMN})


@dataclass(frozen=True, slots=True)
class SchemaOperation:
    """One reviewed schema operation between a frozen state and a candidate state."""

    kind: str
    qualified_name: str
    column: str | None = None
    detail: tuple[tuple[str, Any], ...] = ()

    @property
    def data_losing(self) -> bool:
        """Return whether the operation cannot be reversed without data recovery."""
        return self.kind in DATA_LOSING_OPS


def _column_state(metadata: MetaData, qualified_name: str, name: str) -> dict[str, Any]:
    column = metadata.tables[qualified_name].columns[name]
    foreign_keys = sorted(str(item.target_fullname) for item in column.foreign_keys)
    return {
        "type": str(column.type.compile(dialect=_DIALECT)).upper(),
        "nullable": bool(column.nullable),
        "primaryKey": column.primary_key,
        "comment": column.comment,
        "foreignKeys": foreign_keys,
    }


def _constraint_names(table: Table) -> dict[str, Any]:
    foreign_keys = {
        str(constraint.columns.keys()[0]): str(constraint.name)
        for constraint in table.foreign_key_constraints
    }
    return {
        "primaryKey": str(table.primary_key.name),
        "foreignKeys": dict(sorted(foreign_keys.items())),
    }


def contract_state(model: ContractSchemaModel) -> dict[str, Any]:
    """Serialize the contract-derived owned schema into a comparable frozen state."""
    tables: dict[str, Any] = {}
    for normalized in sorted(model.tables, key=lambda item: item.qualified_name):
        name = normalized.qualified_name
        table = model.metadata.tables[name]
        tables[name] = {
            "contractId": normalized.contract_id,
            "schema": normalized.schema_name,
            "table": normalized.table_name,
            "comment": table.comment,
            "primaryKey": [column.name for column in table.primary_key.columns],
            "constraintNames": _constraint_names(table),
            "columns": {
                column.name: _column_state(model.metadata, name, column.name)
                for column in table.columns
            },
        }
    return {
        "stateVersion": STATE_VERSION,
        "schemas": list(model.schemas),
        "tables": tables,
    }


def empty_state() -> dict[str, Any]:
    """Return the state of a database before any owned revision has run."""
    return {"stateVersion": STATE_VERSION, "schemas": [], "tables": {}}


def load_state(path: Path) -> dict[str, Any]:
    """Load a frozen state document, treating a missing file as the empty state."""
    if not path.is_file():
        return empty_state()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or loaded.get("stateVersion") != STATE_VERSION:
        raise ValueError(f"unsupported migration state document: {path}")
    return loaded


def write_state(path: Path, state: dict[str, Any], *, revision: str) -> Path:
    """Write a frozen state document for the given head revision."""
    payload = {**state, "revision": revision}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _column_operations(
    name: str, before: dict[str, Any], after: dict[str, Any]
) -> list[SchemaOperation]:
    operations: list[SchemaOperation] = []
    old = before.get("columns") or {}
    new = after.get("columns") or {}
    for column in sorted(set(new) - set(old)):
        operations.append(
            SchemaOperation(OP_ADD_COLUMN, name, column, tuple(sorted(new[column].items())))
        )
    for column in sorted(set(old) - set(new)):
        operations.append(
            SchemaOperation(OP_DROP_COLUMN, name, column, tuple(sorted(old[column].items())))
        )
    for column in sorted(set(old) & set(new)):
        if old[column] != new[column]:
            changed = {
                key: value for key, value in new[column].items() if old[column].get(key) != value
            }
            operations.append(
                SchemaOperation(OP_ALTER_COLUMN, name, column, tuple(sorted(changed.items())))
            )
    return operations


def diff_states(before: dict[str, Any], after: dict[str, Any]) -> tuple[SchemaOperation, ...]:
    """Return the reviewed operations that move a frozen state to a candidate state."""
    old_tables = before.get("tables") or {}
    new_tables = after.get("tables") or {}
    operations: list[SchemaOperation] = []
    for name in sorted(set(new_tables) - set(old_tables)):
        operations.append(SchemaOperation(OP_CREATE_TABLE, name))
    for name in sorted(set(old_tables) - set(new_tables)):
        operations.append(SchemaOperation(OP_DROP_TABLE, name))
    for name in sorted(set(old_tables) & set(new_tables)):
        operations.extend(_column_operations(name, old_tables[name], new_tables[name]))
    return tuple(operations)
