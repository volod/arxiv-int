"""Keep hosted CI dependency syncs free of the native extraction stack."""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("target", ["ci", "ci-github"])
def test_ci_dependency_syncs_keep_the_target_profile(target: str) -> None:
    result = subprocess.run(
        ["make", "--dry-run", target],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    syncs = [line for line in result.stdout.splitlines() if "uv sync --locked" in line]
    assert syncs, "CI must exercise the dependency-syncing checks"
    for command in syncs:
        assert ("--extra extraction" in command) == (target == "ci"), command
