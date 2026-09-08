# Codebase Review and Development Handoffs

The implementation review found useful, mostly cohesive foundation modules and concrete boundary
defects that should be repaired before building on them. It did not justify a package-wide rewrite.
Production code, tests, dependencies, operator configuration, and archives are unchanged by this
review. The [task record](../../records/0001-govern-codebase-and-workflow-audit.md) retains the full
request, review scope, reproducible findings, decisions, and remaining gate failures.

## Implementation scope inspected

The review traced CLI/Make entry points through runtime configuration, dotenv expansion, protected
paths, Compose planning/reset, and readiness transports. It also inspected contract registry/
canonical/evolution/fingerprint primitives, evaluation bundles and metrics, retrieval metrics,
stage/extraction/store interfaces, feature declarations, model placement, logging, quality parsers,
and their relevant tests. The package has no concrete directory-to-report runner yet; missing
domain stages remain planned capability work rather than defects in a running pipeline.

Nine synthetic reproductions confirm gaps in reset ancestor protection, readiness report write
protection, database credential transport, installed-extension checks, bundle symlink validation,
canonical reference containment, schema-qualified field identity, shell/Python derived values, and
multiline plan parsing. Only disposable fixtures and fake probe transports were used. The reset
reproduction calls `apply=False`; no real service was stopped or data erased. Additional static
observations about endpoint handling, duplicated profile policy, interface shape, scheduling and
queue bounds are explicitly distinguished from reproduced failures in the record.

## Future repairs and checkpoints

The [forward plan](../../plan.md) retains focused refactoring and enforcement work before affected
consumers. Completed foundation repairs are linked from current-state pages and accepted records:
shared root policy, configuration parity, profile-aware service planning, probe safety, contract
identity/reference validation, and durable-record/dependency checks. Typed stage and artifact
interfaces are [record 0040](../../records/0040-pipeline-refactor-stage-and-artifact-interface-contracts.md).
Host-wide GPU scheduling is
[record 0032](../../records/0032-inference-implement-model-resource-scheduler.md). Evidence bundle
validation is [record 0033](../../records/0033-eval-found-refactor-evaluation-bundle-validation.md).
Remaining telemetry tasks own their implementation gaps, avoiding duplicate backlog entries.

Seven finite checkpoints review foundation/store, corpus/control, knowledge/identity,
investigation/report, production/recovery, selected semantic retrieval, and archive organization.
Each declares inputs, invariants, evidence, a downstream gate, and a valid no-refactor-needed
outcome. A blocking finding requires a separate repair task before code changes, and keeps its
checkpoint open. Early checkpoints accept deterministic integration evidence; unavailable private
labels do not block otherwise independent fixture implementation. A fixture verdict never replaces
real-data, CUDA, promotion, or placement acceptance.

## Durable workflow available now

[AGENTS.md](../../../../AGENTS.md), the [planning workflow](../../../guide/planning-workflow.md), and
the [record template](../../records/template.md) now require complete accepted task snapshots,
preserved scope amendments, exact requirement-to-evidence results, implementation decisions, and
audit handoffs. Small-budget implementation runs take one bounded task without reducing its gates.
Before removal from the forward plan, current state links the accepted record and dependents link
the retained prerequisite. Interrupted work remains open with evidence and a next action. Missing
historical task text is marked unavailable rather than reconstructed as fact.

Audit notes distinguish observations from hypotheses and name evidence, impact, next check, owner
and disposition. Current summaries link records instead of losing those details or becoming a
second queue. New review rounds use new ids when later changes expose integration risk. Routine
self-review remains part of every task; model choice alone supplies no quality guarantee.

These are documentation requirements available now. The parser ignored continuation lines and
`make plan-status` reported priority without checking dependency readiness when this review ran;
[record and checkpoint integrity](../../records/0004-foundation-enforce-task-record-and-checkpoint-integrity.md)
has since added record, note, dependency-cycle and checkpoint enforcement. The integrity checker
was not extended by this review itself.

The [README quickstart](../../../../README.md#quick-start) now has ordered tables for prerequisites,
environment, host inference, locked extras, services, and readiness; a separately labelled target
sequence covers forecasting through reports, catalogs, graphs, anomalies and source drill-down.
Archive copy/move organization remains a separate planned utility. The available/planned distinction
is explicit throughout; no pipeline execution is claimed by these examples.

## Plan transition

Open tasks changed from **77 to 93**: agent tasks **66 to 82**, human-assisted tasks **11 to 11**.
No implementation task was completed or removed, and no capability changed delivery status.
The registry remains at 20 capabilities, with two shipped foundations. Groups retain registry
order; refactoring prerequisites precede affected implementation, and checkpoints gate their
named consumers. Classification review feeds investigation; archive placement remains independent.

| Capability | Before | After | Added scope |
| --- | --- | --- | --- |
| `project-foundation` | 0 | 2 | CI baseline and record/dependency enforcement |
| `portable-runtime` | 0 | 4 | Root, configuration, service-planning and probe repairs |
| `contract-governance` | 5 | 6 | Contract reference and field identity repair |
| `canonical-store` | 3 | 4 | Foundation/store checkpoint |
| `evaluation-foundation` | 1 | 2 | Evidence bundle validation repair |
| `pipeline-control` | 9 | 11 | Typed interface refactor and corpus/control checkpoint |
| `identity-ontology-graph` | 4 | 5 | Knowledge/identity checkpoint |
| `discovery-visualization` | 7 | 8 | Investigation/report checkpoint |
| `operational-recovery` | 4 | 5 | Production/recovery checkpoint |
| `semantic-retrieval` | 3 | 4 | Selected semantic branch checkpoint |
| `archive-organization` | 4 | 5 | Placement integrity checkpoint |

## Verification

The audit artifacts live under `.data/codebase-review/20260905/`, using an explicit
`DATA_DIR=.data` override because the configured tooling volume is read-only. The operator's `.env`
was not modified. `reproduce.py` and `findings.json` retain the nine local cases; the task record
names the corresponding source paths, impacts and future owners.

Markdown, documentation links, spec-plan integrity and whitespace checks pass. An independent
multiline dependency review covers 93 tasks and 241 explicit edges including conditional branches,
with no cycles, duplicate fields or missing checkpoint references. The four early checkpoints have
no human task in their prerequisite closures. This is an audit result, not a shipped checker feature.

`make -k ci DATA_DIR=.data` reports 168 passing tests and passing typing/shell/documentation checks,
but still fails on pre-existing import formatting/order in `runtime/__init__.py` and Radon D (23)
in the combined Compose topology test. The subsequent cognitive-complexity subcheck is not reached.
Those unchanged failures now have a focused repair task; this review does not waive the CI gate.
The
[record](../../records/0001-govern-codebase-and-workflow-audit.md#final-verification-and-next-action)
retains exact commands, outcomes and limits. Runtime services, model/CUDA jobs and provided-archive
runs were not started. No archive-quality, throughput, model-fit or security-certification claim is
made.
