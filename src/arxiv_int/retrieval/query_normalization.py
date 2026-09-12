"""Bounded query-only normalization for the declared Russian lexical profiles."""

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.resources.paths import configs_root
from arxiv_int.retrieval import query_transforms as transforms
from arxiv_int.retrieval.query_aliases import token_aliases, whole_query_aliases

LITERAL_QUERY_PROFILE = "literal-v1"
# Adopted by the second-opinion final run (record 0072); query-only, no reindex.
ACCEPTED_V1_QUERY_PROFILE = "russian-safe-v1"
SELECTED_QUERY_PROFILE = "russian-guarded-v2"
MAX_QUERY_VARIANTS = 5
# Edit-distance matching of shorter words matches too many unrelated terms.
FUZZY_MIN_CHARS = 5
_SPACE = re.compile(r"\s+")
_CHOICES = {
    "alias_binding": ("terms", "phrase"),
    "alias_scope": ("query", "token"),
    "homoglyph_scope": ("query", "token"),
    "transliteration_rules": ("v1", "v2"),
}


@dataclass(frozen=True, slots=True)
class QueryProfile:
    """One declared set of bounded query transformations.

    Defaults reproduce the accepted ``russian-safe-v1`` mechanics, so a profile
    only names the guarded behavior it opts into.
    """

    profile_id: str
    aliases: bool
    homoglyphs: bool
    keyboard_layout: bool
    transliteration: bool
    unicode_nfc: bool
    alias_set: str = "legacy-v1"
    alias_scope: str = "query"
    alias_binding: str = "terms"
    homoglyph_scope: str = "query"
    transliteration_rules: str = "v1"
    mechanical_fallback: bool = False
    fleeting_vowels: bool = False
    fuzzy_fallback: bool = False
    preserve_syntax: bool = False


@dataclass(frozen=True, slots=True)
class QueryPolicy:
    """Reviewed query profiles, alias dictionaries, and their file fingerprint."""

    profiles: dict[str, QueryProfile]
    alias_sets: dict[str, dict[str, tuple[str, ...]]]
    default_profile: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class QueryPlan:
    """Bounded variants: primary always runs; fallback and fuzzy run only on no hits.

    ``fuzzy`` holds the long-word text of each primary variant; every word of one text
    must match within the bounded edit distance. ``literal_primary`` marks a base the syntax
    guard held verbatim, so a later stage scores its readable variants alone.
    """

    profile_id: str
    base: str
    primary: tuple[str, ...]
    fallback: tuple[str, ...] = ()
    fuzzy: tuple[str, ...] = ()
    literal_primary: bool = False

    @property
    def variants(self) -> tuple[str, ...]:
        """Return every variant the plan may send, primary first."""
        return tuple(dict.fromkeys((*self.primary, *self.fallback)))


@lru_cache(maxsize=1)
def load_query_policy() -> QueryPolicy:
    """Load the packaged query policy and return its immutable identity."""
    path = configs_root() / "retrieval" / "query-normalization.json"
    payload = json.loads(path.read_text(encoding="ascii"))
    alias_sets = {
        name: {
            _base(key): tuple(_base(str(value)) for value in values)
            for key, values in entries.items()
        }
        for name, entries in payload["alias_sets"].items()
    }
    profiles = {
        profile_id: QueryProfile(profile_id=profile_id, **settings)
        for profile_id, settings in payload["profiles"].items()
    }
    default = str(payload["default_profile"])
    _validate(profiles, alias_sets, default)
    return QueryPolicy(profiles, alias_sets, default, hash_file(path)[0])


