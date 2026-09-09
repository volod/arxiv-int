"""Bounded archive hashing and drift-check regressions."""

import hashlib
from pathlib import Path
from unittest.mock import patch

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.commands import require_frozen_context
from arxiv_int.pipeline.run.context import RunContext, snapshot_silos


def test_snapshot_does_not_read_whole_files(tmp_path: Path) -> None:
    payload = b"archive bytes" * 100_000
    (tmp_path / "doc.bin").write_bytes(payload)
    expected = sha256_text(f"default:doc.bin:{hashlib.sha256(payload).hexdigest()}")
    with patch.object(Path, "read_bytes", side_effect=AssertionError("whole-file read")):
        assert snapshot_silos((SiloRoot("default", tmp_path),)) == expected


def test_frozen_load_does_not_open_archive_bytes(frozen_run: RunContext) -> None:
    original_open = Path.open

    def guarded_open(path: Path, *args: object, **kwargs: object) -> object:
        assert not path.is_relative_to(frozen_run.silos[0].root), "archive content reread"
        return original_open(path, *args, **kwargs)

    with patch.object(Path, "open", guarded_open):
        assert (
            require_frozen_context(
                frozen_run.runs_dir,
                frozen_run.run_id,
                project_root=frozen_run.project_root,
                environment={},
            )
            == frozen_run
        )


def test_snapshot_memory_is_independent_of_file_size(tmp_path: Path) -> None:
    import tracemalloc

    from arxiv_int.pipeline.run.snapshot import capture_snapshot

    silos = (SiloRoot("default", tmp_path),)
    peaks = []
    for size in (4 * 1024**2, 64 * 1024**2):
        with (tmp_path / "large.bin").open("wb") as handle:
            handle.truncate(size)
        tracemalloc.start()
        try:
            capture_snapshot(silos)
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
    assert max(peaks) < 4 * 1024**2
    assert abs(peaks[1] - peaks[0]) < 1024**2


def test_content_identity_preserves_order_normalization_and_silos(tmp_path: Path) -> None:
    first = tmp_path / "first"
    first.mkdir()
    second = tmp_path / "second"
    second.mkdir()
    (first / "z").write_bytes(b"last")
    (first / "a \r\nname").write_bytes(b"first")
    (second / "z").write_bytes(b"different silo")
    silos = (SiloRoot("one", first), SiloRoot("two", second), SiloRoot("gone", tmp_path / "gone"))
    parts = [
        f"one:a \r\nname:{hashlib.sha256(b'first').hexdigest()}",
        f"one:z:{hashlib.sha256(b'last').hexdigest()}",
        f"two:z:{hashlib.sha256(b'different silo').hexdigest()}",
        "gone:missing",
    ]
    assert snapshot_silos(silos) == sha256_text("\n".join(parts))
    assert snapshot_silos(()) == sha256_text("empty-archive")


def test_symlink_and_empty_directory_treatment_is_preserved(tmp_path: Path) -> None:
    from arxiv_int.pipeline.run.snapshot import capture_snapshot, metadata_snapshot

    archive = tmp_path / "archive"
    archive.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "doc").write_bytes(b"outside")
    (archive / "file-link").symlink_to(outside / "doc")
    (archive / "dir-link").symlink_to(outside, target_is_directory=True)
    (archive / "broken-link").symlink_to(tmp_path / "absent")
    (archive / "empty").mkdir()
    content, metadata = capture_snapshot((SiloRoot("default", archive),))
    assert content == sha256_text("empty-archive")
    assert metadata == metadata_snapshot(())


def test_unreadable_file_still_refuses_snapshot(tmp_path: Path) -> None:
    import pytest

    from arxiv_int.pipeline.run.snapshot import capture_snapshot

    (tmp_path / "unreadable").write_bytes(b"private")
    with (
        patch.object(Path, "open", side_effect=PermissionError("unreadable")),
        pytest.raises(PermissionError, match="unreadable"),
    ):
        capture_snapshot((SiloRoot("default", tmp_path),))


def test_capture_refuses_change_after_file_was_hashed(tmp_path: Path) -> None:
    import pytest

    from arxiv_int.pipeline.control.artifacts import hash_file
    from arxiv_int.pipeline.run.errors import StaleUpstreamError
    from arxiv_int.pipeline.run.snapshot import capture_snapshot

    first = tmp_path / "a"
    first.write_bytes(b"before")
    (tmp_path / "z").write_bytes(b"last")

    def change_earlier_file(path: Path) -> tuple[str, int]:
        result = hash_file(path)
        if path.name == "z":
            first.write_bytes(b"changed after hash")
        return result

    with (
        patch("arxiv_int.pipeline.run.snapshot.hash_file", change_earlier_file),
        pytest.raises(StaleUpstreamError, match="during hashing"),
    ):
        capture_snapshot((SiloRoot("default", tmp_path),))
