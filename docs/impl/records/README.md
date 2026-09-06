# Task Records

Copy the [template](template.md) to `<task-id>.md` at task start and index it here. Records preserve
full scope and evidence after [plan](../plan.md) removal; [current state](../current.md) links them.
See [record rules](../../guide/planning-workflow.md#durable-task-records) for amendments and legacy work.
Record results remain understandable without private runtime artifacts; unavailable evidence is explicit.

| Record | Scope | Result |
| --- | --- | --- |
| [Codebase and workflow audit](codebase-and-workflow-audit.md) | Read-only implementation review, future refactoring/checkpoints, handoff rules and README | Review/docs present; the baseline CI block is resolved; the other identified code repairs remain open |
| [Compact agent instructions](compact-agent-instructions.md) | Reduce repeated rules and required context; retain gates and handoffs | Documentation review; verification in record |
| [Quality baseline repair](restore-quality-gate-baseline.md) | Repair runtime import formatting and split the Compose topology test at invariant boundaries | Accepted; `make ci` and `make quality` pass with all invariants retained |
