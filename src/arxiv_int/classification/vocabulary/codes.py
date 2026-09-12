"""Hierarchical taxonomy codes: two digits per level, dot separated (``04``, ``04.02``, ``04.02.01``).

The code carries the hierarchy, so a class's parent is its code without the last segment and its
depth is the number of segments.
"""

import re

CODE_PATTERN = re.compile(r"\d{2}(?:\.\d{2})*")
KIND_DOMAIN = "domain"
KIND_FIELD = "field"
KIND_SUBFIELD = "subfield"
KIND_BY_DEPTH = {1: KIND_DOMAIN, 2: KIND_FIELD, 3: KIND_SUBFIELD}


class CodeError(ValueError):
    """Raised for text that is not a taxonomy code."""


def require_code(text: str) -> str:
    """Return text when it is a well-formed code."""
    if CODE_PATTERN.fullmatch(text) is None:
        raise CodeError(f"taxonomy code must be two-digit dot-separated segments: {text!r}")
    return text


def code_depth(code: str) -> int:
    """Return 1 for a domain code and one more per segment."""
    return require_code(code).count(".") + 1


def parent_code(code: str) -> str | None:
    """Return the code without its last segment, or ``None`` for a domain."""
    require_code(code)
    return code.rsplit(".", 1)[0] if "." in code else None


def kind_for(code: str) -> str:
    """Return the structural kind implied by a code's depth."""
    depth = code_depth(code)
    try:
        return KIND_BY_DEPTH[depth]
    except KeyError as error:
        raise CodeError(f"taxonomy code {code} is deeper than a subfield") from error
