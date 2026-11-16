"""Pure, bounded query-text transforms used by the declared query profiles.

Every function returns a new query string (or ``None`` when nothing applies) and
never touches stored source text. ``*_v1`` functions keep the accepted
``russian-safe-v1`` behavior byte-for-byte; the others implement the guarded
second-opinion candidate.
"""

import re

_CYRILLIC = re.compile(r"[\u0400-\u04ff]")
_LATIN = re.compile(r"[a-z]")
_SYNTAX = re.compile(r"(^|\s)[+-]\S|[:\"()\[\]{}^~*?\\]|\b(AND|OR|NOT)\b")
_CONSONANTS = (
    "\u0431\u0432\u0433\u0434\u0436\u0437\u043a\u043b\u043c\u043d"
    "\u043f\u0440\u0441\u0442\u0444\u0445\u0446\u0447\u0448\u0449"
)
# Productive fleeting-vowel endings only: -ets, -ok, -ek, -en', -el, -ol.
_FLEETING = re.compile(
    rf"^(.+[{_CONSONANTS}])(?:\u0435(\u0446)()|[\u043e\u0435](\u043a)()"
    rf"|\u0435(\u043d)(\u044c)|[\u0435\u043e](\u043b)())$"
)
_KEYBOARD_FROM = "qwertyuiop[]asdfghjkl;'zxcvbnm,."
_KEYBOARD_TO = (
    "\u0439\u0446\u0443\u043a\u0435\u043d\u0433\u0448\u0449\u0437\u0445\u044a"
    "\u0444\u044b\u0432\u0430\u043f\u0440\u043e\u043b\u0434\u0436\u044d"
    "\u044f\u0447\u0441\u043c\u0438\u0442\u044c\u0431\u044e"
)
_KEYBOARD = str.maketrans(_KEYBOARD_FROM, _KEYBOARD_TO)
_LAYOUT_KEYS = frozenset("[];',.")
_LOWER_LOOKALIKES = "acekmoptxy"
_LOWER_CYRILLIC = "\u0430\u0441\u0435\u043a\u043c\u043e\u0440\u0442\u0445\u0443"
_UPPER_LOOKALIKES = "ABCEHKMOPTXY"
_UPPER_CYRILLIC = "\u0410\u0412\u0421\u0415\u041d\u041a\u041c\u041e\u0420\u0422\u0425\u0423"
_V1_HOMOGLYPHS = str.maketrans(_LOWER_LOOKALIKES, _LOWER_CYRILLIC)
_TO_CYRILLIC = str.maketrans(
    _LOWER_LOOKALIKES + _UPPER_LOOKALIKES, _LOWER_CYRILLIC + _UPPER_CYRILLIC
)
_TO_LATIN = str.maketrans(_LOWER_CYRILLIC + _UPPER_CYRILLIC, _LOWER_LOOKALIKES + _UPPER_LOOKALIKES)
_V1_TRANSLITERATION = (
    ("shch", "\u0449"), ("yo", "\u0451"), ("zh", "\u0436"), ("kh", "\u0445"),
    ("ts", "\u0446"), ("ch", "\u0447"), ("sh", "\u0448"), ("yu", "\u044e"),
    ("ya", "\u044f"), ("a", "\u0430"), ("b", "\u0431"), ("v", "\u0432"),
    ("g", "\u0433"), ("d", "\u0434"), ("e", "\u0435"), ("z", "\u0437"),
    ("i", "\u0438"), ("j", "\u0439"), ("k", "\u043a"), ("l", "\u043b"),
    ("m", "\u043c"), ("n", "\u043d"), ("o", "\u043e"), ("p", "\u043f"),
    ("r", "\u0440"), ("s", "\u0441"), ("t", "\u0442"), ("u", "\u0443"),
    ("f", "\u0444"), ("h", "\u0445"), ("c", "\u0446"), ("y", "\u044b"),
)  # fmt: skip
# Longest-first digraphs, then word-final glides; bare c/e/y are positional below.
_V2_DIGRAPHS = (
    ("shch", "\u0449"), ("sch", "\u0449"), ("zh", "\u0436"), ("kh", "\u0445"),
    ("ts", "\u0446"), ("tz", "\u0446"), ("ch", "\u0447"), ("sh", "\u0448"),
    ("yu", "\u044e"), ("ju", "\u044e"), ("ya", "\u044f"), ("ja", "\u044f"),
    ("yo", "\u0451"), ("jo", "\u0451"), ("ye", "\u0435"), ("je", "\u0435"),
    ("ck", "\u043a"), ("ph", "\u0444"), ("x", "\u043a\u0441"), ("w", "\u0432"),
    ("q", "\u043a"), ("'", "\u044c"),
)  # fmt: skip
_V2_ENDINGS = (
    ("iy", "\u0438\u0439"), ("yy", "\u044b\u0439"),
    ("oy", "\u043e\u0439"), ("ey", "\u0435\u0439"), ("ay", "\u0430\u0439"),
    ("uy", "\u0443\u0439"),
)  # fmt: skip
_V2_SINGLE = dict(zip("abvgdzijklmnoprstufh", (
    "\u0430\u0431\u0432\u0433\u0434\u0437\u0438\u0439\u043a\u043b"
    "\u043c\u043d\u043e\u043f\u0440\u0441\u0442\u0443\u0444\u0445"
), strict=True))  # fmt: skip
_LATIN_VOWELS = "aeiouy"


