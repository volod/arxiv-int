"""Selective lock and transitive dependency changes without loading tool backends."""

from pathlib import Path

import pytest

from arxiv_int.pipeline.control.dependency_assets import dependency_assets

_LOCK = """version = 1
revision = 3
requires-python = ">=3.12"
[[package]]
name = "tool-a"
version = "1"
dependencies = [{name = "shared"}]
[[package]]
name = "tool-b"
version = "1"
[[package]]
name = "shared"
version = "1"
"""


def test_lock_closure_excludes_unrelated_tools_and_includes_transitive_edits(
    tmp_path: Path,
) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text(_LOCK)
    before_a = dependency_assets(tmp_path, ("tool-a",))
    before_b = dependency_assets(tmp_path, ("tool-b",))
    lock.write_text(
        _LOCK.replace('name = "shared"\nversion = "1"', 'name = "shared"\nversion = "2"')
    )
    assert dependency_assets(tmp_path, ("tool-a",)) != before_a
    assert dependency_assets(tmp_path, ("tool-b",)) == before_b
    lock.write_text(_LOCK + "\n# Formatting has no dependency semantics.\n")
    assert dependency_assets(tmp_path, ("tool-a",)) == before_a


def test_missing_lock_or_declared_package_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    with pytest.raises(ValueError, match=r"requires uv\.lock"):
        dependency_assets(tmp_path, ("tool-a",))
    (tmp_path / "uv.lock").write_text(_LOCK)
    with pytest.raises(ValueError, match=r"missing from uv\.lock"):
        dependency_assets(tmp_path, ("typo",))
