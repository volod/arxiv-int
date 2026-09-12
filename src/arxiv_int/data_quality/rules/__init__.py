"""Compile contract-derived quality rules from normalized ODCS fields."""

from typing import Any

from arxiv_int.contracts.sqlalchemy.normalize import NormalizedTable
from arxiv_int.data_quality.engine.model import QualityRule, RuleCatalog
from arxiv_int.data_quality.rules.declared import declared_quality
from arxiv_int.data_quality.rules.field_rules import column_rules, unit_rules
from arxiv_int.data_quality.rules.identity import UnsupportedQualityMappingError

__all__ = ["UnsupportedQualityMappingError", "compile_rule_catalog"]


def compile_rule_catalog(
    table: NormalizedTable,
    tables: tuple[NormalizedTable, ...],
    odcs: dict[str, Any],
) -> RuleCatalog:
    """Build the stable rule catalog for one normalized contract table."""
    primary_key = _primary_key(table)
    rules: list[QualityRule] = []
    for column in table.columns:
        rules.extend(column_rules(table, column, tables))
    rules.extend(unit_rules(table))
    rules.extend(declared_quality(table, odcs))
    return RuleCatalog(
        contract_id=table.contract_id,
        odcs_id=table.odcs_id,
        version=table.version,
        description=table.description,
        schema_name=table.schema_name,
        table_name=table.table_name,
        primary_key=primary_key,
        rules=tuple(rules),
    )


def _primary_key(table: NormalizedTable) -> tuple[str, ...]:
    """Return the ordered key, refusing a composite one until it can be compiled.

    Uniqueness rules are compiled per column, so a composite key would wrongly require each of
    its columns to be unique on its own. No contract declares one; refusing here keeps a future
    contract from silently publishing rules that its own key does not satisfy.
    """
    names = tuple(
        column.name
        for column in sorted(
            (item for item in table.columns if item.primary_key_position is not None),
            key=lambda item: item.primary_key_position or 0,
        )
    )
    if len(names) > 1:
        listed = ", ".join(names)
        raise UnsupportedQualityMappingError(
            f"{table.contract_id}: composite primary key ({listed}) has no compiled uniqueness "
            "rule; declare one key column or add a composite rule kind first"
        )
    return names
