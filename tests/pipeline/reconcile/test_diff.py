"""Source-manifest scan, diff, tombstone, and shared-evidence fixtures."""

from pathlib import Path

from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.reconcile.diff import diff_manifests, tombstones_for
from arxiv_int.pipeline.reconcile.model import SiloScan, SourceManifest, SourceOccurrence
from arxiv_int.pipeline.reconcile.scan import content_hashes, scan_silos
from arxiv_int.pipeline.reconcile.views import (
    DerivedRow,
    merge_rows,
    retract,
    split_row,
    view_from_occurrences,
)


def _occ(silo: str, path: str, digest: str) -> SourceOccurrence:
    return SourceOccurrence(silo, path, digest)


def _manifest(*items: SourceOccurrence, complete: bool = True) -> SourceManifest:
    scans = (SiloScan("main", complete, complete, items, "" if complete else "partial"),)
    return SourceManifest("scan-a", scans, complete)


def test_scan_hashes_files_and_keeps_silos_distinct(tmp_path: Path) -> None:
    left = tmp_path / "a"
    right = tmp_path / "b"
    left.mkdir()
    right.mkdir()
    (left / "doc.txt").write_text("same", encoding="utf-8")
    (right / "doc.txt").write_text("same", encoding="utf-8")
    manifest = scan_silos((SiloRoot("left", left), SiloRoot("right", right)))
    assert manifest.comparable
    assert len(content_hashes(manifest)) == 1
    paths = {item.path_key for silo in manifest.silos for item in silo.occurrences}
    assert paths == {"left:doc.txt", "right:doc.txt"}


def test_diff_classifies_add_change_rename_and_remove() -> None:
    previous = _manifest(_occ("main", "old.txt", "aaa"), _occ("main", "keep.txt", "bbb"))
    current = _manifest(
        _occ("main", "new.txt", "aaa"),
        _occ("main", "keep.txt", "ccc"),
        _occ("main", "extra.txt", "ddd"),
    )
    delta = diff_manifests(previous, current)
    kinds = {event.kind: event for event in delta.events}
    assert kinds["path-rename"].previous_path == "old.txt"
    assert kinds["path-rename"].relative_path == "new.txt"
    assert kinds["content-change"].relative_path == "keep.txt"
    assert kinds["add"].relative_path == "extra.txt"
    assert "remove" not in kinds


def test_partial_or_unreadable_scans_withhold_removal_tombstones() -> None:
    previous = _manifest(_occ("main", "gone.txt", "aaa"))
    current = _manifest(complete=False)
    delta = diff_manifests(previous, current)
    assert delta.of_kind("remove") == ()
    assert delta.withheld_removals
    assert tombstones_for(delta, previous, current, "gen-1") == ()


def test_last_occurrence_retracts_only_unshared_rows() -> None:
    previous = _manifest(
        _occ("main", "a.txt", "aaa"),
        _occ("main", "b.txt", "aaa"),
        _occ("main", "c.txt", "ccc"),
    )
    current = _manifest(_occ("main", "b.txt", "aaa"))
    delta = diff_manifests(previous, current)
    tombs = tombstones_for(delta, previous, current, "gen-1")
    by_path = {item.relative_path: item for item in tombs}
    assert by_path["a.txt"].last_occurrence is False
    assert by_path["c.txt"].last_occurrence is True
    occurrences = tuple(item for silo in previous.silos for item in silo.occurrences)
    view = retract(view_from_occurrences(occurrences), tombs)
    assert "aaa" in view.retained
    assert "ccc" in view.retracted


def test_merge_split_and_review_keep_shared_evidence() -> None:
    left = DerivedRow("aaa", "doc-a", frozenset({"main:a.txt"}))
    right = DerivedRow("bbb", "doc-b", frozenset({"main:b.txt"}))
    merged = merge_rows(left, right, "cluster-1")
    first, second = split_row(merged, "doc-c")
    view = retract(
        view_from_occurrences(()),
        (),
        replacements=(first, second),
    )
    from arxiv_int.pipeline.reconcile.model import TOMBSTONE_SCHEMA, Tombstone

    tomb = Tombstone(
        TOMBSTONE_SCHEMA,
        "main:a.txt:aaa",
        "main",
        "a.txt",
        "aaa",
        "scan",
        "gen",
        True,
    )
    after = retract(view, (tomb,))
    assert "cluster-1" in after.retained or "doc-c" in after.retained
    assert after.retracted == ()
