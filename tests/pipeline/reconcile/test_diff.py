"""Source-manifest scan, diff, tombstone, and shared-evidence fixtures."""

import hashlib
from pathlib import Path

import pytest

from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.reconcile.closure import invalidate_hashes
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
from arxiv_int.pipeline.run.reuse_index import ReuseEntry


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


def test_non_last_occurrence_removal_keeps_the_shard_live() -> None:
    previous = _manifest(_occ("main", "a.txt", "aaa"), _occ("main", "dup.txt", "aaa"))
    current = _manifest(_occ("main", "dup.txt", "aaa"))
    delta = diff_manifests(previous, current)
    tombs = tombstones_for(delta, previous, current, "gen-1")
    assert [item.last_occurrence for item in tombs] == [False]
    entry = ReuseEntry(
        "k1", "alpha", "aaa", 1, "/runs/k1", "succeeded", 10, "run-1", "gen-1", False
    )
    assert invalidate_hashes(delta, {"k1": entry}, ()) == frozenset()


def test_a_move_between_silos_is_not_reported_as_one_rename() -> None:
    previous = SourceManifest(
        "scan-a",
        (
            SiloScan("alpha", True, True, (_occ("alpha", "x.txt", "aaa"),)),
            SiloScan("beta", True, True, ()),
        ),
        True,
    )
    current = SourceManifest(
        "scan-b",
        (
            SiloScan("alpha", True, True, ()),
            SiloScan("beta", True, True, (_occ("beta", "y.txt", "aaa"),)),
        ),
        True,
    )
    delta = diff_manifests(previous, current)
    for event in delta.of_kind("path-rename"):
        assert event.previous_silo_id == event.silo_id
    kinds = {event.kind for event in delta.events}
    assert kinds == {"add", "remove"}
    tombs = tombstones_for(delta, previous, current, "gen-1")
    assert [(item.silo_id, item.last_occurrence) for item in tombs] == [("alpha", False)]


def test_rename_prefers_the_pairing_inside_one_silo() -> None:
    previous = SourceManifest(
        "scan-a",
        (
            SiloScan("alpha", True, True, (_occ("alpha", "x.txt", "aaa"),)),
            SiloScan("beta", True, True, (_occ("beta", "x.txt", "aaa"),)),
        ),
        True,
    )
    current = SourceManifest(
        "scan-b",
        (
            SiloScan("alpha", True, True, (_occ("alpha", "moved.txt", "aaa"),)),
            SiloScan("beta", True, True, (_occ("beta", "x.txt", "aaa"),)),
        ),
        True,
    )
    delta = diff_manifests(previous, current)
    renames = delta.of_kind("path-rename")
    assert [(item.silo_id, item.previous_silo_id, item.previous_path) for item in renames] == [
        ("alpha", "alpha", "x.txt")
    ]


def test_scan_hashes_large_files_without_reading_them_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "silo"
    root.mkdir()
    payload = b"chunked-source-bytes\n" * 4096
    (root / "big.bin").write_bytes(payload)
    original = Path.read_bytes

    def refuse(self: Path) -> bytes:
        if self.name == "big.bin":
            raise AssertionError("source scan must not read a whole file into memory")
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", refuse)
    manifest = scan_silos((SiloRoot("main", root),))
    digest = hashlib.sha256(payload).hexdigest()
    assert content_hashes(manifest) == (digest,)
