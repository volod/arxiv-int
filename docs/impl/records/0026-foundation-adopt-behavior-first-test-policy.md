# Adopt Behavior-First Test Policy

## Task and scope

- Id / capability / checkpoint: `adopt-behavior-first-test-policy` / `project-foundation` /
  `review-foundation-and-store-boundaries`
- State: accepted
- Source: ad hoc operator request (2026-09-06) to replace the numeric coverage floor during
  development; not a previously listed plan task. Dirty scope at start includes unrelated
  projection, corpus, and evolution files that this task does not absorb.
- Initial count: 77 tasks (67 agent, 10 human); next agent task
  `review-foundation-and-store-boundaries`.
- Accepted task:

```markdown
#### adopt-behavior-first-test-policy

Replace the numeric test-coverage floor with tests for integrity, correctness, and business logic.

- Serves: `project-foundation` --
[Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Quality baseline repair](records/0003-foundation-restore-quality-gate-baseline.md);
[0004](records/0004-foundation-enforce-task-record-and-checkpoint-integrity.md).
- User-visible outcome: Implementation tasks are accepted when happy-path and main corner-case tests
cover integrity, correctness, and business logic. Milestone checkpoints add tests for important
stabilized cases. A coverage percentage does not fail quality workflows.
- Scope boundary: Change the specified test policy, coverage reporting gate, agent instructions, and
existing milestone checkpoint fields. Do not add a parallel audit mill, restore a numeric floor, or
run a named checkpoint in this change.
- Data and artifact paths: `docs/design/spec.md`, `docs/impl/plan.md`, `docs/guide/`, `AGENTS.md`,
`Makefile`, `pyproject.toml`, `docs/impl/current/`, `tests/quality/`, and
`$DATA_DIR/quality-policy/<run-id>/`.
- Execution path: Amend development-integrity and checkpoint review rules; remove the coverage
percentage failure threshold while keeping a diagnostic coverage report; point each remaining
milestone checkpoint at deepening tests for important stabilized cases.
- Acceptance gates: Specification and plan describe behavior-first tests; `make coverage` and
`make quality` report coverage without failing on a percentage; `make ci` and documentation-link /
spec-plan lints pass. Restoring `fail_under` is a regression.
- Documentation target: `docs/impl/current/developer-tooling.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: operator follow-up (2026-09-06): do not add a coverage-policy test or other tests
that freeze current implementation or historical policy; keep the suite as a specification of
integrity, correctness, and business logic; do not grow incidental coverage.

```markdown
#### adopt-behavior-first-test-policy

Replace the numeric test-coverage floor with tests for integrity, correctness, and business logic.

- Serves: `project-foundation` --
[Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Quality baseline repair](records/0003-foundation-restore-quality-gate-baseline.md);
[0004](records/0004-foundation-enforce-task-record-and-checkpoint-integrity.md).
- User-visible outcome: Implementation tasks are accepted when happy-path and main corner-case tests
cover integrity, correctness, and business logic. Milestone checkpoints add tests for important
stabilized cases. A coverage percentage does not fail quality workflows.
- Scope boundary: Change the specified test policy, coverage reporting gate, agent instructions, and
existing milestone checkpoint fields. Do not add coverage-policy tests, implementation snapshots,
or a parallel audit mill. Do not restore a numeric floor or run a named checkpoint in this change.
- Data and artifact paths: `docs/design/spec.md`, `docs/impl/plan.md`, `docs/guide/`, `AGENTS.md`,
`Makefile`, `pyproject.toml`, `docs/impl/current/`, and `$DATA_DIR/quality-policy/<run-id>/`.
- Execution path: Amend development-integrity and checkpoint review rules; remove the coverage
percentage failure threshold while keeping a diagnostic coverage report; point each remaining
milestone checkpoint at deepening tests for important stabilized cases. Do not add tests that only
encode the policy change or freeze current files.
- Acceptance gates: Specification and plan describe behavior-first tests; `make coverage` and
`make quality` report coverage without failing on a percentage; `make ci` and documentation-link /
spec-plan lints pass.
- Documentation target: `docs/impl/current/developer-tooling.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

## Implementation

Removed `[tool.coverage.report] fail_under = 90` so `make coverage` and `make quality` still emit
a diagnostic report but no longer fail on a percentage. `make ci` is unchanged. AGENTS, the
development guide, and developer-tooling/project-foundation current pages describe the gate.

The seven remaining milestone checkpoints now add tests for important stabilized integrity,
correctness, and business-logic cases, or record that existing tests already cover them. A
coverage percentage is not a checkpoint gate. Missing important cases may still spawn a focused
prerequisite refactor task; empty deepen-tests tasks were not pre-planned.

A coverage-policy unit test was not kept: it would freeze configuration rather than product
behavior. Current-state pages: [Developer tooling](../current/developer-tooling.md) and
[Project foundation](../current/project-foundation.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Spec and plan | `docs/design/spec.md` development integrity; seven checkpoint fields in `docs/impl/plan.md` | pass; behavior-first tests; no numeric floor |
| Coverage report has no percentage failure | `pyproject.toml` `[tool.coverage.report]` has no `fail_under` | pass |
| `make ci` | `make ci` | pass; 727 passed, 13 skipped |
| Documentation and spec-plan lints | included in `make ci` | pass; 0 broken links; 0 spec-plan findings |
| `make quality` | `make quality` | pass; diagnostic coverage 91%; lint-md; wheel |

## Audit handoff

`none identified`. Reviewed spec, plan checkpoints, AGENTS, Make/pyproject gates, and current-state
quality pages. Did not run `review-foundation-and-store-boundaries`. Unrelated dirty files were
not absorbed.

## Close or resume

Accepted. The numeric coverage floor is gone; tests are specified as integrity, correctness, and
business logic. Milestone checkpoints own deepening once a stage stabilizes. Plan counts remain
77 (67 agent, 10 human). Next agent task is still `review-foundation-and-store-boundaries`.
`project-foundation` stays shipped; no capability status changed. Unrelated dirty files were not
absorbed.
