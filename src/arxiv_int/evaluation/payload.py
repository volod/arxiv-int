"""Narrow JSON payload helpers for scoring frozen evaluation objects."""

from collections.abc import Mapping


def as_str(value: object, default: str = "") -> str:
    """Return a string or the default."""
    return value if isinstance(value, str) else default


def as_int(value: object, default: int = 0) -> int:
    """Return a non-bool integer or the default."""
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def as_float(value: object, default: float = 0.0) -> float:
    """Return a finite numeric value or the default."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def as_bool(value: object) -> bool:
    """Return a boolean, treating missing values as false."""
    return bool(value)


def as_items(value: object) -> tuple[object, ...]:
    """Return a tuple of items from a JSON array."""
    if isinstance(value, list):
        return tuple(value)
    return ()


def as_maps(value: object) -> tuple[Mapping[str, object], ...]:
    """Return object rows from a JSON array."""
    return tuple(item for item in as_items(value) if isinstance(item, dict))


def as_strings(value: object) -> tuple[str, ...]:
    """Return string rows from a JSON array."""
    return tuple(str(item) for item in as_items(value))


def as_string_rows(value: object) -> list[tuple[str, ...]]:
    """Return nested string rows from a JSON array of arrays."""
    rows: list[tuple[str, ...]] = []
    for item in as_items(value):
        if isinstance(item, (list, tuple)):
            rows.append(tuple(str(cell) for cell in item))
    return rows
