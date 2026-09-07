# Checkpoints, Committed Proof Identities, and Human Handoffs

## Task and scope

- Id: `strengthen-checkpoints-and-human-proof-handoffs`; capability: `project-foundation`.
- State: accepted; the documentation and dependency gates below passed.
- Source: operator request after accepted records 0029-0033; clean working tree at
  `9790b07bde0c210356b29b58c223716a6b329b06`.
- Initial count: 73 tasks (63 agent, 10 human).
- Amendments: one, below.

```markdown
#### strengthen-checkpoints-and-human-proof-handoffs

Strengthen the remaining plan with timely integrity checkpoints, committed-proof identity
obfuscation requirements, and explicit agent-to-human artifact handoffs.

- Serves: `project-foundation` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Dependencies: [Foundation/store repair](records/0028-store-refactor-foundation-store-acceptance-boundaries.md);
[Archive roots](records/0029-runtime-retire-separate-proof-archive-root.md);
[Pandera compatibility](records/0030-contract-gov-upgrade-pandera-polars-concat-compat.md);
[Inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Resource scheduler](records/0032-inference-implement-model-resource-scheduler.md);
[Bundle validation](records/0033-eval-found-refactor-evaluation-bundle-validation.md).
- User-visible outcome: Important integrated boundaries are reviewed before their consumers proceed;
Git-bound proof artifacts use repeatable, type-correct identity substitutes; producers announce
reviewable human packets and name exactly which downstream work is blocked.
- Scope boundary: Update specification, remaining task formation, workflow instructions and current
workflow documentation. Preserve accepted 0029-0033 and their runtime behavior. Plan the exporter;
do not implement it, process source data, commit artifacts, or approve human policy decisions.
- Data and artifact paths: `AGENTS.md`, `docs/design/spec.md`, `docs/impl/plan.md`,
`docs/guide/planning-workflow.md`, current-state workflow/evaluation pages, and this record/index.
Tool evidence belongs under `$DATA_DIR/planning-review/0034/`.
- Execution path: Read the newer accepted records and current dependencies; add bounded checkpoint
contracts and required consumer edges; specify stable one-way identity obfuscation only for Git
exports; annotate producers with human tasks, packet paths, decisions and blocked consumers;
make human prerequisites explicit and require the agent's completion message to report handoffs.
- Acceptance gates: New checkpoints have named invariants, tests and downstream gates; every human
task has a producer handoff; no dependency cycles or self-gated evidence production; obfuscation
preserves local originals, formatting, joins and repeatability without strong-crypto scope;
`make format`, `make ci`, Markdown, link and spec/plan checks pass.
- Documentation target: `docs/impl/current/governance.md`
- Review checkpoint: none; bounded workflow change with manual dependency/handoff audit.
```

Operator constraints retained: records 0029-0033 are already implemented; obfuscation applies only
to artifacts under Git control, including person/company/product names, addresses, contacts and
account identifiers. Legally clean proof data permits a simple deterministic one-way hash; strong
cryptographic protection and resistance to reversal are outside scope. Human decisions remain human.

Operator amendment: "Please ensure that we handle dynamic ontology, geotemporal data, and domain
design properly within the current scope as well." Full revised task:

```markdown
#### strengthen-checkpoints-and-human-proof-handoffs

Strengthen the remaining plan with timely integrity checkpoints, committed-proof identity
obfuscation requirements, and explicit agent-to-human artifact handoffs.

- Serves: `project-foundation` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Dependencies: [Foundation/store repair](records/0028-store-refactor-foundation-store-acceptance-boundaries.md);
[Archive roots](records/0029-runtime-retire-separate-proof-archive-root.md);
[Pandera compatibility](records/0030-contract-gov-upgrade-pandera-polars-concat-compat.md);
[Inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Resource scheduler](records/0032-inference-implement-model-resource-scheduler.md);
[Bundle validation](records/0033-eval-found-refactor-evaluation-bundle-validation.md).
- User-visible outcome: Important integrated boundaries are reviewed before their consumers proceed;
Git-bound proof artifacts use repeatable, type-correct identity substitutes; producers announce
reviewable human packets and name exactly which downstream work is blocked.
- Scope boundary: Update specification, remaining task formation, workflow instructions and current
workflow documentation. Preserve accepted 0029-0033 and their runtime behavior. Plan the exporter;
do not implement it, process source data, commit artifacts, or approve human policy decisions.
- Data and artifact paths: `AGENTS.md`, `docs/design/spec.md`, `docs/impl/plan.md`,
`docs/guide/planning-workflow.md`, current-state workflow/evaluation pages, and this record/index.
Tool evidence belongs under `$DATA_DIR/planning-review/0034/`.
- Execution path: Read the newer accepted records and current dependencies; add bounded checkpoint
contracts and required consumer edges; specify stable one-way identity obfuscation only for Git
exports; annotate producers with human tasks, packet paths, decisions and blocked consumers;
make human prerequisites explicit and require the agent's completion message to report handoffs.
Include dynamic ontology snapshots/evolution, geotemporal assertion semantics, and domain design
within existing identity, fact, graph and artifact capabilities; do not add an autonomous ontology
learner, external geocoder or GIS platform.
- Acceptance gates: New checkpoints have named invariants, tests and downstream gates; every human
task has a producer handoff; no dependency cycles or self-gated evidence production; obfuscation
preserves local originals, formatting, joins and repeatability without strong-crypto scope;
dynamic ontology, geotemporal and domain-design requirements have implementation and checkpoint
owners with positive/negative cases; `make format`, `make ci`, Markdown, link and spec/plan checks pass.
- Documentation target: `docs/impl/current/governance.md`
- Review checkpoint: none; bounded workflow change with manual dependency/handoff audit.
```

