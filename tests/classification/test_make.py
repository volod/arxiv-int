"""Public Make interfaces for the classification scheme commands."""

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
RUN = "run-abc"


def _dry_run(target: str, *variables: str, run_env: str | None = None) -> str:
    environment = {key: value for key, value in os.environ.items() if key != "RUN_ID"}
    if run_env is not None:
        environment["RUN_ID"] = run_env
    return subprocess.run(
        ["make", "--no-print-directory", "--dry-run", target, *variables],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_tree_reads_the_packaged_taxonomy_unless_a_run_is_given() -> None:
    packaged = _dry_run("classification-tree", "ROOT=04", "DEPTH=2")
    assert '--root "04"' in packaged and "--run-id" not in packaged
    assert f'--run-id "{RUN}"' in _dry_run("classification-tree", f"RUN_ID={RUN}")
    assert f'--run-id "{RUN}"' in _dry_run("classification-tree", run_env=RUN)
    assert '--scheme "/tmp/s"' in _dry_run("classification-tree", "SCHEME=/tmp/s")


def test_check_and_show_need_a_created_run_or_a_scheme() -> None:
    for target, extra in (("classification-check", ()), ("classification-show", ("CLASS=04",))):
        default = _dry_run(target, *extra)
        assert 'arxiv_int_require_created_run_id "local"' in default
        explicit = _dry_run(target, *extra, f"RUN_ID={RUN}")
        assert f'--run-id "{RUN}"' in explicit
        scheme = _dry_run(target, *extra, "SCHEME=/tmp/s")
        assert '--scheme "/tmp/s"' in scheme and "require_created_run_id" not in scheme
