from pathlib import Path

SPEC = """# Design

## Capability Registry

| # | Capability | Status | How it is evaluated | Implementation |
| --- | --- | --- | --- | --- |
| 1 | `foundation` | shipped | Fresh setup passes | [Foundation](../impl/current.md) |
| 2 | `feature` | planned | Fixture behavior passes | - |
"""

NO_NOTES = "`none identified` for the reviewed scope."


def task_block(
    identifier: str = "build-feature",
    *,
    capability: str = "feature",
    status: str = "CLEAR",
    optional: bool = False,
    dependencies: str = "none.",
    checkpoint: str = "none; task-local review only.",
    extra_fields: str = "",
) -> str:
    suffix = " (optional)" if optional else ""
    return f"""#### {identifier}{suffix}

Describe future product behavior.

- Serves: `{capability}` -- [Feature](../design/spec.md#feature)
- Agent status: {status}
{extra_fields}- Dependencies: {dependencies}
- User-visible outcome: A user can exercise the feature.
- Scope boundary: The fixture path only; deployment is outside scope.
- Data and artifact paths: `tests/fixtures/` only.
- Execution path: Add a module and deterministic tests.
- Acceptance gates: `make ci` passes or the negative result is recorded.
- Documentation target: [Current state](current.md).
- Review checkpoint: {checkpoint}
"""


def checkpoint_block(identifier: str = "review-feature", *, dependencies: str = "none.") -> str:
    return task_block(
        identifier,
        dependencies=dependencies,
        extra_fields="- Task kind: checkpoint\n",
    )


def record_text(
    identifier: str = "build-feature",
    *,
    state: str = "accepted after the required gates below passed.",
    snapshot: str | None = None,
    evidence: bool = True,
    handoff: str = NO_NOTES,
) -> str:
    body = f"""# Record

## Task and scope

- Id: `{identifier}`; capability: `feature`.
- State: {state}
- Accepted task:
"""
    if snapshot is not None:
        body += f"\n```markdown\n{snapshot}```\n"
    body += "\n## Acceptance evidence\n\n"
    if evidence:
        body += (
            "| Gate | Command | Result |\n| --- | --- | --- |\n"
            "| Deterministic tests | `make ci` | pass |\n"
        )
    else:
        body += "No table is recorded here.\n"
    return f"{body}\n## Audit handoff\n\n{handoff}\n"


def plan_with(*blocks: str, human_blocks: tuple[str, ...] = ()) -> str:
    agent_content = "\n".join(blocks) if blocks else "No open agent tasks."
    human_content = "\n".join(human_blocks) if human_blocks else "No open human tasks."
    return f"""# Plan

## Agent Implementation Tasks

### Feature -- `feature`

{agent_content}

## Human-Assisted Tasks

### Feature -- `feature`

{human_content}
"""


def write_project(
    root: Path,
    *,
    spec: str = SPEC,
    plan: str | None = None,
    records: dict[str, str] | None = None,
    index: dict[str, str] | None = None,
) -> Path:
    (root / "docs/design").mkdir(parents=True)
    records_dir = root / "docs/impl/records"
    records_dir.mkdir(parents=True)
    (root / "docs/design/spec.md").write_text(spec, encoding="utf-8")
    resolved_plan = plan if plan is not None else plan_with(task_block())
    (root / "docs/impl/plan.md").write_text(resolved_plan, encoding="utf-8")
    stored = records or {}
    for name, text in stored.items():
        (records_dir / f"{name}.md").write_text(text, encoding="utf-8")
    listed = stored if index is None else index
    rows = "".join(f"| [{name}]({name}.md) | scope | result |\n" for name in listed)
    (records_dir / "README.md").write_text(
        f"# Task Records\n\n| Record | Scope | Result |\n| --- | --- | --- |\n{rows}",
        encoding="utf-8",
    )
    return root
