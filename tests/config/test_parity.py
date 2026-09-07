"""Paired shell and Python resolution of one runtime configuration."""

import os
import subprocess
from pathlib import Path

import pytest

from arxiv_int.runtime import ConfigurationError, load_runtime_config
from arxiv_int.runtime.dotenv import read_dotenv

COMMON_SH = Path(__file__).parents[2] / "scripts/shared/common.sh"
_RESOLVE = 'source "$1"; arxiv_int_resolve_env || exit 1; env -0'


def _checkout(path: Path, dotenv: str) -> Path:
    path.mkdir(parents=True)
    (path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (path / ".env").write_text(dotenv, encoding="utf-8")
    return path


def _shell_resolve(
    root: Path, overrides: dict[str, str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/nonexistent"),
        "PROJECT_ROOT": str(root),
        **overrides,
    }
    return subprocess.run(
        ["bash", "-c", _RESOLVE, "bash", str(COMMON_SH)],
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=environment,
    )


def _shell_environment(root: Path, overrides: dict[str, str], cwd: Path) -> dict[str, str]:
    completed = _shell_resolve(root, overrides, cwd)
    assert completed.returncode == 0, completed.stderr
    entries = (item for item in completed.stdout.split("\0") if "=" in item)
    return dict(item.split("=", 1) for item in entries)


CASES = {
    "defaults": (
        "ARCHIVE_DIR=archive\nRESULTS_DIR=results\nPGDATA_DIR=database\n",
        {},
        {"RUNS_DIR": "results/runs", "TMP_DIR": "results/tmp"},
    ),
    "overridden-results-referenced-by-runs": (
        "ARCHIVE_DIR=archive\nRESULTS_DIR=dotenv results\nPGDATA_DIR=database\n"
        "RUNS_DIR=${RESULTS_DIR}/journal\n",
        {"RESULTS_DIR": "process results"},
        {"RESULTS_DIR": "process results", "RUNS_DIR": "process results/journal"},
    ),
    "nested-references": (
        "ARCHIVE_DIR=archive\nDATA_DIR=state\nRESULTS_DIR=${DATA_DIR}/results\n"
        "PGDATA_DIR=${RESULTS_DIR}/database\nRUNS_DIR=${RESULTS_DIR}/journal\n",
        {},
        {"PGDATA_DIR": "state/results/database", "RUNS_DIR": "state/results/journal"},
    ),
    "quotes-spaces-and-comments": (
        'ARCHIVE_DIR="source archive"  # operator note\n'
        "export RESULTS_DIR='bulk results'\nPGDATA_DIR=database\n",
        {},
        {"ARCHIVE_DIR": "source archive", "RESULTS_DIR": "bulk results"},
    ),
    "explicit-empty-values": (
        "ARCHIVE_DIR=archive\nRESULTS_DIR=results\nPGDATA_DIR=database\nRUNS_DIR=\nDATA_DIR=\n",
        {"VLLM_PORT": ""},
        {"RUNS_DIR": "results/runs", "DATA_DIR": ".data"},
    ),
    "environment-only-roots": (
        "",
        {"ARCHIVE_DIR": "archive", "RESULTS_DIR": "results", "PGDATA_DIR": "database"},
        {"RESULTS_DIR": "results", "MODEL_CACHE_DIR": "results/models"},
    ),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_shell_and_python_resolve_the_same_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    dotenv, overrides, expected = CASES[case]
    root = _checkout(tmp_path / "a checkout", dotenv)
    elsewhere = tmp_path / "unrelated cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    shell_environment = _shell_environment(root, overrides, elsewhere)
    through_make = load_runtime_config(environment=shell_environment)
    directly = load_runtime_config(project_root=root, environment=overrides)

    assert through_make.values == directly.values
    assert through_make.project_root == root
    for name, relative in expected.items():
        assert dict(directly.values)[name] == str(root / relative)


def test_an_alternate_checkout_keeps_its_own_roots(tmp_path: Path) -> None:
    dotenv = "ARCHIVE_DIR=archive\nRESULTS_DIR=results\nPGDATA_DIR=database\n"
    first = _checkout(tmp_path / "first checkout", dotenv)
    second = _checkout(tmp_path / "second checkout", dotenv)

    first_config = load_runtime_config(environment=_shell_environment(first, {}, second))
    second_config = load_runtime_config(environment=_shell_environment(second, {}, first))

    assert first_config.results_dir == first / "results"
    assert second_config.results_dir == second / "results"


INVALID = {
    "cyclic-references": (
        "ARCHIVE_DIR=archive\nRESULTS_DIR=${RUNS_DIR}/results\nPGDATA_DIR=database\n"
        "RUNS_DIR=${RESULTS_DIR}/journal\n",
        "references itself",
    ),
    "missing-reference": (
        "ARCHIVE_DIR=archive\nRESULTS_DIR=${UNKNOWN_DIR}/results\nPGDATA_DIR=database\n",
        "references missing UNKNOWN_DIR",
    ),
    "empty-reference": (
        "ARCHIVE_DIR=archive\nPROOF_ARCHIVE_DIR=\nRESULTS_DIR=${PROOF_ARCHIVE_DIR}/results\n"
        "PGDATA_DIR=database\n",
        "references empty PROOF_ARCHIVE_DIR",
    ),
    "malformed-assignment": (
        "ARCHIVE_DIR=archive\nRESULTS DIR results\nPGDATA_DIR=database\n",
        "expected NAME=value",
    ),
}


@pytest.mark.parametrize("case", sorted(INVALID))
def test_shell_and_python_refuse_the_same_invalid_configuration(tmp_path: Path, case: str) -> None:
    dotenv, message = INVALID[case]
    root = _checkout(tmp_path / "a checkout", dotenv)

    completed = _shell_resolve(root, {}, root)
    with pytest.raises(ConfigurationError, match=message):
        load_runtime_config(project_root=root, environment={})

    assert completed.returncode != 0
    assert message in completed.stderr


def test_resolution_mutates_neither_the_process_environment_nor_the_checkout(
    tmp_path: Path,
) -> None:
    dotenv = "ARCHIVE_DIR=archive\nRESULTS_DIR=results\nPGDATA_DIR=database\n"
    root = _checkout(tmp_path / "a checkout", dotenv)
    before = dict(os.environ)

    load_runtime_config(project_root=root, environment={})
    _shell_environment(root, {}, root)

    assert dict(os.environ) == before
    assert (root / ".env").read_text(encoding="utf-8") == dotenv
    assert sorted(item.name for item in root.iterdir()) == [".env", "pyproject.toml"]


@pytest.mark.parametrize("exported", [False, True])
def test_shell_local_values_only_override_when_exported(tmp_path: Path, exported: bool) -> None:
    root = _checkout(tmp_path / "checkout", "LOG_LEVEL= INFO \n")
    assignment = ("export " if exported else "") + "LOG_LEVEL=DEBUG; "
    completed = subprocess.run(
        ["bash", "-c", assignment + _RESOLVE, "bash", str(COMMON_SH)],
        env={"PATH": "/usr/bin:/bin", "PROJECT_ROOT": str(root)},
        text=True,
        capture_output=True,
        check=True,
    )
    environment = dict(item.split("=", 1) for item in completed.stdout.split("\0") if "=" in item)
    expected = "DEBUG" if exported else "INFO"
    assert environment["LOG_LEVEL"] == expected
    assert read_dotenv(root / ".env")["LOG_LEVEL"] == "INFO"
