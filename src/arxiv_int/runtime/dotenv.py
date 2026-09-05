"""Minimal dotenv reader for dependency-free runtime bootstrap."""

import re
from pathlib import Path


class DotenvError(ValueError):
    """A dotenv file contains a malformed assignment."""


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
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            raise DotenvError(f"{path}:{line_number}: expected NAME=value")
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[name] = value
    return values