## Implementation

The specification now defines deterministic, typed identity obfuscation for Git-bound proof copies.
Local archive data, canonical outputs and human-review packets keep their original identities.
Versioned SHA-256 namespaces produce stable person/company/product labels and appropriately formatted
contact/address/account substitutes. Export must preserve references, domain relationships and
geotemporal meaning, rebuild anchors/checksums, detect collisions/leaks and leave originals unchanged.
The exporter is queued as `implement-committed-proof-identity-obfuscation`; it is not implemented by
this documentation task. Existing bundle validation remains unchanged.

Five new checkpoints have required edges before their first affected consumers:

| Checkpoint | Boundary and first gated consumers |
| --- | --- |
| `review-inference-and-evaluation-boundaries` | Inference leases/cancellation, metrics and immutable/exported evidence; stage/artifact interface integration |
| `review-pipeline-publication-and-reuse-boundaries` | File/database activation, cache lineage, interruption and concurrency; streaming inventory |
| `review-retrieval-and-classification-boundaries` | Source accounting, Russian text, ranking, hierarchy and exception consistency; lexical and classification proofs |
| `review-domain-artifact-and-triage-boundaries` | Domain relations, financial/BOM arithmetic, registry and review state; report interfaces and domain/anomaly proofs |
| `review-recovery-before-scale-pilots` | Restore/rebuild, policy and historical-result parity; representative scale pilots |

Existing corpus/control, knowledge/identity and production checkpoints retain their later scope and
consume the earlier reviews. Producer `Review checkpoint` labels now point to the appropriate early
review. Reviews require integrated positive/corner/negative evidence and blocking repairs before
their consumers proceed; they cannot substitute for CUDA, provided-archive or human acceptance.

The second queued implementation, `implement-ontology-snapshots-and-geotemporal-contracts`, owns
immutable ontology snapshots, draft/published separation, evolution compatibility and shared
source-valid/recorded time and location/CRS uncertainty contracts. Existing identity, extraction,
validation, graph, domain and report tasks consume those contracts. Knowledge/identity and domain
checkpoints test replay, stale snapshots, interval/effectivity boundaries and domain non-implications:
shared names, addresses, dates or amounts cannot establish identity, supply, part-of or settlement.
No capability was added and no runtime ontology/geospatial support is claimed by this record.

All 10 human tasks have explicit producer handoffs across 27 agent tasks. The fields name packets,
draft/final contributions, decisions and blocked consumers; human prerequisites use explicit task
ids. All 13 proof tasks declare a Git-bound export list or a no-export outcome. `AGENTS.md`, the
planning workflow and record template require completing agents to report packet readiness, the
inspection entry point, decision-record location and blocked next work. Independent eligible work
can continue while a branch waits for a human. `make plan-status` remains a dependency reporter;
the agent's completion report implements the notice requirement, not a new CLI feature.

Current workflow and evaluation documentation distinguish these requirements from implemented
behavior. Accepted records 0029-0033 and production code, contracts, ontology assets and tests were
preserved. Their existing evidence informs the added integration reviews without reopening them.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Baseline state | `git status --short`; `make plan-status`; records 0029-0033 | clean; 73 tasks; next agent is `create-evaluation-fixtures-and-metrics` |
| Formatting | `make format` | pass; 404 files unchanged; no runtime edits |
| Required CI | `make ci`; `$DATA_DIR/planning-review/0034/ci.log` | pass; 855 tests passed, 20 skipped; contract generation/evolution, disposable baseline DDL, migration, ontology, lint and typing checks passed |
| Documentation | `make lint-md lint-doc-links lint-spec-plan` | pass; zero broken links and zero spec/plan findings |
| Parsed dependency and handoff audit | `source scripts/shared/common.sh`, `arxiv_int_load_env`, then `uv run python "$DATA_DIR/planning-review/0034/dependency-handoff-audit.py"` | pass; 5 checkpoint gates, all 10 human tasks mapped to 27 producers, 13 proof export gates, no self-gated packets; JSON/text evidence in the same directory |
| Plan readiness | `make plan-status` | 80 tasks: 70 agent, 10 human; 79 blocked; next agent is `implement-committed-proof-identity-obfuscation` |
| Scope preservation | `git diff --check`; audit of changed paths and accepted records | pass; documentation/workflow only; 0029-0033 unchanged |

Manual review checked semantic ownership, packet readiness and the difference between forward
handoff links and prerequisite edges. The parsed-edge audit found two dependency continuations
separated by blank lines; these were repaired and required-edge assertions passed. Conditional
branches remain explicit and no producer depends on approval of its own packet. This proves the
planning structure and existing CI baseline, not implementation of the queued exporter or semantic
contracts, real-archive quality, model fit or human acceptance. Skipped tests remain skipped.

## Audit handoff

None identified as unresolved concerns in this bounded planning change. New implementation scope
has one owner per concern: the Git-bound exporter and ontology/geotemporal contract tasks; their
consumers and checkpoints own the corresponding integration acceptance. Human judgments remain in
their existing 10 human tasks. No review packet was produced or human decision requested by this task.

## Close or resume

All required gates passed. The ad hoc documentation task is accepted; it was never added to the
remaining-work list. The plan grows from 73 to 80 tasks: 63 to 70 agent tasks, with 10 human tasks
unchanged (five new checkpoints and two new implementation tasks). Capability statuses are unchanged.

Next eligible agent task: `implement-committed-proof-identity-obfuscation`. The newly queued tasks
remain unimplemented. No human task is ready solely because of this planning update; future marked
producers must emit the concrete handoff before dependent work continues. No commit or push was made.
