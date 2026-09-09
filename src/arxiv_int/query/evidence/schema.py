"""Load contract columns and parse portable rows without SQLAlchemy."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from arxiv_int.contracts.catalog.normalize import (
    PARTITION_KEY_ORIGIN,
    NormalizedColumn,
    NormalizedTable,
    normalize_contract,
)
from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.interfaces.tokens import require_relative_path, require_token
from arxiv_int.resources.paths import contracts_root

DOCUMENTS_CONTRACT = "documents"
OCCURRENCES_CONTRACT = "source-occurrences"
PATH_EVENTS_CONTRACT = "document-path-events"
PATH_EVENT_KINDS = frozenset({"initial", "rename", "copy", "import"})
FIXTURE_GENERATION_ID = "fixture"
DEFAULT_CONTRACT_VERSION = "1.0.0"

_TABLES: dict[str, NormalizedTable] = {}


class ContractRowError(ValueError):
    """Raised when a portable row does not match its ODCS contract."""


@dataclass(frozen=True, slots=True)
class ContractRow:
    """One portable row whose keys are a registered contract's columns."""

    contract_id: str
    values: Mapping[str, str]

    def get(self, column: str) -> str:
        """Return one contract column, or empty when the field was omitted."""
        names = column_names(self.contract_id)
        if column not in names:
            raise ContractRowError(f"{self.contract_id} has no column {column!r}")
        return self.values.get(column, "")


def normalized_table(contract_id: str) -> NormalizedTable:
    """Return the cached normalized table for one registered contract."""
    cached = _TABLES.get(contract_id)
    if cached is not None:
        return cached
    registry = FileRegistry(contracts_root())
    table = normalize_contract(registry.load_odcs(contract_id), contract_id)
    _TABLES[contract_id] = table
    return table


def column_names(contract_id: str) -> frozenset[str]:
    """Return physical column names for one contract, including generated keys."""
    return frozenset(column.name for column in normalized_table(contract_id).columns)


def parse_row(contract_id: str, raw: Mapping[str, Any]) -> ContractRow:
    """Validate one JSON object against the named contract and return a row."""
    table = normalized_table(contract_id)
    _reject_unknown_fields(contract_id, raw, table)
    values = _parse_present_columns(contract_id, table, raw)
    _validate_row(contract_id, values)
    return ContractRow(contract_id, MappingProxyType(values))


def serialize_row(row: ContractRow) -> dict[str, str]:
    """Return contract columns present on one portable row."""
    return {key: row.values[key] for key in sorted(row.values)}


def occurrence_identity(row: ContractRow) -> str:
    """Return the stable occurrence token used by path events."""
    token = row.get("occurrence_id")
    if token:
        return token
    return f"{row.get('silo_id')}:{row.get('relative_path')}:{row.get('scan_id')}"


def occurrence_physical_path(row: ContractRow) -> str:
    """Return the silo-relative file that actually exists on disk."""
    return row.get("container_path") or row.get("relative_path")


def occurrence_is_member(row: ContractRow) -> bool:
    """Report whether this occurrence is a virtual container member."""
    return bool(row.get("member_path"))


def _reject_unknown_fields(
    contract_id: str, raw: Mapping[str, Any], table: NormalizedTable
) -> None:
    allowed = {column.name for column in table.columns}
    unknown = sorted(str(key) for key in raw if str(key) not in allowed)
    if unknown:
        raise ContractRowError(f"{contract_id} has unknown field(s): {', '.join(unknown)}")


def _parse_present_columns(
    contract_id: str, table: NormalizedTable, raw: Mapping[str, Any]
) -> dict[str, str]:
    values: dict[str, str] = {}
    for column in table.columns:
        text = _column_text(contract_id, column, raw)
        if text:
            values[column.name] = text
    return values


def _column_text(contract_id: str, column: NormalizedColumn, raw: Mapping[str, Any]) -> str:
    if column.name not in raw:
        _require_present(contract_id, column)
        return ""
    text = _cell_text(raw[column.name], contract_id, column.name)
    if not text:
        _require_present(contract_id, column)
    return text


def _require_present(contract_id: str, column: NormalizedColumn) -> None:
    if not column.nullable and column.origin != PARTITION_KEY_ORIGIN:
        raise ContractRowError(f"{contract_id} is missing required field {column.name!r}")


def _cell_text(value: object, contract_id: str, column: str) -> str:
    if value is None:
        return ""
    if isinstance(value, (bool, dict, list)):
        raise ContractRowError(f"{contract_id} field {column!r} must be a scalar JSON value")
    return str(value).strip()


def _optional_token(values: Mapping[str, str], name: str) -> None:
    text = values.get(name, "")
    if text:
        require_token(text, name)


def _optional_relative_path(values: Mapping[str, str], name: str) -> None:
    text = values.get(name, "")
    if text:
        require_relative_path(text, name)


def _validate_path_event(values: Mapping[str, str]) -> None:
    kind = values.get("kind", "")
    if kind not in PATH_EVENT_KINDS:
        raise ContractRowError(f"unknown path-event kind {kind!r}")
    require_token(values.get("document_id", ""), "document_id")
    require_token(values.get("silo_id", ""), "silo_id")
    require_token(values.get("content_hash", ""), "content_hash")
    require_relative_path(values.get("relative_path", ""), "relative_path")
    _optional_relative_path(values, "previous_relative_path")
    _optional_token(values, "occurrence_id")


def _validate_document(values: Mapping[str, str]) -> None:
    require_token(values.get("document_id", ""), "document_id")
    _optional_token(values, "content_hash")


def _validate_occurrence(values: Mapping[str, str]) -> None:
    _optional_token(values, "silo_id")
    _optional_relative_path(values, "relative_path")
    _optional_token(values, "scan_id")
    _optional_relative_path(values, "container_path")
    _optional_relative_path(values, "member_path")


_ROW_VALIDATORS: dict[str, Callable[[Mapping[str, str]], None]] = {
    PATH_EVENTS_CONTRACT: _validate_path_event,
    DOCUMENTS_CONTRACT: _validate_document,
    OCCURRENCES_CONTRACT: _validate_occurrence,
}


def _validate_row(contract_id: str, values: Mapping[str, str]) -> None:
    table = normalized_table(contract_id)
    for column in table.columns:
        if column.primary_key_position is not None:
            require_token(values.get(column.name, ""), column.name)
    validator = _ROW_VALIDATORS.get(contract_id)
    if validator is not None:
        validator(values)
