"""The base CLI and setup bootstrap must work before optional extras are installed."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]


@pytest.mark.parametrize(
    "arguments",
    [
        ["--help"],
        ["setup", "--help"],
        ["features"],
        ["inference", "--help"],
        ["archive", "--help"],
    ],
)
def test_base_cli_does_not_require_optional_packages(arguments: list[str]) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "from arxiv_int.cli import main; import sys; raise SystemExit(main(sys.argv[1:]))",
            *arguments,
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout or result.stderr
