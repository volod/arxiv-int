"""Bounded query-only normalization for the selected Russian lexical profile."""

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.resources.paths import configs_root

LITERAL_QUERY_PROFILE = "literal-v1"
SELECTED_QUERY_PROFILE = "russian-safe-v1"
MAX_QUERY_VARIANTS = 5
_SPACE = re.compile(r"\s+")
_CYRILLIC = re.compile(r"[\u0400-\u04ff]")
_LATIN = re.compile(r"[a-z]")
_KEYBOARD_FROM = "qwertyuiop[]asdfghjkl;'zxcvbnm,."
_KEYBOARD_TO = "\u0439\u0446\u0443\u043a\u0435\u043d\u0433\u0448\u0449\u0437\u0445\u044a\u0444\u044b\u0432\u0430\u043f\u0440\u043e\u043b\u0434\u0436\u044d\u044f\u0447\u0441\u043c\u0438\u0442\u044c\u0431\u044e"
_KEYBOARD = str.maketrans(_KEYBOARD_FROM, _KEYBOARD_TO)
_HOMOGLYPHS = str.maketrans(
    {
        "a": "\u0430",
        "c": "\u0441",
        "e": "\u0435",
        "k": "\u043a",
        "m": "\u043c",
        "o": "\u043e",
        "p": "\u0440",
        "t": "\u0442",
        "x": "\u0445",
        "y": "\u0443",
    }
)
_TRANSLITERATION = (
    ("shch", "\u0449"),
    ("yo", "\u0451"),
    ("zh", "\u0436"),
    ("kh", "\u0445"),
    ("ts", "\u0446"),
    ("ch", "\u0447"),
    ("sh", "\u0448"),
    ("yu", "\u044e"),
    ("ya", "\u044f"),
    ("a", "\u0430"),
    ("b", "\u0431"),
    ("v", "\u0432"),
    ("g", "\u0433"),
    ("d", "\u0434"),
    ("e", "\u0435"),
    ("z", "\u0437"),
    ("i", "\u0438"),
    ("j", "\u0439"),
    ("k", "\u043a"),
    ("l", "\u043b"),
    ("m", "\u043c"),
    ("n", "\u043d"),
    ("o", "\u043e"),
    ("p", "\u043f"),
    ("r", "\u0440"),
    ("s", "\u0441"),
    ("t", "\u0442"),
    ("u", "\u0443"),
    ("f", "\u0444"),
    ("h", "\u0445"),
    ("c", "\u0446"),
    ("y", "\u044b"),
)


@dataclass(frozen=True, slots=True)
class QueryProfile:
    """One declared set of bounded query transformations."""

    profile_id: str
    aliases: bool
    homoglyphs: bool
    keyboard_layout: bool
    transliteration: bool
    unicode_nfc: bool


@dataclass(frozen=True, slots=True)
class QueryPolicy:
    """Reviewed query profiles, aliases, and their file fingerprint."""

    profiles: dict[str, QueryProfile]
    aliases: dict[str, tuple[str, ...]]
    default_profile: str
    fingerprint: str


@lru_cache(maxsize=1)
def load_query_policy() -> QueryPolicy:
    """Load the packaged query policy and return its immutable identity."""
    path = configs_root() / "retrieval" / "query-normalization.json"
    payload = json.loads(path.read_text(encoding="ascii"))
    profiles = {
        profile_id: QueryProfile(profile_id=profile_id, **settings)
        for profile_id, settings in payload["profiles"].items()
    }
    default = str(payload["default_profile"])
    if default not in profiles:
        raise ValueError(f"unknown default query profile {default!r}")
    aliases = {
        _base(key): tuple(_base(str(value)) for value in values)
        for key, values in payload["aliases"].items()
    }
    return QueryPolicy(profiles, aliases, default, hash_file(path)[0])


def query_variants(text: str, *, profile_id: str = SELECTED_QUERY_PROFILE) -> tuple[str, ...]:
    """Return bounded search variants without changing stored source evidence."""
    policy = load_query_policy()
    try:
        profile = policy.profiles[profile_id]
    except KeyError as error:
        raise ValueError(f"unknown query profile {profile_id!r}") from error
    base = _base(text) if profile.unicode_nfc else text.strip()
    variants = [base]
    if profile.aliases:
        variants.extend(policy.aliases.get(base.casefold(), ()))
    if profile.homoglyphs and _CYRILLIC.search(base) and _LATIN.search(base.casefold()):
        variants.append(base.casefold().translate(_HOMOGLYPHS))
    if profile.keyboard_layout and _only_latin_letters(base):
        variants.append(base.casefold().translate(_KEYBOARD))
    if profile.transliteration and _only_latin_letters(base):
        variants.append(_transliterate(base.casefold()))
    return tuple(dict.fromkeys(item for item in variants if item))[:MAX_QUERY_VARIANTS]


def query_policy_fingerprint() -> str:
    """Return the selected query policy file fingerprint."""
    return load_query_policy().fingerprint


def _base(text: str) -> str:
    return _SPACE.sub(" ", unicodedata.normalize("NFC", text).strip())


def _only_latin_letters(text: str) -> bool:
    letters = [char for char in text.casefold() if char.isalpha()]
    return bool(letters) and all("a" <= char <= "z" for char in letters)


def _transliterate(text: str) -> str:
    output = text
    for latin, cyrillic in _TRANSLITERATION:
        output = output.replace(latin, cyrillic)
    return output
