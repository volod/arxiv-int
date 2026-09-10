"""Streamed MinHash sketches that never materialize the full shingle set.

Each shingle updates every sketch register through a distinct multiply-add
permutation, so Jaccard estimates stay accurate for near-duplicates and editions
without a second pass or an in-memory shingle table.
"""

import hashlib
from collections.abc import Iterator, Sequence

_MASK = (1 << 64) - 1
_EMPTY = _MASK
_ODD_GOLDEN = 0x9E3779B97F4A7C15
_MIX = 0xBF58476D1CE4E5B9


def tokens(text: str, limit: int) -> list[str]:
    """Split one whitespace-collapsed search view into bounded word tokens."""
    if limit <= 0:
        raise ValueError("token limit must be positive")
    return [token for token in text.split(" ", limit)[:limit] if token]


def shingles(words: Sequence[str], size: int) -> Iterator[int]:
    """Yield the 64-bit hash of every contiguous word shingle in order."""
    if size < 1:
        raise ValueError("shingle size must be positive")
    if not words:
        return
    if len(words) <= size:
        yield _hash(" ".join(words))
        return
    for start in range(len(words) - size + 1):
        yield _hash(" ".join(words[start : start + size]))


def sketch(hashes: Iterator[int], bins: int) -> tuple[tuple[int, ...], int]:
    """Build one densified minimum-value sketch and report the shingles consumed."""
    if bins < 1:
        raise ValueError("sketch bins must be positive")
    signature = [_EMPTY] * bins
    consumed = 0
    for value in hashes:
        consumed += 1
        for index in range(bins):
            candidate = _permute(value, index)
            if candidate < signature[index]:
                signature[index] = candidate
    return _densify(signature, bins), consumed


def bands(signature: tuple[int, ...], rows: int) -> tuple[int, ...]:
    """Fold the sketch into locality-sensitive band keys of ``rows`` positions."""
    if len(signature) % rows:
        raise ValueError("signature length must be a multiple of the band row count")
    keys: list[int] = []
    for index in range(0, len(signature), rows):
        payload = ",".join(str(value) for value in signature[index : index + rows])
        keys.append(_hash(f"{index}:{payload}"))
    return tuple(keys)


def similarity(left: Sequence[int], right: Sequence[int]) -> float:
    """Estimate Jaccard similarity as the share of agreeing sketch positions."""
    if len(left) != len(right) or not left:
        raise ValueError("sketches must share one non-empty length")
    matches = sum(1 for a, b in zip(left, right, strict=True) if a == b)
    return matches / len(left)


def _permute(value: int, index: int) -> int:
    coefficient = (_ODD_GOLDEN + (index << 1) + 1) & _MASK
    return (value * coefficient + (index * _MIX)) & _MASK


def _densify(signature: list[int], bins: int) -> tuple[int, ...]:
    if all(value == _EMPTY for value in signature):
        return tuple(signature)
    filled = list(signature)
    for index in range(bins):
        if signature[index] != _EMPTY:
            continue
        for step in range(1, bins):
            donor = signature[(index + step) % bins]
            if donor != _EMPTY:
                filled[index] = (donor + step) & _MASK
                break
    return tuple(filled)


def _hash(value: str) -> int:
    return int.from_bytes(hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest(), "big")
