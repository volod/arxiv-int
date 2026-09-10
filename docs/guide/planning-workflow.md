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
Add `Human review handoff` to every agent task that produces or assembles human-evaluation inputs;
use the [handoff contract](#human-review-handoffs) below. The field is a forward handoff, not a
dependency on the approval it enables.

Archive integration and dataset tasks name the configured roots their ordinary artifacts occupy,
the integration test, and the run/manifest fingerprints a reviewer checks. Extra cross-checks stay
under `tests/integration/`; do not add a production proof publisher or parallel manifest. Tasks
commit no source-derived fixture, label, answer, figure or metadata; see
[published proof and evaluation data](../design/spec.md#published-proof-and-evaluation-data).
Name the implementation prerequisite, the presence/checksum/contract checks a reviewer runs in place,
and the resulting fingerprint. Committed fixtures are synthetic and must preserve the pinned
ontology, geotemporal and domain relationships they exercise on their own terms, never by copying
archive content.

## Task lanes

| Lane | Status | Acceptance needs |
| --- | --- | --- |
| Agent Implementation Tasks | `CLEAR` | Local code, tests and docs |
| Agent Implementation Tasks | `RUN NEEDED` | A declared heavier run |
| Human-Assisted Tasks | `BLOCKED BY HUMAN` | Unavailable human-provided input/access |
| Human-Assisted Tasks | `HUMAN-GATED` | Human judgment, authorization or spending authority |

### Human review handoffs

Mark every producer of a human task's required artifacts, including draft contributors and the
integration/checkpoint task that assembles the final packet. Use explicit human task links; the
human task's `Dependencies` lists the producer ids and all required earlier human decisions. An
integration task must not depend on approval of the packet it creates. Fixture builders may use
visibly proposed policies; promotion, accepted-output integration, scale or placement consumers
carry the actual approval dependency. Conditional viewer/semantic/move requirements stay explicit.

Each `Human review handoff` names:

- the human task id and the packet path under the existing run/review or acceptance root;
- the producer's contribution and whether it completes the packet or leaves other inputs pending;
- the decision requested, inspection/reproduction instructions and downstream tasks that must wait.

The complete packet includes immutable artifact/code/contract/model/ontology/policy fingerprints,
scope and coverage, validation/metric results, representative positive/negative/ambiguous cases,
candidate thresholds or inclusion rules, residual gaps and costs, and the decision-record location.
Prepare everything the agent can produce before requesting judgment. If another prerequisite or
decision is missing, report it explicitly; a useful draft is not a ready approval packet.
Changed inputs make an earlier decision stale for the changed scope. Record the new review rather
than silently carrying approval forward. Human review packets stay under the configured run and
review roots with the operator's own data; nothing from them is committed.

At completion, the agent's final response must include this concrete handoff for each marked task:

```text
Human review required: <human-task-id and title>
Status: ready | pending <named inputs/decisions> | stale | not-applicable <branch reason>
Review: <packet path, fingerprint, and command or entry point>
Decision: <specific accept/revise/reject or authorized alternatives; decision-record path>
Blocked next work: <task ids and the scope that must wait>
```

Also record the handoff in the task record and rerun `make plan-status`. Report the actual next
eligible task, not a presumed one. A passed producer/checkpoint is not a human decision. Do not
continue a dependent agent task or execute a placement/full-corpus action before its required
decision exists for the same fingerprints. Independent eligible work may continue; do not claim
the whole plan is blocked when only one branch waits. If no agent successor is planned, name the
blocked operation (for example full-corpus execution) without inventing another implementation task.

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

Copy the [template](../impl/records/template.md) at task start into a sequenced filename; add the
record to its [index](../impl/records/README.md). Keep the full original task and full amendments
after plan removal. Records retain evidence and decisions; current pages describe available behavior
and link records. Future actions belong in the plan, with one owner per note. Keep private source
data out of docs. If historical task text cannot be recovered, mark it unavailable; never fabricate
it.

### Record file naming

Filenames are `NNNN-<group>-<task-id>.md` so a directory listing sorts by implementation order and
still shows capability group and stable task slug.

1. **Sequence (`NNNN`)** -- four zero-padded digits. At task start, take
   `max(existing sequences) + 1` under `docs/impl/records/` (or `0001` when none exist). Never reuse
   or renumber a sequence after the file is created; gaps from abandoned drafts are allowed.
2. **Group** -- short abbrev for the owning capability (or `govern` for cross-cutting governance /
   instruction / audit work). Use the table below; add a row when a new capability enters the
   registry. `make lint-spec-plan` rejects unknown group tokens.
3. **Task id** -- the unchanged plan slug (`implement-deterministic-schema-generation`). The record
   body `Id:` field must match this suffix.
4. **Links** -- point at the full filename, for example
   `records/0011-contract-gov-implement-deterministic-schema-generation.md`. Dependency resolution
   keys on the task-id suffix, so labels can stay human-readable.
5. **Helpers** -- `arxiv_int.quality.record_naming.next_record_sequence` and `build_record_filename`
   encode the same rules for tooling and tests.

| Capability id | Group abbrev |
| --- | --- |
| `project-foundation` | `foundation` |
| `portable-runtime` | `runtime` |
| `contract-governance` | `contract-gov` |
| `canonical-store` | `store` |
| `local-inference` | `inference` |
| `evaluation-foundation` | `eval-found` |
| `pipeline-control` | `pipeline` |
| `corpus-foundation` | `corpus` |
| `lexical-retrieval` | `lexical` |
| `archive-classification` | `archive-cls` |
| `russian-nlp` | `rus-nlp` |
| `identity-ontology-graph` | `identity` |
| `knowledge-extraction` | `knowledge` |
| `domain-investigation-artifacts` | `domain` |
| `anomaly-analysis` | `anomaly` |
| `discovery-visualization` | `discovery` |
| `evaluation-evidence` | `eval-evid` |
| `operational-recovery` | `ops` |
| `semantic-retrieval` | `semantic` |
| `archive-organization` | `archive-org` |
| `governance` (meta / audit / instructions) | `govern` |

## Audit notes and milestone reviews

Self-review every task. Record `none identified` or evidence-bearing notes using the record template.
A concern outside task scope gets one owner: a blocking prerequisite repair task, or a named future
checkpoint for nonblocking concerns. Plan the repair before implementation; do not broaden the task.

Run a checkpoint after its inputs pass and before gated consumers start. Read producer records,
affected code/tests, proofs and routed notes. Reconcile every note; record coverage, evidence,
refactor/no-refactor verdict, and `proceed`, `proceed-with-nonblocking-notes`, or `blocked`.
A blocker keeps the checkpoint open until its separate repair passes. Do not refactor without need.
Checkpoints also add tests for important stabilized integrity, correctness, and business-logic
cases in the stage when existing tests do not already cover them. A numeric coverage percentage is
not an acceptance signal. Existing happy-path and main-corner coverage is a valid
no-additional-tests conclusion.

Early checkpoints use deterministic integration evidence; inspect real-data integration results
when available.
Their fixture verdict enables implementation, not real-corpus/CUDA promotion or physical placement.
Keep integration/human gates separate; missing private labels do not block independent fixture work.

Create a bounded review round for changed public contracts, duplicated policy, repeated regressions,
or integration risk after a checkpoint closes. Use a new id, explicit inputs/gates and a prior-record
link. Do not create generic recurring audits or infer quality from model choice.

Place reviews before the first consumer of a newly integrated boundary, including before expensive
proofs or scale pilots when their prerequisite behavior can be checked cheaply. Name exact producers,
cross-module invariants, positive/main-corner/negative evidence and gated consumers. Add required
`Dependencies` edges to those consumers: a producer's `Review checkpoint` field alone is not a gate.
Do not make a checkpoint depend on the consumer it must release. Dynamic ontology snapshots,
geotemporal interpretation and domain distinctions are integration invariants, not a reason to add
an unrelated ontology learner or GIS stack.

## Completion transition

Follow the AGENTS task cycle. Before plan removal, map every gate to evidence, resolve or route every
note, link the accepted record from current state, and replace references to the removed task.
Update indexes and capability status where applicable. Failed acceptance leaves the task open;
retain partial results and the next action. Records are permanent evidence, not a second backlog.
