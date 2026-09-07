"""Deterministic YAML emission for generated dbt source and test documents."""

from collections.abc import Mapping, Sequence
from typing import Any

from arxiv_int.data_quality.model import (
    KIND_ACCEPTED_VALUES,
    KIND_NULLABILITY,
    KIND_UNIQUE,
    QualityRule,
    RuleCatalog,
)


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(char in text for char in ":#{}[]&*!|>%@`'\""):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _emit_mapping(document: Mapping[str, Any], indent: int) -> str:
    prefix = "  " * indent
    if not document:
        return f"{prefix}{{}}\n"
    lines: list[str] = []
    for key in sorted(document, key=str):
        value = document[key]
        rendered_key = _scalar(key) if not isinstance(key, str) else key
        if isinstance(value, (Mapping, list, tuple)):
            if not value:
                empty = "{}" if isinstance(value, Mapping) else "[]"
                lines.append(f"{prefix}{rendered_key}: {empty}")
            else:
                lines.append(f"{prefix}{rendered_key}:")
                lines.append(emit_yaml(value, indent + 1).rstrip("\n"))
        else:
            lines.append(f"{prefix}{rendered_key}: {_scalar(value)}")
    return "\n".join(lines) + "\n"


def _emit_sequence(document: Sequence[Any], indent: int) -> str:
    prefix = "  " * indent
    if not document:
        return f"{prefix}[]\n"
    lines: list[str] = []
    for item in document:
        if isinstance(item, (Mapping, list, tuple)):
            nested = emit_yaml(item, indent + 1).rstrip("\n")
            first, _, rest = nested.partition("\n")
            lines.append(f"{prefix}- {first.lstrip()}")
            if rest:
                lines.append(rest)
        else:
            lines.append(f"{prefix}- {_scalar(item)}")
    return "\n".join(lines) + "\n"


def emit_yaml(document: Any, indent: int = 0) -> str:
    """Return sorted, byte-stable YAML for mappings, lists, and scalars."""
    if isinstance(document, Mapping):
        return _emit_mapping(document, indent)
    if isinstance(document, (list, tuple)):
        return _emit_sequence(document, indent)
    return f"{'  ' * indent}{_scalar(document)}\n"


def _column_tests(rules: Sequence[QualityRule]) -> list[Any]:
    tests: list[Any] = []
    for rule in rules:
        if rule.kind == KIND_NULLABILITY:
            tests.append("not_null")
        elif rule.kind == KIND_UNIQUE:
            tests.append("unique")
        elif rule.kind == KIND_ACCEPTED_VALUES:
            tests.append({"accepted_values": {"arguments": {"values": list(rule.accepted_values)}}})
        elif rule.kind == "relationship" and rule.target_schema and rule.target_table:
            tests.append(
                {
                    "relationships": {
                        "arguments": {
                            "field": rule.target_column,
                            "to": f"source('{rule.target_schema}', '{rule.target_table}')",
                        }
                    }
                }
            )
    return tests


def dbt_table_document(catalog: RuleCatalog) -> dict[str, Any]:
    """Return one dbt source table mapping with column tests and descriptions."""
    by_column: dict[str, list[QualityRule]] = {}
    for rule in catalog.rules:
        if rule.column is None:
            continue
        by_column.setdefault(rule.column, []).append(rule)
    columns = []
    for name in by_column:
        column_rules = by_column[name]
        description = next(
            (rule.description for rule in column_rules if rule.description),
            None,
        )
        entry: dict[str, Any] = {
            "description": description,
            "meta": {
                "arxiv_int_rule_ids": [rule.rule_id for rule in column_rules],
            },
            "name": name,
        }
        tests = _column_tests(column_rules)
        if tests:
            entry["tests"] = tests
        columns.append(entry)
    return {
        "columns": columns,
        "config": {"meta": {"arxiv_int_contract_id": catalog.contract_id}},
        "description": catalog.description,
        "meta": {
            "odcs_id": catalog.odcs_id,
            "primary_key": list(catalog.primary_key),
            "rule_catalog_version": catalog.catalog_version,
        },
        "name": catalog.table_name,
    }


def dbt_sources_document(catalogs: Sequence[RuleCatalog]) -> dict[str, Any]:
    """Return one combined dbt sources YAML document grouped by PostgreSQL schema."""
    grouped: dict[str, list[RuleCatalog]] = {}
    for catalog in catalogs:
        grouped.setdefault(catalog.schema_name, []).append(catalog)
    sources = []
    for schema_name in sorted(grouped):
        tables = [
            dbt_table_document(catalog)
            for catalog in sorted(grouped[schema_name], key=lambda item: item.table_name)
        ]
        sources.append(
            {
                "description": f"Canonical {schema_name} relations owned by Alembic.",
                "name": schema_name,
                "schema": schema_name,
                "tables": tables,
            }
        )
    return {"sources": sources, "version": 2}


def render_dbt_yaml(catalogs: Sequence[RuleCatalog]) -> str:
    """Render the combined sources YAML."""
    return emit_yaml(dbt_sources_document(catalogs))


def render_contract_dbt_yaml(catalog: RuleCatalog) -> str:
    """Render one contract's source YAML."""
    return emit_yaml(dbt_sources_document((catalog,)))
