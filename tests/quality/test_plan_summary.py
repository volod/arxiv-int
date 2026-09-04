from pathlib import Path

from arxiv_int.quality.plan_summary import main, summary_lines
from tests.quality._plan_fixture import plan_with, task_block, write_project

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_repository_plan_reports_the_next_foundation_task() -> None:
    lines = summary_lines(PROJECT_ROOT)

    assert lines == [
        "tasks: 69",
        "agent lane: 60",
        "human lane: 9",
        "statuses: BLOCKED BY HUMAN=1, CLEAR=25, HUMAN-GATED=8, RUN NEEDED=35",
        "next agent: resolve-loc-lm-bench-reuse-integration [project-foundation]",
        "next human: authorize-upstream-repository-changes [project-foundation]",
    ]


def test_summary_counts_statuses_and_selects_required_work(tmp_path: Path) -> None:
    optional = task_block(identifier="optional-first", optional=True)
    required = task_block(identifier="required-next")
    plan = plan_with(required, optional)
    root = write_project(tmp_path, plan=plan)

    lines = summary_lines(root)

    assert "tasks: 2" in lines
    assert "statuses: CLEAR=2" in lines
    assert "next agent: required-next [feature]" in lines


def test_invalid_plan_summary_refuses_to_schedule(tmp_path: Path) -> None:
    root = write_project(tmp_path, plan=plan_with())

    assert summary_lines(root) == ["plan is invalid; run make lint-spec-plan"]
    assert main(["--root", str(root)]) == 1
