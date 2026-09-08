"""Shared checks for identity tokens and silo-relative POSIX paths."""

from collections.abc import Mapping
from types import MappingProxyType


def require_token(value: str, field: str) -> None:
    """Refuse empty, padded, or null-bearing identity strings."""
    if not value or value != value.strip():
        raise ValueError(f"{field} must be a non-empty token without surrounding whitespace")
    if "\x00" in value:
        raise ValueError(f"{field} must not contain a null byte")


def require_relative_path(value: str, field: str) -> None:
    """Refuse absolute, escaped, or empty silo-relative POSIX paths."""
    if not value or "\x00" in value:
        raise ValueError(f"{field} must be a non-empty silo-relative POSIX path")
    if value.startswith("/") or "\\" in value:
        raise ValueError(f"{field} must be a silo-relative POSIX path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{field} must not contain empty, '.' or '..' segments")


def freeze_str_mapping(values: Mapping[str, str]) -> Mapping[str, str]:
    """Return an immutable copy of a string mapping."""
    return MappingProxyType(dict(values))
