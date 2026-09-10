"""Reviewed abbreviation/alias expansion for declared query profiles."""

import re
from collections.abc import Mapping

AliasMap = Mapping[str, tuple[str, ...]]
_EDGE = re.compile(r"^[^\w]+|[^\w]+$")
_SHORT_KEY = 2
_STEM_SLACK = 3
_MIN_STEM = 4


def fold(text: str) -> str:
    """Casefold, fold yo to e, and strip edge punctuation from one token."""
    return _EDGE.sub("", text.casefold().replace("\u0451", "\u0435"))


def whole_query_aliases(base: str, aliases: AliasMap) -> tuple[str, ...]:
    """Return the accepted v1 behavior: expand only when the whole query is a key."""
    return tuple(aliases.get(base.casefold(), ()))


def token_aliases(base: str, aliases: AliasMap, *, phrase: bool) -> tuple[str, ...]:
    """Substitute keys found as tokens, and add keys for expansions found in the query."""
    tokens = base.split()
    folded = [fold(token) for token in tokens]
    variants: list[str] = []
    for key in sorted(aliases, key=lambda item: (-len(item.split()), item)):
        variants.extend(_forward(tokens, folded, key, aliases[key], phrase=phrase))
        variants.extend(_reverse(tokens, folded, key, aliases[key]))
    return tuple(dict.fromkeys(variants))


def _forward(
    tokens: list[str], folded: list[str], key: str, expansions: tuple[str, ...], *, phrase: bool
) -> list[str]:
    size = len(key.split())
    starts = [
        start
        for start in _windows(folded, key.split())
        if _typed_as_key(tokens[start : start + size], key)
    ]
    return [
        _replace(tokens, start, size, f'"{expansion}"' if phrase else expansion)
        for start in starts
        for expansion in expansions
    ]


def _reverse(
    tokens: list[str], folded: list[str], key: str, expansions: tuple[str, ...]
) -> list[str]:
    variants: list[str] = []
    for expansion in expansions:
        words = [fold(item) for item in expansion.split()]
        variants.extend(
            _replace(tokens, start, len(words), key.upper())
            for start in _stem_windows(folded, words)
        )
    return variants


def _typed_as_key(typed: list[str], key: str) -> bool:
    # Two-letter keys collide with ordinary words, so they must be typed in upper case.
    return len(key) > _SHORT_KEY or all(token.isupper() for token in typed)


def _windows(folded: list[str], key_tokens: list[str]) -> list[int]:
    size = len(key_tokens)
    return [
        start
        for start in range(len(folded) - size + 1)
        if folded[start : start + size] == key_tokens
    ]


def _stem_windows(folded: list[str], expansion: list[str]) -> list[int]:
    size = len(expansion)
    return [
        start
        for start in range(len(folded) - size + 1)
        if all(
            _stem_match(query, word)
            for query, word in zip(folded[start : start + size], expansion, strict=True)
        )
    ]


def _stem_match(query: str, word: str) -> bool:
    if len(word) < _MIN_STEM:
        return query == word
    return query.startswith(word[: max(_MIN_STEM, len(word) - _STEM_SLACK)])


def _replace(tokens: list[str], start: int, size: int, value: str) -> str:
    return " ".join([*tokens[:start], value, *tokens[start + size :]])