def only_latin_letters(text: str) -> bool:
    """Return whether every letter is ASCII Latin (and at least one letter exists)."""
    letters = [char for char in text.casefold() if char.isalpha()]
    return bool(letters) and all("a" <= char <= "z" for char in letters)


def has_query_syntax(text: str) -> bool:
    """Return whether the text uses field, phrase, grouping, prefix, or boolean syntax."""
    return bool(_SYNTAX.search(text))


def is_layout_artifact(text: str) -> bool:
    """Return whether the only query syntax is punctuation a Russian layout would produce.

    Cyrillic ``\u0445``, ``\u044a``, ``\u0436`` and ``\u044d`` sit on the Latin ``[``, ``]``,
    ``;`` and ``'`` keys, so a wrong-layout word reads as query syntax. Deliberate field, phrase,
    grouping, prefix or boolean syntax uses characters the layout never emits and is left alone.
    """
    if not only_latin_letters(text) or not has_query_syntax(text):
        return False
    return not has_query_syntax("".join(char for char in text if char not in _LAYOUT_KEYS))


def keyboard_v1(text: str) -> str | None:
    """Map Latin keys typed on a Russian layout to the intended Cyrillic letters."""
    return text.casefold().translate(_KEYBOARD) if only_latin_letters(text) else None


def transliterate_v1(text: str) -> str | None:
    """Apply the accepted, context-free Latin-to-Cyrillic table."""
    if not only_latin_letters(text):
        return None
    output = text.casefold()
    for latin, cyrillic in _V1_TRANSLITERATION:
        output = output.replace(latin, cyrillic)
    return output


def homoglyphs_v1(text: str) -> str | None:
    """Translate the whole casefolded query when it mixes Cyrillic and Latin letters."""
    if _CYRILLIC.search(text) and _LATIN.search(text.casefold()):
        return text.casefold().translate(_V1_HOMOGLYPHS)
    return None


def transliterate_v2(text: str) -> tuple[str, ...]:
    """Positional transliteration of an all-Latin query; drops outputs with residual Latin."""
    if not only_latin_letters(text):
        return ()
    words = text.casefold().split()
    initial = [_transliterate_word(word, initial_e="\u044d") for word in words]
    plain = [_transliterate_word(word, initial_e="\u0435") for word in words]
    variants = (" ".join(initial), " ".join(plain))
    return tuple(item for item in dict.fromkeys(variants) if not _LATIN.search(item))


def homoglyph_tokens(text: str) -> str | None:
    """Repair mixed-script tokens toward their majority script, and cross identifier codes."""
    changed = False
    output = []
    for token in text.split():
        repaired = _repair_token(token)
        changed = changed or repaired != token
        output.append(repaired)
    return " ".join(output) if changed else None


def fleeting_vowel(text: str) -> str | None:
    """Add the genitive stem of nominative nouns with a fleeting e/o (a bounded probe)."""
    changed = False
    output = []
    for token in text.split():
        folded = token.casefold().replace("\u0451", "\u0435")
        match = _FLEETING.match(folded) if not _LATIN.search(folded) else None
        if match is None or not _CYRILLIC.search(folded):
            output.append(token)
            continue
        stem, *endings = match.groups()
        final, soft = next((endings[i], endings[i + 1]) for i in range(0, 8, 2) if endings[i])
        output.append(stem + final + ("\u044f" if soft else "\u0430"))
        changed = True
    return " ".join(output) if changed else None


def _transliterate_word(word: str, *, initial_e: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(word):
        rest = word[index:]
        ending = next((pair for pair in _V2_ENDINGS if rest == pair[0]), None)
        digraph = next((pair for pair in _V2_DIGRAPHS if rest.startswith(pair[0])), None)
        if ending is not None:
            output.append(ending[1])
            index += len(ending[0])
        elif digraph is not None:
            output.append(digraph[1])
            index += len(digraph[0])
        else:
            output.append(_positional(word, index, initial_e))
            index += 1
    return "".join(output)


def _positional(word: str, index: int, initial_e: str) -> str:
    char = word[index]
    following = word[index + 1] if index + 1 < len(word) else ""
    previous = word[index - 1] if index else ""
    if char == "c":
        return "\u0446" if following in "eiy" and following else "\u043a"
    if char == "e":
        return initial_e if index == 0 else "\u0435"
    if char == "y":
        return "\u0439" if previous and previous in _LATIN_VOWELS else "\u044b"
    return _V2_SINGLE.get(char, char)


def _repair_token(token: str) -> str:
    letters = [char for char in token if char.isalpha()]
    cyrillic = sum(1 for char in letters if _CYRILLIC.match(char))
    latin = sum(1 for char in letters if "a" <= char.casefold() <= "z")
    if cyrillic and latin:
        return token.translate(_TO_CYRILLIC if cyrillic >= latin else _TO_LATIN)
    if _is_code(token, letters):
        return _cross_code(token, letters)
    return token


def _is_code(token: str, letters: list[str]) -> bool:
    return (
        any(char.isdigit() for char in token)
        and bool(letters)
        and all(char.isupper() for char in letters)
    )


def _cross_code(token: str, letters: list[str]) -> str:
    if all(char in _UPPER_LOOKALIKES for char in letters):
        return token.translate(_TO_CYRILLIC)
    if all(char in _UPPER_CYRILLIC for char in letters):
        return token.translate(_TO_LATIN)
    return token
