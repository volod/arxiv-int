"""Reversible, path-safe ASCII tokens and short slugs for scheme classes.

A token is a single directory-name component that decodes back to its class id. Only lowercase
ASCII letters, digits, ``.`` and ``-`` pass through; every other byte (including ``_`` itself and a
trailing ``.``) becomes ``_hh``. Namespace prefixes keep taxonomy (``t``), extension (``x-``), and
outcome (``_``) tokens disjoint, and also keep tokens clear of hidden or reserved device names.
"""

import re
import unicodedata

from arxiv_int.classification.vocabulary.outcomes import (
    EXCEPTIONAL_OUTCOMES,
    EXTENSION_PREFIX,
    NAMESPACE_EXTENSION,
    NAMESPACE_OUTCOME,
    TAXONOMY_PREFIX,
    namespace_of,
)

TOKEN_TAXONOMY_PREFIX = "t"
TOKEN_EXTENSION_PREFIX = "x-"
TOKEN_OUTCOME_PREFIX = "_"
_SAFE = frozenset("0123456789abcdefghijklmnopqrstuvwxyz.-")
_ESCAPE = re.compile(r"_([0-9a-f]{2})")
_SLUG_BREAK = re.compile(r"[^a-z0-9]+")


class TokenError(ValueError):
    """Raised for a token that does not decode to a class id."""


def encode_component(text: str) -> str:
    """Encode text into the safe alphabet; the result never ends with ``.``."""
    encoded: list[str] = []
    raw = text.encode("utf-8")
    for index, byte in enumerate(raw):
        character = chr(byte)
        trailing_dot = character == "." and index == len(raw) - 1
        if character in _SAFE and not trailing_dot:
            encoded.append(character)
        else:
            encoded.append(f"_{byte:02x}")
    return "".join(encoded)


def decode_component(token: str) -> str:
    """Invert :func:`encode_component`; refuse bytes that should have been escaped."""
    output = bytearray()
    position = 0
    while position < len(token):
        if token[position] == "_":
            match = _ESCAPE.match(token, position)
            if match is None:
                raise TokenError(f"malformed escape in token {token!r}")
            output.append(int(match.group(1), 16))
            position = match.end()
            continue
        if token[position] not in _SAFE:
            raise TokenError(f"unsafe character in token {token!r}")
        output.append(ord(token[position]))
        position += 1
    decoded = output.decode("utf-8")
    if encode_component(decoded) != token:
        raise TokenError(f"token {token!r} is not in canonical form")
    return decoded


def class_token(class_id: str) -> str:
    """Return the path-safe token for one class id."""
    namespace = namespace_of(class_id)
    if namespace == NAMESPACE_OUTCOME:
        return f"{TOKEN_OUTCOME_PREFIX}{class_id}"
    if namespace == NAMESPACE_EXTENSION:
        return f"{TOKEN_EXTENSION_PREFIX}{encode_component(class_id[len(EXTENSION_PREFIX) :])}"
    return f"{TOKEN_TAXONOMY_PREFIX}{encode_component(class_id[len(TAXONOMY_PREFIX) :])}"


def class_id_from_token(token: str) -> str:
    """Decode a token back to its class id."""
    if token.startswith(TOKEN_OUTCOME_PREFIX):
        outcome = token[len(TOKEN_OUTCOME_PREFIX) :]
        if outcome not in EXCEPTIONAL_OUTCOMES:
            raise TokenError(f"unknown outcome token {token!r}")
        return outcome
    if token.startswith(TOKEN_EXTENSION_PREFIX):
        return f"{EXTENSION_PREFIX}{decode_component(token[len(TOKEN_EXTENSION_PREFIX) :])}"
    if token.startswith(TOKEN_TAXONOMY_PREFIX) and len(token) > len(TOKEN_TAXONOMY_PREFIX):
        return f"{TAXONOMY_PREFIX}{decode_component(token[len(TOKEN_TAXONOMY_PREFIX) :])}"
    raise TokenError(f"token {token!r} has no namespace prefix")


def ascii_slug(caption: str, max_bytes: int) -> str:
    """Return a lowercase ASCII slug of a caption, cut at a word boundary within ``max_bytes``."""
    folded = unicodedata.normalize("NFKD", caption).encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_BREAK.sub("-", folded.lower()).strip("-")
    if len(slug) <= max_bytes:
        return slug
    cut = slug[: max_bytes + 1]
    boundary = cut.rfind("-")
    return (cut[:boundary] if boundary > 0 else slug[:max_bytes]).strip("-")
