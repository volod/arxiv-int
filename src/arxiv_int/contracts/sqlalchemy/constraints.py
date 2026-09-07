"""Compare owned key, default, check and index definitions, not just their names."""

from typing import Any, cast

from sqlalchemy import CheckConstraint, DefaultClause, Table, UniqueConstraint
from sqlalchemy.engine.reflection import Inspector
from sqlglot import exp, parse_one


def normalized_expression(sql: str) -> exp.Expression:
    """Normalize PostgreSQL's text casts and IN rendering without discarding precedence."""
    tree = parse_one(sql, read="postgres")
    for node in reversed(list(tree.walk())):
        replacement = _normalize_node(node)
        if node is tree:
            tree = replacement
        elif replacement is not node:
            node.replace(replacement)
    return tree


def _normalize_node(node: exp.Expression) -> exp.Expression:
    if isinstance(node, exp.Paren):
        return cast(exp.Expression, node.this)
    if (
        isinstance(node, exp.Cast)
        and isinstance(node.this, exp.Literal)
        and node.this.is_string
        and node.to == exp.DataType.build("text")
    ):
        return node.this
    if isinstance(node, exp.EQ) and isinstance(node.expression, exp.Any):
        array = node.expression.this
        if isinstance(array, exp.Array):
            return exp.In(this=node.this, expressions=array.expressions)
    return node


def constraint_findings(inspector: Inspector, table: Table) -> list[str]:
    """Check canonical and store-owned constraints and declared indexes."""
    findings: list[str] = []
    primary = inspector.get_pk_constraint(table.name, schema=table.schema)
    if tuple(primary.get("constrained_columns") or ()) != tuple(table.primary_key.columns.keys()):
        findings.append(f"live catalog '{table.fullname}' primary-key order differs")
    observed_fks = inspector.get_foreign_keys(table.name, schema=table.schema)
    for key in table.foreign_key_constraints:
        columns = tuple(key.columns.keys())
        matches = [item for item in observed_fks if tuple(item["constrained_columns"]) == columns]
        expected = tuple(element.target_fullname for element in key.elements)
        if not any(_foreign_target(item) == expected for item in matches):
            findings.append(
                f"live catalog '{table.fullname}' foreign key {key.name or columns} differs"
            )
    observed_unique = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints(table.name, schema=table.schema)
    }
    for constraint in table.constraints:
        if (
            isinstance(constraint, UniqueConstraint)
            and tuple(constraint.columns.keys()) not in observed_unique
        ):
            findings.append(f"live catalog '{table.fullname}' unique key {constraint.name} differs")
    findings.extend(_check_findings(inspector, table))
    findings.extend(_default_index_findings(inspector, table))
    return findings


def _foreign_target(item: Any) -> tuple[str, ...]:
    return tuple(
        f"{item['referred_schema'] or 'public'}.{item['referred_table']}.{column}"
        for column in item["referred_columns"]
    )


def _check_findings(inspector: Inspector, table: Table) -> list[str]:
    observed = {
        str(item["name"]): item
        for item in inspector.get_check_constraints(table.name, schema=table.schema)
    }
    findings: list[str] = []
    for constraint in table.constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        actual = observed.get(str(constraint.name))
        if actual is None or normalized_expression(
            str(constraint.sqltext)
        ) != normalized_expression(actual["sqltext"]):
            findings.append(f"live catalog '{table.fullname}' check {constraint.name} differs")
        elif actual.get("dialect_options", {}).get("postgresql_not_valid"):
            findings.append(
                f"live catalog '{table.fullname}' check {constraint.name} is not validated"
            )
    return findings


def _default_index_findings(inspector: Inspector, table: Table) -> list[str]:
    findings: list[str] = []
    observed_columns = {
        item["name"]: item for item in inspector.get_columns(table.name, schema=table.schema)
    }
    for column in table.columns:
        actual = observed_columns.get(column.name)
        if actual is None:
            continue
        expected_default = (
            str(column.server_default.arg)
            if isinstance(column.server_default, DefaultClause)
            else None
        )
        observed_default = actual.get("default")
        if expected_default != observed_default:
            findings.append(f"live catalog '{table.fullname}.{column.name}' default differs")
    observed_indexes = {
        item["name"]: (tuple(item["column_names"]), bool(item["unique"]))
        for item in inspector.get_indexes(table.name, schema=table.schema)
    }
    for index in table.indexes:
        if observed_indexes.get(index.name) != (tuple(index.columns.keys()), bool(index.unique)):
            findings.append(f"live catalog '{table.fullname}' index {index.name} differs")
    return findings
