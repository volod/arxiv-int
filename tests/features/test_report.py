import pytest

from arxiv_int.features import FEATURE_GROUPS, group_lines, inventory_lines


def test_inventory_reports_every_group_with_status_and_licences() -> None:
    lines = inventory_lines()
    text = "\n".join(lines)

    assert lines[0].startswith("arxiv-int ")
    assert f"{len(FEATURE_GROUPS)} feature groups" in lines[0]
    for group in FEATURE_GROUPS:
        assert f"{group.name} [" in text
    assert "requires: pyarrow (Apache-2.0)" in text
    assert "install: uv pip install 'arxiv-int[lake]'" in text


def test_reserved_groups_report_their_owning_capability() -> None:
    text = "\n".join(inventory_lines())

    assert "nlp [reserved]" in text
    assert "reserved for capability: russian-nlp" in text


def test_unknown_stage_is_reported_to_the_caller() -> None:
    with pytest.raises(LookupError):
        inventory_lines("no-such-stage")


def test_stage_inventory_reports_only_the_groups_that_stage_needs() -> None:
    lines = inventory_lines("ontology")
    text = "\n".join(lines)

    assert "1 feature group for stage 'ontology'" in lines[0]
    assert "graph [" in text
    assert "lake [" not in text


def test_stage_inventory_marks_conditional_gpu_and_ui_groups() -> None:
    embed = "\n".join(inventory_lines("embed"))
    report = "\n".join(inventory_lines("report"))
    gpu = "\n".join(inventory_lines())

    assert "requirement: conditional" in embed
    assert "gpu [" in embed
    assert "requirement: conditional" in report
    assert "ui [" in report
    assert "embed (conditional)" in gpu
    assert "report (conditional)" in gpu


def test_group_lines_wrap_long_stage_lists() -> None:
    lake = next(group for group in FEATURE_GROUPS if group.name == "lake")

    assert all(len(line) <= 100 for line in group_lines(lake))


def test_system_dependencies_are_reported() -> None:
    text = "\n".join(inventory_lines("extract"))

    assert "requires: docling (MIT)" in text
    assert "requires: iscc-tika (Apache-2.0)" in text
    assert "tesseract-ocr-rus" in text
    assert "tesseract-ocr-deu" in text
    assert "tesseract-ocr-ukr" in text
