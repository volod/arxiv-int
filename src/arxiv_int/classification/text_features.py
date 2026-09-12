"""Dependency-free Unicode word and character features for classification."""

import re
from collections import Counter
from collections.abc import Iterable

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_STOPWORDS = frozenset({"and", "for", "of", "the", "и", "для", "та", "й"})


def word_spans(text: str) -> tuple[tuple[str, int, int], ...]:
    """Return each normalized token with the span of the characters that produced it.

    Offsets address ``text`` itself, not a casefolded copy, so a fold that changes
    length (for example ``\u00df`` to ``ss``) cannot shift a reported span.
    """
    return tuple(
        (token, match.start(), match.end())
        for match in _WORD.finditer(text)
        if (token := match.group(0).casefold()) not in _STOPWORDS
    )


def words(text: str) -> tuple[str, ...]:
    """Return normalized Unicode word tokens without language-specific downloads."""
    return tuple(token for token, _, _ in word_spans(text))


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
