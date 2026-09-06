from pathlib import Path

from arxiv_int.quality.plan_model import (
    fenced_blocks,
    parse_task_block,
    read_registry,
    read_tasks,
)
from tests.quality._plan_fixture import SPEC, plan_with, task_block, write_project


def test_registry_and_task_metadata_are_parsed(tmp_path: Path) -> None:
    root = write_project(tmp_path)

    registry = read_registry(root / "docs/design/spec.md")
    tasks = read_tasks(root / "docs/impl/plan.md")

    assert [capability.identifier for capability in registry] == ["foundation", "feature"]
    assert registry[0].status == "shipped"
    assert [(task.identifier, task.serves, task.agent_status) for task in tasks] == [
        ("build-feature", "feature", "CLEAR")
    ]


def test_fenced_task_examples_are_not_parsed(tmp_path: Path) -> None:
    plan = plan_with(task_block()) + "\n```markdown\n#### example-task\n```\n"
    root = write_project(tmp_path, plan=plan)

    assert [task.identifier for task in read_tasks(root / "docs/impl/plan.md")] == ["build-feature"]


def test_only_the_capability_registry_table_is_parsed(tmp_path: Path) -> None:
    spec = (
        SPEC
        + """

## Another table

| # | Capability | Status | How it is evaluated | Implementation |
| --- | --- | --- | --- | --- |
| 3 | `ignored` | planned | Other | - |
"""
    )
    root = write_project(tmp_path, spec=spec)

    assert [item.identifier for item in read_registry(root / "docs/design/spec.md")] == [
        "foundation",
        "feature",
    ]


def test_multiline_fields_keep_their_continuation_lines(tmp_path: Path) -> None:
    plan = plan_with(task_block(dependencies="`first-task`;\n`second-task`."))
    root = write_project(tmp_path, plan=plan)

    task = read_tasks(root / "docs/impl/plan.md")[0]

    assert task.fields["dependencies"] == "`first-task`;\n`second-task`."


def test_a_repeated_field_is_recorded(tmp_path: Path) -> None:
    plan = plan_with(task_block(extra_fields="- Dependencies: `first-task`.\n"))
    root = write_project(tmp_path, plan=plan)

    task = read_tasks(root / "docs/impl/plan.md")[0]

    assert task.repeated_fields == ("dependencies",)


def test_a_fenced_snapshot_parses_back_into_a_task() -> None:
    snapshot = task_block("earlier-work", dependencies="`first-task`;\n`second-task`.")

    task = parse_task_block(snapshot)

    assert task is not None
    assert task.identifier == "earlier-work"
    assert task.fields["dependencies"] == "`first-task`;\n`second-task`."
    assert parse_task_block("no heading here") is None


def test_fenced_blocks_are_returned_by_language() -> None:
    text = "intro\n\n```markdown\n#### kept\n```\n\n```bash\nignored\n```\n"

    assert fenced_blocks(text, "markdown") == ["#### kept"]
