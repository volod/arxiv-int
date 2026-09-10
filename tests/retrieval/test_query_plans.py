"""Guarded query plans stay bounded, staged, syntax-preserving, and query-only."""

import unicodedata
from typing import Any, cast

from sqlalchemy import Connection

from arxiv_int.retrieval.lexical import LexicalRequest, search
from arxiv_int.retrieval.projection import LexicalTarget
from arxiv_int.retrieval.query_normalization import (
    ACCEPTED_V1_QUERY_PROFILE,
    LITERAL_QUERY_PROFILE,
    MAX_QUERY_VARIANTS,
    load_query_policy,
    query_plan,
    query_variants,
)
from arxiv_int.retrieval.query_transforms import (
    fleeting_vowel,
    has_query_syntax,
    homoglyph_tokens,
    transliterate_v2,
)

GUARDED = "russian-guarded-v2"
ACCEPTED = ACCEPTED_V1_QUERY_PROFILE
TARGET = LexicalTarget("lexical:t", "t", "search.t", "t_bm25", 1, "c", "calibration")
LEP = "\u041b\u042d\u041f"
LEP_EXPANSION = (
    "\u043b\u0438\u043d\u0438\u044f \u044d\u043b\u0435\u043a\u0442\u0440\u043e"
    "\u043f\u0435\u0440\u0435\u0434\u0430\u0447\u0438"
)
INSPECTION = "\u043e\u0441\u043c\u043e\u0442\u0440"
PLC_WORDS = (
    "\u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0438\u0440\u0443\u0435\u043c\u044b\u0439 "
    "\u043b\u043e\u0433\u0438\u0447\u0435\u0441\u043a\u0438\u0439 "
    "\u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440"
)
PUMP = "\u043d\u0430\u0441\u043e\u0441"
MIXED_PUMP = "\u043d\u0430\u0441\u043e" + "c"


class _Recorder:
    """Minimal connection double that returns no rows and records every statement."""

    def __init__(self, rows: list[Any] | None = None) -> None:
        self.statements: list[tuple[str, dict[str, object]]] = []
        self.rows = rows or []

    def execute(self, statement: object, parameters: dict[str, object]) -> "_Recorder":
        self.statements.append((str(statement), parameters))
        return self

    def fetchall(self) -> list[Any]:
        return self.rows

    def scalar(self) -> int:
        return len(self.rows)


def test_every_declared_profile_names_a_known_alias_set() -> None:
    policy = load_query_policy()
    assert {profile.alias_set for profile in policy.profiles.values()} <= set(policy.alias_sets)
    assert policy.profiles[GUARDED].preserve_syntax


def test_guarded_aliases_bind_phrases_inside_queries_and_reverse_expansions() -> None:
    assert query_plan(f"{INSPECTION} {LEP}", profile_id=GUARDED).primary == (
        f"{INSPECTION} {LEP}",
        f'{INSPECTION} "{LEP_EXPANSION}"',
    )
    assert "\u041f\u041b\u041a" in query_plan(PLC_WORDS, profile_id=GUARDED).primary


def test_two_letter_abbreviations_expand_only_when_typed_in_upper_case() -> None:
    upper = query_plan(f"\u0422\u041e {PUMP}\u0430", profile_id=GUARDED).primary
    lower = query_plan(f"\u0442\u043e {PUMP}\u0430", profile_id=GUARDED).primary
    assert len(upper) == 2
    assert lower == (f"\u0442\u043e {PUMP}\u0430",)


def test_fuzzy_stage_covers_long_words_of_every_primary_variant() -> None:
    assert query_plan("\u0429\u041e", profile_id=GUARDED).fuzzy == ()
    battery = query_plan("\u0410\u041a\u0411", profile_id=GUARDED).fuzzy
    assert battery == (
        "\u0430\u043a\u043a\u0443\u043c\u0443\u043b\u044f\u0442\u043e\u0440\u043d\u0430\u044f "
        "\u0431\u0430\u0442\u0430\u0440\u0435\u044f",
    )
    assert query_plan("podshipnik", profile_id=ACCEPTED).fuzzy == ()


def test_query_syntax_disables_every_variant_and_fallback() -> None:
    for query in (f"{PUMP} -Modbus", "title:x", '"a b"', "a AND b", "(a OR b) c"):
        assert has_query_syntax(query)
        plan = query_plan(query, profile_id=GUARDED)
        assert plan.primary == (query,)
        assert not plan.fallback and not plan.fuzzy
    assert not has_query_syntax("RS-485 Wi-Fi TN-45/6")


