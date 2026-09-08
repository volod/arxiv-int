"""Crash injection and checksum validation for sibling artifact publication."""

from pathlib import Path

import pytest

from arxiv_int.pipeline.control.artifacts import (
    ArtifactPublishError,
    InjectedCrash,
    publish_attempt,
    validate_attempt,
)


def test_publish_then_validate_accepts_complete_tree(tmp_path: Path) -> None:
    directory = tmp_path / "attempt-1"
    published = publish_attempt(
        directory,
        reuse_key="abc",
        attempt=1,
        files={"output.json": b'{"ok": true}\n'},
        row_counts={"output.json": 1},
    )
    validated = validate_attempt(directory, reuse_key="abc", attempt=1)
    assert published.files["output.json"].bytes == 13
    assert validated.files["output.json"].row_count == 1
    assert (directory / "manifest.json").is_file()
    assert not (directory / ".output.json.tmp").exists()


def test_crash_after_payload_rename_is_not_accepted(tmp_path: Path) -> None:
    directory = tmp_path / "attempt-1"

    def crash(point: str) -> None:
        if point == "after-payload-rename":
            raise InjectedCrash(point)

    with pytest.raises(InjectedCrash):
        publish_attempt(
            directory,
            reuse_key="abc",
            attempt=1,
            files={"output.json": b"payload"},
            injector=crash,
        )
    assert (directory / "output.json").is_file()
    assert not (directory / "manifest.json").exists()
    with pytest.raises(ArtifactPublishError, match="manifest is missing"):
        validate_attempt(directory, reuse_key="abc", attempt=1)


def test_checksum_mismatch_is_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "attempt-1"
    publish_attempt(directory, reuse_key="abc", attempt=1, files={"output.json": b"one"})
    (directory / "output.json").write_bytes(b"two")
    with pytest.raises(ArtifactPublishError, match="checksum mismatch"):
        validate_attempt(directory, reuse_key="abc", attempt=1)


def test_empty_and_reserved_names_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ArtifactPublishError, match="empty"):
        publish_attempt(tmp_path / "a", reuse_key="abc", attempt=1, files={})
    with pytest.raises(ArtifactPublishError, match="reserved"):
        publish_attempt(tmp_path / "b", reuse_key="abc", attempt=1, files={"manifest.json": b"{}"})


def test_unregistered_files_are_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "attempt-1"
    publish_attempt(directory, reuse_key="abc", attempt=1, files={"output.json": b"one"})
    (directory / "extra.bin").write_bytes(b"two")
    with pytest.raises(ArtifactPublishError, match="unregistered"):
        validate_attempt(directory, reuse_key="abc", attempt=1)
