from pathlib import Path

import pytest

from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.interfaces.sources import BoundingBox, SiloRoot, SourceAnchor, SourceOccurrence


def _occurrence(silo_id: str, relative_path: str = "invoices/ledger.xlsx") -> SourceOccurrence:
    return SourceOccurrence(silo_id=silo_id, relative_path=relative_path, scan_id="scan-1")


def test_duplicate_relative_paths_in_different_silos_are_distinct() -> None:
    left = _occurrence("alpha")
    right = _occurrence("beta")

    assert left.relative_path == right.relative_path
    assert left.identity != right.identity
    assert left != right


def test_same_silo_path_across_scans_is_a_new_occurrence() -> None:
    first = SourceOccurrence(silo_id="alpha", relative_path="notes.txt", scan_id="scan-1")
    second = SourceOccurrence(silo_id="alpha", relative_path="notes.txt", scan_id="scan-2")

    assert first.identity != second.identity


def test_content_hash_does_not_collapse_duplicate_paths() -> None:
    first = SourceOccurrence(
        silo_id="alpha",
        relative_path="copy.txt",
        scan_id="scan-1",
        content_hash="sha256:same",
    )
    second = SourceOccurrence(
        silo_id="beta",
        relative_path="copy.txt",
        scan_id="scan-1",
        content_hash="sha256:same",
    )

    assert first.content_hash == second.content_hash
    assert first.identity != second.identity


def test_member_anchor_keeps_container_and_nested_path() -> None:
    occurrence = SourceOccurrence(
        silo_id="mail",
        relative_path="inbox/bundle.zip",
        scan_id="scan-1",
        container_path="inbox/bundle.zip",
        member_path="attachments/invoice.pdf",
    )
    anchor = SourceAnchor(occurrence=occurrence, page=2, start_char=10, end_char=24, kind="page")

    assert occurrence.is_member is True
    assert anchor.occurrence.member_path == "attachments/invoice.pdf"
    assert occurrence.resolve(Path("/silos/mail")) == Path("/silos/mail/inbox/bundle.zip")


def test_cell_anchor_names_sheet_range_and_grid() -> None:
    occurrence = _occurrence("tables")
    anchor = SourceAnchor(
        occurrence=occurrence,
        sheet="Payments",
        cell_range="B2:D10",
        row=2,
        column=2,
        bbox=BoundingBox(1.0, 2.0, 8.0, 12.0),
        space="original",
        kind="cell",
    )

    assert anchor.is_cell is True
    assert anchor.sheet == "Payments"
    assert anchor.cell_range == "B2:D10"
    assert anchor.bbox is not None
    assert (anchor.bbox.x0, anchor.bbox.y1) == (1.0, 12.0)


def test_original_and_normalized_anchors_share_the_occurrence() -> None:
    occurrence = _occurrence("tables")
    original = SourceAnchor(occurrence=occurrence, start_char=0, end_char=12, space="original")
    normalized = SourceAnchor(occurrence=occurrence, start_char=4, end_char=16, space="normalized")

    assert original.occurrence == normalized.occurrence
    assert original.space != normalized.space


def test_stage_context_resolves_the_same_path_per_silo() -> None:
    context = StageContext(
        stage="extract",
        run_id="run-1",
        generation_id="gen-1",
        silos=(
            SiloRoot("alpha", Path("/silos/alpha")),
            SiloRoot("beta", Path("/silos/beta")),
        ),
        results_dir=Path("/results"),
        options={},
    )
    left = _occurrence("alpha")
    right = _occurrence("beta")

    assert context.source_path(left) != context.source_path(right)
    assert context.source_path(left) == Path("/silos/alpha/invoices/ledger.xlsx")


def test_unknown_silo_and_duplicate_silo_ids_are_refused() -> None:
    with pytest.raises(ValueError, match="unique"):
        StageContext(
            stage="extract",
            run_id="run-1",
            generation_id="gen-1",
            silos=(SiloRoot("alpha", Path("/a")), SiloRoot("alpha", Path("/b"))),
            results_dir=Path("/results"),
            options={},
        )
    context = StageContext(
        stage="extract",
        run_id="run-1",
        generation_id="gen-1",
        silos=(SiloRoot("alpha", Path("/a")),),
        results_dir=Path("/results"),
        options={},
    )
    with pytest.raises(LookupError, match="beta"):
        context.silo_root("beta")


@pytest.mark.parametrize(
    "relative_path",
    ["/abs.txt", "../escape.txt", "a/../b.txt", "a//b.txt", r"dir\file.txt", ""],
)
def test_absolute_or_escaped_relative_paths_are_refused(relative_path: str) -> None:
    with pytest.raises(ValueError, match="relative"):
        SourceOccurrence(silo_id="alpha", relative_path=relative_path, scan_id="scan-1")


def test_inverted_character_span_is_refused() -> None:
    with pytest.raises(ValueError, match="end_char"):
        SourceAnchor(occurrence=_occurrence("alpha"), start_char=9, end_char=3)
