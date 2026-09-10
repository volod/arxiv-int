"""Execute Make recipes with failed dependencies and harmless command markers."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SYNC_TARGETS = (
    "contracts",
    "contracts-gen",
    "contracts-check",
    "contracts-evolution",
    "contracts-evolution-live",
    "db-revision",
    "db-check",
    "ontology-gen",
    "ontology-check",
    "data-quality",
    "transform-parse",
    "transform-compile",
    "transform-build",
    "transform-test",
)


@pytest.mark.parametrize("target", SYNC_TARGETS)
@pytest.mark.parametrize("failure", ["sync", "config", "none"])
def test_make_refuses_command_after_failed_prerequisite(
    tmp_path: Path, target: str, failure: str
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "executed"
    for name, script in {
        "uv": f"#!/bin/bash\nexit {37 if failure == 'sync' else 0}\n",
        "arxiv-int": '#!/bin/bash\ntouch "$MARKER"\n',
    }.items():
        path = bin_dir / name
        path.write_text(script)
        path.chmod(0o755)
    common = tmp_path / "common.sh"
    common.write_text(
        'arxiv_int_data_root() { echo "$DATA_DIR"; }\n'
        f"arxiv_int_load_env() {{ return {38 if failure == 'config' else 0}; }}\n"
    )
    completed = subprocess.run(
        [
            "make",
            "--no-print-directory",
            target,
            f"VENV={tmp_path}",
            f"COMMON_SH={common}",
            f"DATA_DIR={tmp_path / 'data'}",
            "INPUT=fixture.json",
        ],
        cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:/usr/bin:/bin", "MARKER": str(marker)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert (completed.returncode == 0) == (failure == "none")
    assert marker.exists() == (failure == "none"), completed.stdout + completed.stderr


def test_make_test_preserves_cache_root_with_spaces(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "arguments"
    python = bin_dir / "python"
    python.write_text('#!/bin/bash\nprintf "%s\\n" "$@" > "$MARKER"\n')
    python.chmod(0o755)
    cache_root = tmp_path / "tool data"
    subprocess.run(
        ["make", "--no-print-directory", "test", f"VENV={tmp_path}", f"DATA_DIR={cache_root}"],
        cwd=ROOT,
        env={**os.environ, "MARKER": str(marker)},
        check=True,
        capture_output=True,
    )
    assert marker.read_text().splitlines() == [
        "-m",
        "pytest",
        "-o",
        f"cache_dir={cache_root}/cache/pytest",
        "-m",
        "not heavy and not archive",
    ]
