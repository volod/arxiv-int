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
| [Record and checkpoint integrity](enforce-task-record-and-checkpoint-integrity.md) | Preserve full task fields, resolve dependencies against open tasks and accepted records, and validate records, notes and checkpoints | Accepted; `make ci` and `make quality` pass and the gate reports each defect class |
| [Safe runtime root boundaries](refactor-safe-runtime-root-boundaries.md) | Unify protected-root containment before any reset deletion or readiness-report write | Accepted; regressions cover reset containment, report destinations, derived aliasing and symlink swaps |
| [Runtime configuration parity](refactor-runtime-configuration-parity.md) | Resolve one configuration through Make, direct CLI and readiness without precedence drift | Accepted; `make ci` and `make quality` pass with paired shell/Python fixtures for precedence, references, invalid input and cache placement |
| [Profile-aware service planning](refactor-profile-aware-service-planning.md) | Shared service selection, pure commands and selected layout/readiness checks | Accepted; profile matrix regressions, `make ci` and offline `make quality` pass |
| [Readiness probe safety](refactor-readiness-probe-safety.md) | Secret-free commands, installed extensions and bounded local HTTP | Accepted; 304 tests, CI and full quality pass |
