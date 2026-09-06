"""Minimal dotenv grammar and reference expansion for dependency-free bootstrap."""

import re
from collections.abc import Mapping
from pathlib import Path

PATH_SUFFIX = "_DIR"
_NAME = re.compile(r"[A-Z][A-Z0-9_]*")
_REFERENCE = re.compile(r"\$(?:\{([A-Z][A-Z0-9_]*)\}|([A-Z][A-Z0-9_]*))")


class DotenvError(ValueError):
    """A dotenv file or a variable reference cannot be resolved."""


def _unquote(value: str) -> str | None:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return None


def _value_of(raw_value: str) -> str:
    value = raw_value.strip()
    unquoted = _unquote(value)
    if unquoted is None and " #" in value:
        value = value.split(" #", 1)[0].rstrip()
        unquoted = _unquote(value)
    return value if unquoted is None else unquoted


def read_dotenv(path: Path) -> dict[str, str]:
    """Read the small, shell-compatible KEY=VALUE subset used by this project."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, raw_value = line.partition("=")
        name = name.strip()
        if not separator or not _NAME.fullmatch(name):
            raise DotenvError(f"{path}:{line_number}: expected NAME=value")
        values[name] = _value_of(raw_value)
    return values


def _resolve(
    name: str, values: Mapping[str, str], resolved: dict[str, str], chain: tuple[str, ...]
) -> str:
    if name in resolved:
        return resolved[name]
    if name in chain:
        cycle = " -> ".join((*chain[chain.index(name) :], name))
        raise DotenvError(f"{name} references itself: {cycle}")
    value = values[name]
    if name.endswith(PATH_SUFFIX):
        value = _REFERENCE.sub(
            lambda match: _reference(name, match, values, resolved, (*chain, name)), value
        )
    resolved[name] = value
    return value


def _reference(
    name: str,
    match: re.Match[str],
    values: Mapping[str, str],
    resolved: dict[str, str],
    chain: tuple[str, ...],
) -> str:
    referenced = match.group(1) or match.group(2)
    if referenced not in values:
        raise DotenvError(f"{name} references missing {referenced}")
    value = _resolve(referenced, values, resolved, chain)
    if not value.strip():
        raise DotenvError(f"{name} references empty {referenced}")
    return value


def expand_references(values: Mapping[str, str]) -> dict[str, str]:
    """Expand ${NAME} and $NAME in path variables after precedence has been applied."""
    resolved: dict[str, str] = {}
    for name in values:
        _resolve(name, values, resolved, ())
    return resolved
