import pytest

from arxiv_int.evaluation.export.catalog import parse_identity_catalog
from arxiv_int.evaluation.export.errors import ExportSpanError
from arxiv_int.evaluation.export.map import build_substitution_table
from arxiv_int.evaluation.export.rewrite import rewrite_json_value, rewrite_text
from tests.evaluation.export.export_support import (
    excerpt_text,
    graph_payload,
    identities_payload,
    items_payload,
)


def test_spans_keep_same_name_mentions_distinct() -> None:
    catalog = parse_identity_catalog(identities_payload())
    text = excerpt_text()
    table = build_substitution_table(catalog, {"excerpt.txt": text})
    mapped = rewrite_text(text, table, spans=tuple(span for span in table.spans))
    alpha = table.entity_labels["person:alpha"]
    beta = table.entity_labels["person:beta"]
    assert mapped.text.startswith(alpha)
    assert beta in mapped.text
    assert alpha != beta
    assert "Alice Example" not in mapped.text
    start, end = mapped.map_span(0, len("Alice Example"))
    assert mapped.text[start:end] == alpha


def test_unbound_same_name_occurrence_is_refused() -> None:
    catalog = parse_identity_catalog(identities_payload())
    table = build_substitution_table(catalog, {"excerpt.txt": excerpt_text()})
    with pytest.raises(ExportSpanError, match="without a catalog span"):
        rewrite_text("Alice Example walked in.", table)


def test_json_graph_and_answers_rewrite_together() -> None:
    catalog = parse_identity_catalog(identities_payload())
    table = build_substitution_table(catalog, {"excerpt.txt": excerpt_text()})
    excerpt = rewrite_text(
        excerpt_text(),
        table,
        spans=tuple(span for span in table.spans if span.artifact == "excerpt.txt"),
    )
    items = rewrite_json_value(items_payload(), table, {"excerpt.txt": excerpt})
    graph = rewrite_json_value(graph_payload(), table, {"excerpt.txt": excerpt})
    assert isinstance(items, dict)
    assert isinstance(graph, dict)
    alpha = table.entity_labels["person:alpha"]
    company = table.entity_labels["company:acme"]
    assert items["query_text"].startswith("Where did ")
    assert alpha in str(items["query_text"])
    assert "Alice Example" not in str(items["answer"])
    assert "100 kg" in str(items["answer"])
    assert "2020-01-01" in str(items["answer"])
    assert "55.75,37.62" in str(items["answer"])
    assert items["start"] == 0
    assert items["end"] == len(alpha)
    assert graph["edges"][0]["from"] == alpha
    assert graph["edges"][0]["to"] == company
    assert graph["nodes"][0]["label"] == alpha
    assert graph["nodes"][1]["label"] == table.entity_labels["person:beta"]
