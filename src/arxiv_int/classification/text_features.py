"""Dependency-free Unicode word and character features for classification."""

import re
from collections import Counter
from collections.abc import Iterable

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_STOPWORDS = frozenset({"and", "for", "of", "the", "и", "для", "та", "й"})


def words(text: str) -> tuple[str, ...]:
    """Return normalized Unicode word tokens without language-specific downloads."""
    return tuple(
        token
        for match in _WORD.finditer(text)
        if (token := match.group(0).casefold()) not in _STOPWORDS
    )


def feature_counts(tokens: Iterable[str]) -> Counter[str]:
    """Return word and padded character-trigram counts for normalized tokens."""
    found: Counter[str] = Counter()
    for token in tokens:
        if len(token) > 1:
            found[f"w:{token}"] += 1
        if len(token) >= 5:
            padded = f"^{token}$"
            found.update(f"c:{padded[index : index + 3]}" for index in range(len(padded) - 2))
    return found
