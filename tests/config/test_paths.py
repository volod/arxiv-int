"""Tests for safe path containment."""

from pathlib import Path

from arxiv_int.paths import resolve_allowed_path


def test_path_resolution_is_symlink_safe_and_fail_closed(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    document = outside / "proof.txt"
    document.write_text("proof", encoding="utf-8")
    (allowed / "escape").symlink_to(outside, target_is_directory=True)

    assert resolve_allowed_path(document, ()) is None
    assert resolve_allowed_path(allowed / "escape" / document.name, (allowed,), kind="file") is None
    assert resolve_allowed_path(allowed, (allowed,), kind="directory") == allowed.resolve()