def test_mechanical_variants_run_only_as_a_fallback() -> None:
    plan = query_plan("podshipnik", profile_id=GUARDED)
    assert plan.primary == ("podshipnik",)
    assert "\u043f\u043e\u0434\u0448\u0438\u043f\u043d\u0438\u043a" in plan.fallback
    assert plan.fuzzy
    assert len(plan.primary) <= MAX_QUERY_VARIANTS and len(plan.fallback) <= MAX_QUERY_VARIANTS


def test_homoglyph_repair_follows_the_token_majority_and_crosses_codes() -> None:
    assert homoglyph_tokens(f"M\u043edbus {MIXED_PUMP}") == f"Modbus {PUMP}"
    assert homoglyph_tokens("CK-12") == "\u0421\u041a-12"
    assert homoglyph_tokens("\u0422\u041d-45") == "TH-45"
    assert homoglyph_tokens("Modbus") is None


def test_positional_transliteration_handles_e_ae_and_glides() -> None:
    assert transliterate_v2("ekran") == (
        "\u044d\u043a\u0440\u0430\u043d",
        "\u0435\u043a\u0440\u0430\u043d",
    )
    assert transliterate_v2("novyy") == ("\u043d\u043e\u0432\u044b\u0439",)
    assert transliterate_v2("tsekh control") == (
        "\u0446\u0435\u0445 \u043a\u043e\u043d\u0442\u0440\u043e\u043b",
    )
    assert transliterate_v2("caf\u00e9") == ()


def test_fleeting_vowel_probe_is_limited_to_productive_endings() -> None:
    assert (
        fleeting_vowel("\u0444\u043b\u0430\u043d\u0435\u0446")
        == "\u0444\u043b\u0430\u043d\u0446\u0430"
    )
    assert (
        fleeting_vowel("\u0443\u0440\u043e\u0432\u0435\u043d\u044c")
        == "\u0443\u0440\u043e\u0432\u043d\u044f"
    )
    assert fleeting_vowel(PUMP) is None
    assert fleeting_vowel("\u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440") is None


def test_accepted_profile_behavior_is_unchanged() -> None:
    assert query_variants("C\u041a-5", profile_id=ACCEPTED) == ("C\u041a-5", "\u0441\u043a-5")
    assert query_variants("most", profile_id=LITERAL_QUERY_PROFILE) == ("most",)
    assert query_plan("podshipnik", profile_id=ACCEPTED).fallback == ()
    assert query_plan("podshipnik").fallback


def test_search_binds_the_nfc_base_as_the_primary_clause() -> None:
    decomposed = unicodedata.normalize("NFD", "\u0439\u043e\u0434")
    recorder = _Recorder()
    search(
        cast(Connection, recorder),
        LexicalRequest(query=decomposed, query_profile=LITERAL_QUERY_PROFILE),
        target=TARGET,
    )
    bound = recorder.statements[0][1]["query_text_0"]
    assert isinstance(bound, str) and unicodedata.is_normalized("NFC", bound)


def test_search_runs_fallback_and_fuzzy_only_after_an_empty_stage() -> None:
    recorder = _Recorder()
    result = search(
        cast(Connection, recorder),
        LexicalRequest(query="podshipnik", query_profile=GUARDED, snippets=False),
        target=TARGET,
    )
    statements = [statement for statement, _ in recorder.statements]
    assert result.query_stage == "fuzzy"
    assert len(statements) == 3 and "conjunction_mode => true" in statements[-1]
    assert "count(*)" not in " ".join(statements)
    assert result.as_json_dict()["queryStage"] == "fuzzy"


def test_search_stops_at_the_first_stage_with_hits() -> None:
    row = type(
        "Row",
        (),
        {
            "chunk_id": "c1",
            "document_id": "d1",
            "title": "",
            "language": "rus",
            "score": 1.0,
            "snippet": "",
        },
    )()
    recorder = _Recorder([row])
    result = search(
        cast(Connection, recorder),
        LexicalRequest(query="podshipnik", query_profile=GUARDED),
        target=TARGET,
    )
    assert result.query_stage == "primary"
    assert [hit.chunk_id for hit in result.hits] == ["c1"]
    assert len(recorder.statements) == 1
