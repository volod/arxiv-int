"""Definition comparison keeps logical grouping while tolerating PostgreSQL rendering."""

from arxiv_int.contracts.sqlalchemy.constraints import normalized_expression


def test_postgresql_check_rendering_normalizes_without_changing_meaning() -> None:
    assert normalized_expression("a IS NOT NULL AND b IS NOT NULL") == normalized_expression(
        "((a IS NOT NULL) AND (b IS NOT NULL))"
    )
    assert normalized_expression("status IN ('accepted', 'proposed')") == normalized_expression(
        "(status = ANY (ARRAY['accepted'::text, 'proposed'::text]))"
    )


def test_boolean_grouping_and_typed_literals_remain_distinct() -> None:
    assert normalized_expression("(a OR b) AND c") != normalized_expression("a OR (b AND c)")
    assert normalized_expression("x = '1'::integer") != normalized_expression("x = '1'::text")
    assert normalized_expression("document_id IS NOT NULL") != normalized_expression("true")
