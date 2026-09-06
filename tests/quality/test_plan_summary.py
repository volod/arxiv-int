from pathlib import Path

from arxiv_int.quality.plan_summary import main, summary_lines
from tests.quality._plan_fixture import plan_with, record_text, task_block, write_project


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


def test_next_work_respects_open_prerequisites(tmp_path: Path) -> None:
    blocked = task_block("blocked-work", dependencies="`ready-work`.")
    ready = task_block("ready-work")
    root = write_project(tmp_path, plan=plan_with(blocked, ready))

    lines = summary_lines(root)

    assert "blocked by prerequisites: 1" in lines
    assert "next agent: ready-work [feature]" in lines


def test_a_fully_blocked_lane_reports_no_next_task(tmp_path: Path) -> None:
    human = task_block(
        "await-operator",
        status="HUMAN-GATED",
        dependencies="[Earlier work](records/earlier-work.md); `build-feature`.",
    )
    plan = plan_with(task_block(dependencies="none."), human_blocks=(human,))
    records = {"earlier-work": record_text("earlier-work", snapshot=task_block("earlier-work"))}
    root = write_project(tmp_path, plan=plan, records=records)

    lines = summary_lines(root)

    assert "next agent: build-feature [feature]" in lines
    assert "next human: blocked" in lines
