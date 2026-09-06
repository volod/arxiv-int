"""Make wrappers for setup and profile arguments that do not shadow .env."""

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]


def _dry_run(target: str, *variables: str) -> str:
    return subprocess.run(
        ["make", "--no-print-directory", "--dry-run", target, *variables],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_make_setup_exposes_atomic_commands_without_profile_defaults() -> None:
    help_text = subprocess.run(
        ["make", "--no-print-directory", "help"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    for name in (
        "setup",
        "setup-config",
        "setup-env",
        "services-pull",
        "models-pull",
        "setup-wait",
        "setup-schema",
    ):
        assert name in help_text
    setup = _dry_run("setup")
    assert "arxiv_int_setup_config" in setup
    assert "arxiv_int_setup_env" in setup
    assert 'bin/arxiv-int" setup' in setup
    assert "--extra inference" in setup
    assert "--profiles" not in _dry_run("services-up")
    assert '--profiles "core ui"' in _dry_run("services-up", "SERVICE_PROFILES=core ui")
    assert "setup --phase images" in _dry_run("services-pull")
    assert "setup --phase schema" in _dry_run("setup-schema")
