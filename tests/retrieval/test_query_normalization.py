"""Russian query normalization stays bounded, query-only, and fingerprinted."""

from arxiv_int.retrieval.query_normalization import (
    LITERAL_QUERY_PROFILE,
    MAX_QUERY_VARIANTS,
    SELECTED_QUERY_PROFILE,
    load_query_policy,
    query_policy_fingerprint,
    query_variants,
)


def test_literal_profile_only_applies_unicode_and_space_normalization() -> None:
    assert query_variants("  \u0411\u041f\u041b\u0410  ", profile_id=LITERAL_QUERY_PROFILE) == (
        "\u0411\u041f\u041b\u0410",
    )


def test_selected_profile_expands_declared_and_mechanical_variants() -> None:
    assert query_variants("\u0411\u041f\u041b\u0410") == (
        "\u0411\u041f\u041b\u0410",
        "\u0431\u0435\u0441\u043f\u0438\u043b\u043e\u0442\u043d\u044b\u0439 \u043b\u0435\u0442\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0430\u043f\u043f\u0430\u0440\u0430\u0442",
    )
    assert "\u043a\u043e\u043c\u043f\u0440\u0435\u0441\u0441\u043e\u0440" in query_variants(
        "rjvghtccjh"
    )
    assert "\u043f\u043e\u0434\u0448\u0438\u043f\u043d\u0438\u043a" in query_variants("podshipnik")
    assert "\u0441\u043a-5" in query_variants("C\u041a-5")


def test_policy_is_declared_fingerprinted_and_bounded() -> None:
    policy = load_query_policy()
    assert policy.default_profile == SELECTED_QUERY_PROFILE
    assert len(query_policy_fingerprint()) == 64
    assert len(query_variants("podshipnik")) <= MAX_QUERY_VARIANTS
