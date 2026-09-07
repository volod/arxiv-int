"""Rooted contract reference validation."""

import pytest

from arxiv_int.contracts.paths import resolve_rooted_reference


def test_resolve_rooted_reference_accepts_relative_child(tmp_path) -> None:
    child = tmp_path / "datasets" / "documents.odcs.yaml"
    child.parent.mkdir(parents=True)
    child.write_text("id: documents\n", encoding="utf-8")

    assert resolve_rooted_reference(tmp_path, "datasets/documents.odcs.yaml") == child.resolve()


def test_resolve_rooted_reference_rejects_escapes(tmp_path) -> None:
    with pytest.raises(ValueError, match="must be relative"):
        resolve_rooted_reference(tmp_path, str(tmp_path / "datasets" / "x.yaml"))
    with pytest.raises(ValueError, match="escapes contract root"):
        resolve_rooted_reference(tmp_path, "../outside.yaml")
    with pytest.raises(ValueError, match="is empty"):
        resolve_rooted_reference(tmp_path, "  ")

    outside = tmp_path.parent / "paths-outside.yaml"
    outside.write_text("x: 1\n", encoding="utf-8")
    link = tmp_path / "leak.yaml"
    link.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes contract root"):
        resolve_rooted_reference(tmp_path, "leak.yaml")
