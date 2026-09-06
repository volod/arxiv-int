from pathlib import Path

from arxiv_int.quality.plan_graph import blocking_prerequisites, dependency_references
from arxiv_int.quality.plan_integrity import integrity_findings
from arxiv_int.quality.plan_model import read_tasks
from tests.quality._plan_fixture import (
    checkpoint_block,
    plan_with,
    record_text,
    task_block,
    write_project,
)


def _findings(tmp_path: Path, plan: str, records: dict[str, str] | None = None) -> list[str]:
    return integrity_findings(write_project(tmp_path, plan=plan, records=records))


def test_a_dependency_named_on_a_continuation_line_is_resolved(tmp_path: Path) -> None:
    plan = plan_with(task_block(dependencies="`build-nothing`;\n`also-missing`."))

    findings = _findings(tmp_path, plan)

    assert any("unknown task `build-nothing`" in finding for finding in findings)
    assert any("unknown task `also-missing`" in finding for finding in findings)


def test_an_accepted_sequenced_record_satisfies_a_dependency(tmp_path: Path) -> None:
    snapshot = task_block("earlier-work")
    plan = plan_with(
        task_block(
            dependencies=("[Earlier work](records/0001-feature-earlier-work.md); `earlier-work`.")
        )
    )
    record_name = "0001-feature-earlier-work"

    findings = _findings(
        tmp_path,
        plan,
        {record_name: record_text("earlier-work", snapshot=snapshot)},
    )

    assert findings == []


def test_an_archived_but_unaccepted_record_cannot_satisfy_a_dependency(tmp_path: Path) -> None:
    plan = plan_with(task_block(dependencies="[Earlier work](records/earlier-work.md)."))
    record = record_text("earlier-work", state="blocked at the service gate.")

    findings = _findings(tmp_path, plan, {"earlier-work": record})

    assert any("unaccepted record `earlier-work`" in finding for finding in findings)


def test_a_task_cannot_depend_on_itself(tmp_path: Path) -> None:
    plan = plan_with(task_block(dependencies="`build-feature`."))

    findings = _findings(tmp_path, plan)

    assert any("depends on itself" in finding for finding in findings)


def test_a_required_dependency_cycle_is_reported(tmp_path: Path) -> None:
    plan = plan_with(
        task_block("first-task", dependencies="`second-task`."),
        task_block("second-task", dependencies="`first-task`."),
    )

    findings = _findings(tmp_path, plan)

    assert any("dependency cycle" in finding for finding in findings)


def test_a_conditional_branch_does_not_order_tasks(tmp_path: Path) -> None:
    plan = plan_with(
        task_block("first-task", dependencies="`second-task` only when the branch is selected."),
        task_block("second-task", dependencies="`first-task`."),
    )

    findings = _findings(tmp_path, plan)

    assert findings == []


def test_conditional_and_required_references_are_distinguished() -> None:
    value = "`always-needed`; `sometimes-needed` only for a selected viewer."

    references = dependency_references(value)

    assert [(item.identifier, item.conditional) for item in references] == [
        ("always-needed", False),
        ("sometimes-needed", True),
    ]


def test_blocking_prerequisites_ignore_conditional_and_closed_work(tmp_path: Path) -> None:
    plan = plan_with(
        task_block("first-task"),
        task_block(
            "second-task",
            dependencies="`first-task`; `retired-task` when the branch is selected.",
        ),
    )
    root = write_project(tmp_path, plan=plan)
    tasks = read_tasks(root / "docs/impl/plan.md")
    open_tasks = {task.identifier for task in tasks}

    assert blocking_prerequisites(tasks[1], open_tasks) == ("first-task",)


def test_an_unknown_review_checkpoint_is_reported(tmp_path: Path) -> None:
    plan = plan_with(task_block(checkpoint="`review-nothing`."))

    findings = _findings(tmp_path, plan)

    assert any("is not a known checkpoint" in finding for finding in findings)


def test_a_declared_checkpoint_task_resolves_its_consumers(tmp_path: Path) -> None:
    plan = plan_with(
        task_block(checkpoint="`review-feature`."),
        checkpoint_block(dependencies="`build-feature`."),
    )

    assert _findings(tmp_path, plan) == []


def test_an_audit_input_must_name_a_declared_note(tmp_path: Path) -> None:
    audit = "- Audit inputs: [AUD-feature-9](records/earlier-work.md#audit-handoff).\n"
    plan = plan_with(task_block(extra_fields=audit))
    record = record_text("earlier-work", snapshot=task_block("earlier-work"))

    findings = _findings(tmp_path, plan, {"earlier-work": record})

    assert any("`AUD-feature-9` is not declared" in finding for finding in findings)


def test_an_unresolved_note_without_an_owning_task_is_reported(tmp_path: Path) -> None:
    handoff = (
        "| Note | Kind | Owner |\n| --- | --- | --- |\n"
        "| `AUD-feature-1` | blocking | [Feature](../plan.md#build-feature), routed |\n"
    )
    record = record_text("earlier-work", snapshot=task_block("earlier-work"), handoff=handoff)

    findings = _findings(tmp_path, plan_with(task_block()), {"earlier-work": record})

    assert any("`AUD-feature-1` has no owner" in finding for finding in findings)


def test_a_claimed_note_is_not_an_orphan(tmp_path: Path) -> None:
    handoff = (
        "| Note | Kind | Owner |\n| --- | --- | --- |\n"
        "| `AUD-feature-1` | blocking | [Feature](../plan.md#build-feature), routed |\n"
    )
    record = record_text("earlier-work", snapshot=task_block("earlier-work"), handoff=handoff)
    audit = "- Audit inputs: [AUD-feature-1](records/earlier-work.md#audit-handoff).\n"
    plan = plan_with(task_block(extra_fields=audit))

    assert _findings(tmp_path, plan, {"earlier-work": record}) == []
