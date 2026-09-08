"""Compile reviewed ODCS `quality` declarations into catalog rules."""

from typing import Any

from arxiv_int.contracts.sqlalchemy.normalize import NormalizedTable
from arxiv_int.data_quality.engine.model import (
    BACKEND_PANDERA,
    KIND_ACCEPTED_VALUES,
    SCOPE_BATCH,
    SEVERITY_ERROR,
    QualityRule,
)
from arxiv_int.data_quality.rules.identity import UnsupportedQualityMappingError, rule_id

_SUPPORTED_QUALITY_TYPES = frozenset({"library"})
_SUPPORTED_QUALITY_ENGINES = frozenset({"pandera", "dbt"})
_SUPPORTED_LIBRARY_RULES = frozenset({"accepted_values", "acceptedValues"})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise UnsupportedQualityMappingError(message)


def _accepted_rule(table: NormalizedTable, item: dict[str, Any], names: set[str]) -> QualityRule:
    kind = str(item.get("type") or "")
    engine = str(item.get("engine") or "")
    rule_name = str(item.get("rule") or "")
    _require(
        kind in _SUPPORTED_QUALITY_TYPES, f"{table.contract_id}: unknown quality type {kind!r}"
    )
    _require(
        engine in _SUPPORTED_QUALITY_ENGINES,
        f"{table.contract_id}: unknown quality engine {engine!r}",
    )
    _require(
        rule_name in _SUPPORTED_LIBRARY_RULES,
        f"{table.contract_id}: unknown quality rule {rule_name!r}",
    )
    column = str(item.get("field") or "")
    _require(
        column in names,
        f"{table.contract_id}: quality field {column!r} is not a contract column",
    )
    raw_values = item.get("validValues") or item.get("acceptedValues") or []
    _require(
        isinstance(raw_values, list) and bool(raw_values),
        f"{table.contract_id}: accepted values for {column} must be a non-empty list",
    )
    values = tuple(str(value) for value in raw_values)
    description = str(item.get("description") or f"{column} must be one of {', '.join(values)}.")
    return QualityRule(
        rule_id=rule_id(table.contract_id, column, KIND_ACCEPTED_VALUES),
        kind=KIND_ACCEPTED_VALUES,
        scope=SCOPE_BATCH,
        backend=BACKEND_PANDERA,
        severity=SEVERITY_ERROR,
        required=True,
        description=description,
        column=column,
        accepted_values=values,
        dbt_test="accepted_values",
    )


def declared_quality(table: NormalizedTable, odcs: dict[str, Any]) -> tuple[QualityRule, ...]:
    """Map supported library quality entries; refuse unknown types, engines, and rules."""
    declared = odcs.get("quality")
    if declared is None:
        return ()
    if not isinstance(declared, list):
        raise UnsupportedQualityMappingError(f"{table.contract_id}: quality must be a list")
    names = {column.name for column in table.columns}
    rules: list[QualityRule] = []
    for index, item in enumerate(declared):
        if not isinstance(item, dict):
            raise UnsupportedQualityMappingError(
                f"{table.contract_id}: quality[{index}] must be a mapping"
            )
        rules.append(_accepted_rule(table, item, names))
    return tuple(rules)
