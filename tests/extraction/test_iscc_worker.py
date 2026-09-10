"""Type-check the isolated worker without optional extraction dependencies."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from arxiv_int.extraction import iscc_worker


@pytest.mark.parametrize("python_version", ["3.12", "3.13"])
def test_worker_typechecks_without_optional_backend(python_version: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--python-version",
            python_version,
            "--no-site-packages",
            "--no-incremental",
            "--cache-dir",
            os.devnull,
            str(Path(iscc_worker.__file__).resolve()),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
