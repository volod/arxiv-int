"""Deterministic offline language identification over bounded text samples."""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.resources.paths import language_root

UNKNOWN = "und"
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_CYRILLIC = (0x0400, 0x04FF)
_MARKER_WEIGHT = 3.0
_STOPWORD_WEIGHT = 10.0


@dataclass(frozen=True, slots=True)
class LanguageProfile:
    """One reviewed language signature loaded from the packaged profiles."""

    code: str
    script: str
    markers: frozenset[str]
    stopwords: frozenset[str]


@dataclass(frozen=True, slots=True)
class LanguageResult:
    """Detected language with its normalized confidence share."""

    language: str
    confidence: float


@lru_cache(maxsize=4)
def load_profiles(root: Path) -> tuple[tuple[LanguageProfile, ...], str]:
    """Load the packaged profiles and their reviewed fingerprint."""
    path = root / "profiles.json"
    payload = json.loads(path.read_text(encoding="ascii"))
    profiles = tuple(
        LanguageProfile(
            code,
            str(spec["scripts"][0]),
            frozenset(str(spec["markers"])),
            frozenset(str(word) for word in spec["stopwords"]),
        )
        for code, spec in sorted(payload["languages"].items())
    )
    return profiles, hash_file(path)[0]


def profile_fingerprint(project_root: Path | None = None) -> str:
    """Return the identity of the reviewed language profiles in use."""
    return load_profiles(language_root(project_root))[1]


def _script(text: str) -> tuple[int, int]:
    cyrillic = sum(1 for char in text if _CYRILLIC[0] <= ord(char) <= _CYRILLIC[1])
    latin = sum(1 for char in text if char.isascii() and char.isalpha())
    return cyrillic, latin


def detect_language(
    text: str,
    *,
    sample_chars: int,
    min_letters: int,
    min_confidence: float,
    project_root: Path | None = None,
) -> LanguageResult:
    """Score a bounded sample against every reviewed profile and pick the best."""
    sample = text[:sample_chars]
    cyrillic, latin = _script(sample)
    if cyrillic + latin < min_letters:
        return LanguageResult(UNKNOWN, 0.0)
    words = _WORD.findall(sample.lower())
    if not words:
        return LanguageResult(UNKNOWN, 0.0)
    unique = set(words)
    scores: dict[str, float] = {}
    for profile in load_profiles(language_root(project_root))[0]:
        share = (cyrillic if profile.script == "cyrillic" else latin) / (cyrillic + latin)
        markers = sum(1 for char in sample if char in profile.markers)
        stopwords = sum(1 for word in unique if word in profile.stopwords)
        scores[profile.code] = share * (
            1.0
            + _MARKER_WEIGHT * (markers / len(sample))
            + _STOPWORD_WEIGHT * (stopwords / len(unique))
        )
    total = sum(scores.values())
    if total <= 0.0:
        return LanguageResult(UNKNOWN, 0.0)
    best = max(sorted(scores), key=lambda code: scores[code])
    confidence = round(scores[best] / total, 6)
    if confidence < min_confidence:
        return LanguageResult(UNKNOWN, confidence)
    return LanguageResult(best, confidence)
