"""Public Make interfaces for local services."""

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]


def _dry_run(target: str, *variables: str) -> str:
    return subprocess.run(
        ["make", "--no-print-directory", "--dry-run", target, *variables],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_make_exposes_service_lifecycle_with_pipeline_as_the_default() -> None:
    help_text = subprocess.run(
        ["make", "--no-print-directory", "help"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert all(
        name in help_text
        for name in ("services-up", "services-status", "services-down", "services-reset", "logs")
    )
    assert "--profiles" not in _dry_run("services-up")
    assert "--profiles" not in _dry_run("services-down")
    assert "--profiles" not in _dry_run("services-reset")
    assert "--apply" in _dry_run("services-reset", "APPLY=1")
    assert "--apply" not in _dry_run("services-reset")
    assert '--profiles "core ui"' in _dry_run("services-up", "SERVICE_PROFILES=core ui")


def _data_root() -> str:
    return subprocess.run(
        ["bash", "-c", 'source "$1"; arxiv_int_data_root', "bash", "scripts/shared/common.sh"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_make_tool_caches_follow_the_selected_data_dir() -> None:
    selected = "/tmp/arxiv-int-cache fixture"

    assert f"cache_dir={_data_root()}/cache/pytest" in _dry_run("test")
    assert f"cache_dir={selected}/cache/pytest" in _dry_run("test", f"DATA_DIR={selected}")
