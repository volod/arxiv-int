"""Make wrappers load .env, allocate unique run ids, and stay thin."""

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


def test_make_help_lists_pipeline_targets() -> None:
    help_text = subprocess.run(
        ["make", "--no-print-directory", "help"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    for name in (
        "pipeline",
        "run-create",
        "stage",
        "resume",
        "update",
        "rebuild",
        "invalidate",
        "prune",
        "run-status",
        "forecast",
        "run-finalize",
    ):
        assert name in help_text


def test_make_pipeline_and_run_create_do_not_pass_run_id_or_profile_defaults() -> None:
    pipeline = _dry_run("pipeline")
    created = _dry_run("run-create")
    assert "pipeline run" in pipeline
    assert "run create" in created
    assert "--run-id" not in pipeline
    assert "--run-id" not in created
    assert "--profile" not in pipeline
    assert "--profile" not in created
    assert "arxiv_int_load_env" in pipeline
    assert "arxiv_int_load_env" in created
    assert '--profile "investigation"' not in pipeline


def test_make_stage_and_resume_refuse_developer_run_id_fallback() -> None:
    stage = _dry_run("stage", "STAGE=inventory")
    resume = _dry_run("resume")
    assert "arxiv_int_require_created_run_id" in stage
    assert "arxiv_int_require_created_run_id" in resume
    assert 'stage "inventory" --run-id' in stage
    explicit = _dry_run("stage", "STAGE=inventory", "RUN_ID=run-abc")
    assert '--run-id "run-abc"' in explicit
    assert "arxiv_int_require_created_run_id" in explicit


def test_make_pipeline_passes_from_to_without_hardcoded_paths() -> None:
    text = _dry_run("pipeline", "FROM=extract", "TO=chunk")
    assert '--from "extract"' in text
    assert '--to "chunk"' in text
    assert "/mnt/" not in text
