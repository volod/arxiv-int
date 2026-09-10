"""Named ParadeDB query assets bind user input and refuse unindexed fields."""

import json

import pytest

from arxiv_int.stores.projections.adapters.lexical import (
    INDEXED_COLUMNS,
    TEXT_FIELDS,
    TOKENIZER_FINGERPRINT,
    TOKENIZER_PROFILE,
)
from arxiv_int.stores.projections.adapters.lexical_search import (
    FILTER_FIELDS,
    SEARCH_FIELDS,
    LexicalFieldError,
    count_sql,
    explain_sql,
    facet_sql,
    identifier_query,
    lookup_sql,
    match_query,
    search_sql,
)

INJECTION = "'; DROP TABLE corpus.chunks; --"


def test_tokenizer_profile_declares_russian_literal_and_filter_fields() -> None:
    profile = json.loads(TOKENIZER_PROFILE)
    assert profile["body"]["tokenizer"] == {
        "type": "default",
        "stemmer": "Russian",
        "stopwords_language": "Russian",
    }
    assert profile["identifiers"]["tokenizer"] == {"type": "whitespace", "lowercase": False}
    assert profile["language"]["fast"] is True
    assert set(profile) <= set(INDEXED_COLUMNS)
    assert TOKENIZER_FINGERPRINT and TOKENIZER_PROFILE.isascii()


def test_every_searchable_field_is_indexed() -> None:
    assert set(SEARCH_FIELDS) | set(FILTER_FIELDS) <= set(TEXT_FIELDS)


def test_match_query_binds_query_text_and_filters() -> None:
    query = match_query(query_text=INJECTION, filters={"language": "rus", "document_id": ""})
    assert INJECTION not in query.expression
    assert query.parameters["query_text"] == INJECTION
    assert query.parameters["filter_field_0"] == "language"
    assert query.parameters["filter_value_0"] == "rus"
    assert query.expression.count("parse_with_field") == len(SEARCH_FIELDS)
    assert "paradedb.term(:filter_field_0, :filter_value_0)" in query.expression


def test_match_query_orders_filters_deterministically() -> None:
    first = match_query(query_text="x", filters={"language": "rus", "document_id": "d1"})
    second = match_query(query_text="x", filters={"document_id": "d1", "language": "rus"})
    assert first == second


def test_match_query_refuses_unindexed_search_and_filter_fields() -> None:
    with pytest.raises(LexicalFieldError, match="unindexed field"):
        match_query(query_text="x", fields=("body", "chunk_text"))
    with pytest.raises(LexicalFieldError, match="unindexed field"):
        match_query(query_text="x", filters={"body": "value"})
    with pytest.raises(LexicalFieldError, match="at least one search field"):
        match_query(query_text="x", fields=())


def test_identifier_query_covers_literal_fields_without_analysis() -> None:
    query = identifier_query("P-100")
    assert query.parameters["identifier"] == "P-100"
    assert "parse_with_field" not in query.expression
    assert query.expression.count("paradedb.term") == 2


def test_statements_use_the_index_operator_and_bound_limits() -> None:
    query = match_query(query_text="насос")
    statement = search_sql("search.lexical_p_v1", query, snippets=True)
    assert "chunk_id @@@" in statement
    assert "paradedb.score(chunk_id) AS score" in statement
    assert "max_num_chars => :snippet_chars" in statement
    assert statement.endswith("LIMIT :limit OFFSET :offset")
    assert "NULL::text AS snippet" in search_sql("search.t", query, snippets=False)
    assert count_sql("search.t", query).startswith("SELECT count(*)")
    assert lookup_sql("search.t", query).endswith("ORDER BY document_id, chunk_id LIMIT :limit")
    assert explain_sql("SELECT 1").startswith("EXPLAIN (ANALYZE, VERBOSE, FORMAT TEXT)")


def test_facet_sql_only_groups_whitelisted_columns() -> None:
    query = match_query(query_text="насос")
    assert "GROUP BY 1" in facet_sql("search.t", query, "language")
    with pytest.raises(LexicalFieldError, match="unindexed field"):
        facet_sql("search.t", query, "body")
