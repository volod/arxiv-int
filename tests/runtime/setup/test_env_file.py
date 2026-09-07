"""Dotenv create/append and required-edit naming."""

from pathlib import Path

from arxiv_int.runtime.setup.env_file import missing_required_edits, sync_dotenv_file
from tests.runtime.setup.conftest import checkout


def test_sync_creates_dotenv_from_example_without_overwriting(tmp_path: Path) -> None:
    root = checkout(tmp_path, dotenv=None)
    detail = sync_dotenv_file(root)
    assert "created" in detail
    original = (root / ".env").read_text(encoding="utf-8")
    (root / ".env").write_text(original + "KEEP=operator\n", encoding="utf-8")
    (root / ".env.example").write_text(
        (root / ".env.example").read_text(encoding="utf-8") + "NEW=template\n", encoding="utf-8"
    )
    added = sync_dotenv_file(root)
    text = (root / ".env").read_text(encoding="utf-8")
    assert "added" in added
    assert "KEEP=operator" in text
    assert text.count("NEW=template") == 1
    assert sync_dotenv_file(root) == "dotenv already complete"


def test_missing_edits_name_required_roots(tmp_path: Path) -> None:
    root = checkout(tmp_path, dotenv="DATA_DIR=.data\n")
    edits = missing_required_edits(root, {})
    assert any("ARCHIVE_DIR" in item for item in edits)
    assert any("RESULTS_DIR" in item for item in edits)
    assert any("PGDATA_DIR" in item for item in edits)
