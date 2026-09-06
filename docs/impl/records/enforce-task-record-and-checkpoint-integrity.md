# Enforce Task Record and Checkpoint Integrity

## Task and scope

- Id: `enforce-task-record-and-checkpoint-integrity`; capability: `project-foundation`;
  checkpoint: `review-foundation-and-store-boundaries`.
- State: accepted after the required gates below passed.
- Source: [plan](../plan.md) task `enforce-task-record-and-checkpoint-integrity` at revision
  `e42ef3f` ("Merge pull request #1 from volod/ai-01-specs-tasks"). Working tree clean at start;
  no dirty scope.
- Audit input: [AUD-codebase-09](codebase-and-workflow-audit.md#audit-handoff).
- Accepted task:

```markdown
#### enforce-task-record-and-checkpoint-integrity

Make task handoff records and review dependencies verifiable instead of relying on summaries.

- Serves: `project-foundation` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: implementation
- Audit inputs: [AUD-codebase-09](records/codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Quality baseline repair](records/restore-quality-gate-baseline.md);
[Task records](records/README.md).
- User-visible outcome: Task requirements survive plan removal; missing evidence, unresolved review
blockers and dangling dependency ids cannot be mistaken for completed prerequisites.
- Scope boundary: Extend the existing plan parser/checker and summary; no task database, Git rewrite,
model selection automation, or fabricated records for old tasks.
- Data and artifact paths: `src/arxiv_int/quality/{plan_model,plan_integrity,plan_summary}.py`, `tests/quality/`,
`docs/impl/records/`, and `$DATA_DIR/governance-checks/<run-id>/`.
- Execution path: Preserve complete multiline fields and fenced accepted task snapshots; resolve dependencies
against open tasks or accepted records, distinguish conditional references, detect cycles, validate
record/checkpoint/note links and statuses, and make next-task output respect prerequisites.
- Acceptance gates: Regression fixtures cover lost continuation lines, dangling/archived ids, cycles,
conditional branches, missing snapshots/evidence, unresolved blocking notes and valid no-refactor reviews;
existing structure/order checks remain strict and make ci passes.
- Documentation target: `docs/impl/current/governance.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

The plan parser, a new dependency/reference resolver, a new record reader, the integrity gate and
the plan summary now share one model of the plan and its durable records. No product module,
service, dependency or operator environment changed.

`plan_model.py` reads a task heading and then its whole block: `parse_fields` appends every
continuation line to the field it belongs to, so a prerequisite named on a wrapped line survives
(`AUD-codebase-09`). A field declared twice is reported instead of silently merged. `fenced_blocks`
and `parse_task_block` reparse the fenced snapshot a record preserves, so an accepted task can be
checked with exactly the same code that checks an open one.

`plan_graph.py` (new) resolves references. A dependency field is split into clauses, and a clause
carrying a branch word -- `if`, `when`, `unless`, `only`, `optional`, `conditional`, `otherwise`,
`depending` -- marks its references conditional, so a selected branch orders nothing. A backtick
token is read as a task id only when it is hyphenated, which keeps recorded decision values such as
`apply` and `move` from being mistaken for tasks. Every reference must resolve to an open task or an
accepted record; self-dependencies and cycles over the remaining required edges are reported with
the full cycle. The same module resolves each `Review checkpoint` to a declared checkpoint task or
an accepted checkpoint record, and matches `Audit inputs` against record notes in both directions,
so a claim on an undeclared note and an unresolved note with no owning task are both findings.

`plan_records.py` (new) reads `docs/impl/records/`. Each record must declare its own id, a `State`,
and an index entry. An accepted record additionally needs its fenced snapshot (or an explicit
unavailable marker), at least one acceptance-evidence row, and an audit-handoff result; an accepted
checkpoint record must state a refactor verdict -- `no refactor needed` is valid -- and a
proceed-or-blocked decision. Records that are active or blocked are exempt from the accepted-only
requirements, so an in-progress record is not forced to invent evidence.

`plan_integrity.py` appends the four new finding groups to the existing ones; every previous
structure, status and ordering check is unchanged and still strict. `plan_summary.py` computes
blocking prerequisites and reports the first registry-priority task in each lane whose
prerequisites resolve, plus a `blocked by prerequisites` count; a lane where nothing is ready
reports `blocked` rather than naming unstartable work.

Two seams were split out rather than growing `plan_integrity.py` past the file-size guidance:
reference resolution across plan and records (`plan_graph.py`) and record reading with record
self-consistency (`plan_records.py`). Both live in the same package named by the task and are
reused by the integrity gate and the summary. Alternative considered and rejected: a task database
or an index file listing accepted tasks. The record files already carry that state, and a second
store would need its own integrity gate.

Detection of conditional wording is deliberately conservative: text that is not recognized as a
branch leaves the dependency required, so the gate over-orders rather than under-orders work.

Incidental repair: two trailing single spaces in the quoted request of
[compact agent instructions](compact-agent-instructions.md) failed `MD009` and blocked `make
quality`. Only the trailing whitespace was removed; the quoted wording is unchanged.

Current state: [Governance](../current/governance.md#product-state-transition).

## Acceptance evidence

Run id `20260906`; artifacts under `.data/governance-checks/20260906/` with an explicit
workspace-local `DATA_DIR=.data` override. `negative-cases.log` was produced by mutating a
throwaway copy of the repository's own `docs/` tree, one defect at a time, by the retained
`negatives.py`; the repository files were not modified by it. Each of its eleven cases yields
exactly the expected finding, and the unmutated tree yields none.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Lost continuation lines | `tests/quality/test_plan_model.py::test_multiline_fields_keep_their_continuation_lines`; `test_plan_graph.py::test_a_dependency_named_on_a_continuation_line_is_resolved`; `negative-cases.log` case `lost-continuation-line` | pass; the mutated real plan yields exactly one finding |
| Dangling and archived ids | `test_plan_graph.py::test_an_accepted_record_satisfies_a_dependency`, `::test_an_archived_but_unaccepted_record_cannot_satisfy_a_dependency`, `::test_a_task_cannot_depend_on_itself`; `negative-cases.log` cases `dangling-dependency`, `archived-record-dependency` | pass |
| Cycles | `test_plan_graph.py::test_a_required_dependency_cycle_is_reported`; `negative-cases.log` case `dependency-cycle` | pass; the finding names the full cycle |
| Conditional branches | `test_plan_graph.py::test_a_conditional_branch_does_not_order_tasks`, `::test_conditional_and_required_references_are_distinguished`, `::test_blocking_prerequisites_ignore_conditional_and_closed_work` | pass; unrecognized wording stays required, never optional |
| Missing snapshots and evidence | `test_plan_records.py::test_an_accepted_record_without_a_snapshot_is_reported`, `::test_an_accepted_record_without_evidence_is_reported`, `::test_a_snapshot_for_another_task_is_reported`; `negative-cases.log` cases `missing-accepted-snapshot`, `missing-acceptance-evidence` | pass |
| Unresolved blocking notes | `test_plan_graph.py::test_an_unresolved_note_without_an_owning_task_is_reported`, `::test_an_audit_input_must_name_a_declared_note`, `::test_a_claimed_note_is_not_an_orphan`; `negative-cases.log` cases `orphan-audit-note`, `undeclared-audit-note` | pass |
| Valid no-refactor reviews | `test_plan_records.py::test_a_no_refactor_checkpoint_verdict_is_accepted`, `::test_a_checkpoint_record_must_state_both_verdicts` | pass; a no-refactor verdict is accepted, a missing verdict is reported |
| Checkpoint and record links | `test_plan_graph.py::test_an_unknown_review_checkpoint_is_reported`, `::test_a_declared_checkpoint_task_resolves_its_consumers`; `test_plan_records.py::test_an_unindexed_record_is_reported`, `::test_a_record_filed_under_another_id_is_reported`, `::test_a_record_without_a_state_is_reported`; `negative-cases.log` cases `unknown-checkpoint`, `unindexed-record`, `record-without-state` | pass |
| Existing structure/order checks remain strict | `tests/quality/test_plan_integrity.py` and `test_plan_model.py` unchanged assertions, plus `lint-spec-plan.log` | pass; no previous check was removed or relaxed |
| Next-task output respects prerequisites | `tests/quality/test_plan_summary.py::test_next_work_respects_open_prerequisites`, `::test_a_fully_blocked_lane_reports_no_next_task`; `plan-status.log` | pass |
| Required CI gate | `make ci DATA_DIR=.data` (format, lint, typing, complexity, shell lint, doc links, spec-plan, tests) | pass, `ci.log`: 205 tests, up from 172 |
| Full local quality suite | `make quality DATA_DIR=.data` (ci-checks, coverage, `lint-md`, `build`) | pass, `quality.log`: 91.03% total coverage above the 90.0% floor, both sdist and wheel built |
| File-size guidance | `make quality-report` | pass for changed files, `quality-report.log`; the three files above 250 lines are pre-existing tests outside this scope |

No service, model, GPU, network or real-archive evidence is claimed; every check here reads
repository documents and fixtures only.

## Audit handoff

`none identified`. Reviewed scope: the five quality modules, their tests, and the plan/record
documents the gate reads. [AUD-codebase-09](codebase-and-workflow-audit.md#audit-handoff) is
resolved by this record: continuation lines are preserved, dependencies resolve against open tasks
and accepted records, cycles are detected, and `make plan-status` reports actual eligibility. The
audit's remaining code findings keep their existing owner tasks.

Two limits are recorded rather than routed, because neither is a defect in the accepted scope.
Conditional-branch detection is wording-based and conservative by design. The gate checks that
declared evidence exists and resolves; judging whether that evidence is sufficient stays with
task-local review and the milestone checkpoints.

## Close or resume

All required gates passed; none remain. Plan counts: 92 tasks before (81 agent, 11 human),
91 after (80 agent, 11 human); the now-empty `project-foundation` group heading was removed from the
agent lane. Capability change: none -- `project-foundation` was already `shipped` and this task
added a development gate, not product behavior.

Updated on acceptance: [Governance](../current/governance.md), the
[codebase review page](../current/governance/codebase-review.md), the
[planning workflow](../../guide/planning-workflow.md), the
[development integrity specification](../../design/spec.md#development-integrity-and-review-checkpoints),
the [task cycle](../../../AGENTS.md) and the [record index](README.md). The
[foundation checkpoint](../plan.md#review-foundation-and-store-boundaries) now depends on this
record instead of the removed task.

Next action: the plan's next agent task at the time,
[safe runtime root boundaries](refactor-safe-runtime-root-boundaries.md), since accepted.
No process, service or temporary scaffold remains; the logs under
`.data/governance-checks/20260906/` are retained as evidence.
