from pathlib import Path

from arxiv_int.pipeline.dedupe.decide import GroupingPlan, plan_groups
from arxiv_int.pipeline.dedupe.group import DUPLICATE_FAMILY, Edge, assemble
from arxiv_int.pipeline.dedupe.model import (
    EDITION,
    EXACT,
    LEXICAL,
    MEMBER,
    NORMALIZED,
    REPRESENTATIVE,
    DedupePolicy,
)
from arxiv_int.pipeline.dedupe.sketches import SketchTables
from arxiv_int.pipeline.dedupe.source import NormalizedInput

POLICY = DedupePolicy(batch_rows=2, min_sketch_shingles=1)


def _text(count: int, offset: int = 0) -> str:
    return " ".join(f"slovo{index + offset}" for index in range(count))


def _replaced(text: str, every: int) -> str:
    words = text.split(" ")
    for index in range(0, len(words), every):
        words[index] = f"zamena{index}"
    return " ".join(words)


def _plan(tmp_path: Path, items: dict[str, tuple[str, str, str]]) -> GroupingPlan:
    tables = SketchTables(tmp_path, POLICY)
    try:
        for document_id, (exact, normalized, text) in items.items():
            search = tmp_path / f"{document_id}.txt"
            search.write_text(text, encoding="utf-8")
            tables.add(
                NormalizedInput(
                    document_id, f"n-{document_id}", exact, normalized, len(text), search
                ),
                text,
            )
    finally:
        tables.close()
    return plan_groups(tables.sketch_path, tables.band_path, POLICY)


def test_identical_extracted_text_groups_as_an_exact_duplicate(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        {
            "a": ("text-1", "norm-1", _text(200)),
            "b": ("text-1", "norm-2", _text(200)),
            "c": ("text-2", "norm-3", _text(200, offset=5000)),
        },
    )

    grouped = {member.document_id: member for member in plan.duplicates}
    assert set(grouped) == {"a", "b"}
    assert grouped["a"].method == EXACT
    assert not plan.editions


def test_normalization_only_differences_group_as_normalized_duplicates(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        {
            "a": ("text-1", "norm-1", _text(200)),
            "b": ("text-2", "norm-1", _text(200)),
        },
    )

    assert {member.method for member in plan.duplicates} == {NORMALIZED}
    assert {member.role for member in plan.duplicates} == {REPRESENTATIVE, MEMBER}


def test_near_identical_text_groups_lexically_and_suppresses_members(tmp_path: Path) -> None:
    base = _text(200)
    plan = _plan(
        tmp_path,
        {
            "a": ("text-1", "norm-1", base),
            "b": ("text-2", "norm-2", _replaced(base, 60)),
        },
    )

    assert {member.method for member in plan.duplicates} == {LEXICAL}
    assert [member.suppressed for member in plan.duplicates].count(True) == 1
    assert all(0.9 <= member.score <= 1.0 for member in plan.duplicates)


def test_reworked_text_groups_as_an_edition_without_suppression(tmp_path: Path) -> None:
    base = _text(200)
    plan = _plan(
        tmp_path,
        {
            "a": ("text-1", "norm-1", base),
            "b": ("text-2", "norm-2", _replaced(base, 8)),
        },
    )

    assert {member.method for member in plan.editions} == {EDITION}
    assert not any(member.suppressed for member in plan.editions)
    assert not plan.duplicates


def test_grouping_elects_the_longest_document_as_representative() -> None:
    members = assemble(
        [Edge("short", "long", LEXICAL, 0.95)],
        {"short": 100, "long": 900},
        DUPLICATE_FAMILY,
        suppress_members=True,
    )

    leaders = [member.document_id for member in members if member.role == REPRESENTATIVE]
    assert leaders == ["long"]
    assert [member.document_id for member in members if member.suppressed] == ["short"]


def test_grouping_is_transitive_and_keeps_one_representative() -> None:
    members = assemble(
        [Edge("a", "b", LEXICAL, 0.95), Edge("b", "c", LEXICAL, 0.93)],
        {"a": 10, "b": 20, "c": 30},
        DUPLICATE_FAMILY,
        suppress_members=True,
    )

    assert len({member.group_id for member in members}) == 1
    assert sum(member.role == REPRESENTATIVE for member in members) == 1
    assert len(members) == 3


def test_grouping_is_stable_under_input_order() -> None:
    edges = [Edge("a", "b", LEXICAL, 0.95), Edge("b", "c", LEXICAL, 0.93)]
    sizes = {"a": 10, "b": 20, "c": 30}

    forward = assemble(edges, sizes, DUPLICATE_FAMILY, suppress_members=True)
    reversed_order = assemble(list(reversed(edges)), sizes, DUPLICATE_FAMILY, suppress_members=True)

    assert forward == reversed_order