def query_plan(text: str, *, profile_id: str = SELECTED_QUERY_PROFILE) -> QueryPlan:
    """Return the bounded, staged variants for one query without changing source evidence."""
    policy = load_query_policy()
    try:
        profile = policy.profiles[profile_id]
    except KeyError as error:
        raise ValueError(f"unknown query profile {profile_id!r}") from error
    base = _base(text) if profile.unicode_nfc else text.strip()
    if profile.preserve_syntax and transforms.has_query_syntax(base):
        # A wrong-layout word is unparseable as written, so its mechanical reading stays
        # reachable as a fallback while the literal query keeps the primary stage.
        artifact = transforms.is_layout_artifact(base)
        rescue = _bounded(_mechanical(base, profile)) if artifact else ()
        return QueryPlan(profile_id, base, (base,), rescue, literal_primary=True)
    primary = [base, *_alias_variants(base, profile, policy)]
    primary.extend(_optional(_homoglyph(base, profile)))
    if profile.fleeting_vowels:
        primary.extend(_optional(transforms.fleeting_vowel(base)))
    mechanical = _mechanical(base, profile)
    if not profile.mechanical_fallback:
        primary.extend(mechanical)
    bounded = _bounded(primary)
    fallback = mechanical if profile.mechanical_fallback else []
    extra = tuple(item for item in _bounded(fallback) if item not in bounded)
    fuzzy = _fuzzy_texts(bounded) if profile.fuzzy_fallback else ()
    return QueryPlan(profile_id, base, bounded, extra, fuzzy)


def query_variants(text: str, *, profile_id: str = SELECTED_QUERY_PROFILE) -> tuple[str, ...]:
    """Return every bounded variant a profile may send, primary stage first."""
    return query_plan(text, profile_id=profile_id).variants


def query_policy_fingerprint() -> str:
    """Return the selected query policy file fingerprint."""
    return load_query_policy().fingerprint


def _alias_variants(base: str, profile: QueryProfile, policy: QueryPolicy) -> tuple[str, ...]:
    if not profile.aliases:
        return ()
    aliases = policy.alias_sets[profile.alias_set]
    if profile.alias_scope == "query":
        return whole_query_aliases(base, aliases)
    return token_aliases(base, aliases, phrase=profile.alias_binding == "phrase")


def _homoglyph(base: str, profile: QueryProfile) -> str | None:
    if not profile.homoglyphs:
        return None
    if profile.homoglyph_scope == "query":
        return transforms.homoglyphs_v1(base)
    return transforms.homoglyph_tokens(base)


def _mechanical(base: str, profile: QueryProfile) -> list[str]:
    variants: list[str] = []
    if profile.keyboard_layout:
        variants.extend(_optional(transforms.keyboard_v1(base)))
    if profile.transliteration:
        if profile.transliteration_rules == "v1":
            variants.extend(_optional(transforms.transliterate_v1(base)))
        else:
            variants.extend(transforms.transliterate_v2(base))
    return variants


def _fuzzy_texts(variants: tuple[str, ...]) -> tuple[str, ...]:
    texts = []
    for variant in variants:
        words = [word for word in variant.replace('"', " ").split() if len(word) >= FUZZY_MIN_CHARS]
        if words:
            texts.append(" ".join(words))
    return _bounded(texts)


def _optional(value: str | None) -> tuple[str, ...]:
    return (value,) if value else ()


def _bounded(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in values if item))[:MAX_QUERY_VARIANTS]


def _validate(
    profiles: dict[str, QueryProfile],
    alias_sets: dict[str, dict[str, tuple[str, ...]]],
    default: str,
) -> None:
    if default not in profiles:
        raise ValueError(f"unknown default query profile {default!r}")
    for profile in profiles.values():
        _validate_profile(profile, alias_sets)
    if any(_quoted(entries) for entries in alias_sets.values()):
        raise ValueError("alias dictionaries must not contain query phrase quotes")


def _validate_profile(
    profile: QueryProfile, alias_sets: dict[str, dict[str, tuple[str, ...]]]
) -> None:
    if profile.alias_set not in alias_sets:
        raise ValueError(f"profile {profile.profile_id!r} names unknown alias set")
    invalid = [name for name, allowed in _CHOICES.items() if getattr(profile, name) not in allowed]
    if invalid:
        raise ValueError(f"profile {profile.profile_id!r} has invalid {invalid[0]}")


def _quoted(entries: dict[str, tuple[str, ...]]) -> bool:
    return any('"' in text for key, values in entries.items() for text in (key, *values))


def _base(text: str) -> str:
    return _SPACE.sub(" ", unicodedata.normalize("NFC", text).strip())
