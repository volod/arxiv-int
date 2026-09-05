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
    assert 'arxiv_int_services up --profiles "pipeline"' in _dry_run("services-up")
    assert 'arxiv_int_services down --profiles "pipeline"' in _dry_run("services-down")
    assert 'arxiv_int_services reset --profiles "pipeline"' in _dry_run("services-reset")
    assert "--apply" in _dry_run("services-reset", "APPLY=1")
    assert "--apply" not in _dry_run("services-reset")
    assert 'arxiv_int_services up --profiles "core ui"' in _dry_run(
        "services-up", "SERVICE_PROFILES=core ui"
    )
