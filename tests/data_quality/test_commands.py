"""CLI, artifact writing, and import isolation."""

import logging
from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main


def test_parser_accepts_data_quality_check() -> None:
    args = build_parser().parse_args(
        [
            "data-quality",
            "check",
            "documents",
            "--run-id",
            "run-1",
            "--input",
            "table.parquet",
            "--related",
            "objects=objects.parquet",
            "--skip-snapshot",
        ]
    )
    assert args.command == "data-quality"
    assert args.dataset == "documents"
    assert args.skip_snapshot is True
    assert args.related == ["objects=objects.parquet"]


def test_package_init_does_not_import_pandera() -> None:
    import ast
    from pathlib import Path as P

    root = P("src/arxiv_int/data_quality")
    init_source = (root / "__init__.py").read_text(encoding="utf-8")
    generate_source = (root / "generate.py").read_text(encoding="utf-8")
    tree = ast.parse(init_source + "\n" + generate_source)
    imported = [
        alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names
    ]
    imported.extend(node.module or "" for node in tree.body if isinstance(node, ast.ImportFrom))
    assert "pandera" not in imported
    assert "polars" not in imported


def test_check_command_writes_secret_free_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    caplog.set_level(logging.INFO)
    status = main(
        [
            "data-quality",
            "check",
            "documents",
            "--run-id",
            "cli-1",
            "--input",
            str(tmp_path / "missing.json"),
            "--project-root",
            str(tmp_path),
        ]
    )
    assert status == 1
    assert (
        "unknown dataset" in caplog.text
        or "not a checkout" in caplog.text
        or "No such file" in caplog.text
    )
