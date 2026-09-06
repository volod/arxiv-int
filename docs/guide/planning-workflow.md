# Planning Workflow

[AGENTS.md](../../AGENTS.md) gives the normal task cycle. Read only the section needed here.

## Task shape

Before adding or changing capability scope, follow [capability changes](#capability-changes).
For tasks, use a stable slug, the owning capability group, and all fields below:

```markdown
### Capability name -- `capability-id`

#### stable-task-id

State the unresolved operator problem. Append `(optional)` to the heading only for a refinement.

- Serves: `capability-id` -- [Owning spec section](../design/spec.md#section)
- Agent status: CLEAR
- Dependencies: Open task ids or accepted record links; state conditional branches explicitly.
- User-visible outcome: What becomes possible or trustworthy.
- Scope boundary: Included and excluded behavior.
- Data and artifact paths: Repository-relative paths or configured artifact roots.
- Execution path: Modules, fixtures, commands and declared runs.
- Acceptance gates: Checks, acceptance signal and valid negative result.
- Documentation target: Narrow current-state page.
- Review checkpoint: Owning checkpoint id or record; new round for late integration risks.
```

Use `Task kind: refactor` or `Task kind: checkpoint` when applicable. `Research: yes` allows a
supported negative result; it does not replace status or acceptance gates.

## Task lanes

| Lane | Status | Acceptance needs |
| --- | --- | --- |
| Agent Implementation Tasks | `CLEAR` | Local code, tests and docs |
| Agent Implementation Tasks | `RUN NEEDED` | A declared heavier run |
| Human-Assisted Tasks | `BLOCKED BY HUMAN` | Unavailable human-provided input/access |
| Human-Assisted Tasks | `HUMAN-GATED` | Human judgment, authorization or spending authority |

## Ordering

Follow registry order in both lanes. Within each capability: prerequisites, changed downstream
inputs, required before optional work, cheap deterministic work before expensive runs. Reorder the
registry and both lanes together when priority changes.

Dependencies must resolve to open tasks or accepted records, with no cycles. Write full multiline
fields and mark conditional dependencies with an explicit branch word so they order nothing.
`make lint-spec-plan` enforces dependency, record, note and checkpoint resolution; `make plan-status`
reports the next task whose prerequisites are met. Fix docs, not the checker.

## Capability changes

1. State the operator problem; amend its owning spec section with behavior, exclusions, evaluation,
   acceptance signal and valid negative result. Correct a misshaped capability before adding code.
2. For a new capability, add a registry row marked `planned`, then tasks in registry order.
3. Every task serves its group; every capability declares evaluation; every planned capability has
   open work. When fully accepted, mark it `shipped` and link current-state implementation docs.

Handle necessary chores and task-local review now. Schedule further capability work once; use a
checkpoint for a cross-task concern. Never put completion notes, dates, measurements or history in
`plan.md`; link a prerequisite fact or accepted record without restating it.

## Durable task records

Copy the [template](../impl/records/template.md) at task start; add the record to its
[index](../impl/records/README.md). Keep the full original task and full amendments after plan removal.
Records retain evidence and decisions; current pages describe available behavior and link records.
Future actions belong in the plan, with one owner per note. Keep private source data out of docs.
If historical task text cannot be recovered, mark it unavailable; never fabricate it.

## Audit notes and milestone reviews

Self-review every task. Record `none identified` or evidence-bearing notes using the record template.
A concern outside task scope gets one owner: a blocking prerequisite repair task, or a named future
checkpoint for nonblocking concerns. Plan the repair before implementation; do not broaden the task.

Run a checkpoint after its inputs pass and before gated consumers start. Read producer records,
affected code/tests, proofs and routed notes. Reconcile every note; record coverage, evidence,
refactor/no-refactor verdict, and `proceed`, `proceed-with-nonblocking-notes`, or `blocked`.
A blocker keeps the checkpoint open until its separate repair passes. Do not refactor without need.

Early checkpoints use deterministic integration evidence; inspect real-data proofs when available.
Their fixture verdict enables implementation, not real-corpus/CUDA promotion or physical placement.
Keep proof/human gates separate; missing private labels do not block independent fixture work.

Create a bounded review round for changed public contracts, duplicated policy, repeated regressions,
or integration risk after a checkpoint closes. Use a new id, explicit inputs/gates and a prior-record
link. Do not create generic recurring audits or infer quality from model choice.

## Completion transition

Follow the AGENTS task cycle. Before plan removal, map every gate to evidence, resolve or route every
note, link the accepted record from current state, and replace references to the removed task.
Update indexes and capability status where applicable. Failed acceptance leaves the task open;
retain partial results and the next action. Records are permanent evidence, not a second backlog.
