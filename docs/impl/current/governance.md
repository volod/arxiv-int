# Governance

## One rules source

`AGENTS.md` carries guardrails and one task cycle. It routes planning, checkpoint and setup details
only when needed. `CLAUDE.md`, `GEMINI.md`, `.codex`, and `.cursor/rules/project-rules.mdc` remain
thin links. README and contributor guidance follow the same conditional reading path.

The [instruction review record](../records/0002-govern-compact-agent-instructions.md) preserves scope,
rule-retention checks and measurements. AGENTS shrank from 169 lines/1,517 words to 53 lines/501
words; the record template from 508 to 237 words. Normal rules plus template require 738 words,
excluding the selected task, code and relevant spec/current sections. Planning guidance is optional
until its trigger applies. These are whitespace word counts, not model-specific token measurements.
No older-model compliance benchmark was run; the improvement is reduced context and branching.

The plan remains unchanged at 93 tasks (82 agent, 11 human); no capability moved. Documentation
checks and 168 tests pass; the formatting/import and Compose-complexity failures that full CI
still carried at that point were repaired later by the
[quality baseline repair](../records/0003-foundation-restore-quality-gate-baseline.md). Instruction reduction
does not waive those gates.

## Product state transition

`docs/design/spec.md` owns capabilities, boundaries, evaluations, delivery strategy, and registry
order. `docs/impl/plan.md` contains only work that remains and separates independent agent work from
human-gated acceptance. Status definitions, task shape, ordering rules, and completion mechanics
live in the planning workflow instead of being repeated in the plan. This current tree owns
available behavior and durable results.

`src/arxiv_int/quality/plan_integrity.py` parses the registry and plan. It rejects unknown or
misfiled capabilities, missing or repeated task fields, status-lane mismatches, missing evaluations
or current links, out-of-order groups, required tasks after optional tasks, malformed ids, and
historical plan language. `arxiv-int-plan` and `make plan-status` reuse the same parsed model to
report counts and, in each lane, the first registry-priority task whose prerequisites resolve.

`plan_model.py` keeps every continuation line of a multiline field and reparses the fenced task
snapshot a record preserves, so a prerequisite named on a wrapped line is no longer lost.
`plan_graph.py` resolves each dependency against an open task or an accepted record, treats a
clause carrying a branch word (`if`, `when`, `unless`, `only`, `optional`, `conditional`,
`otherwise`, `depending`) as conditional so it orders nothing, and reports self-dependencies and
cycles over the remaining required edges. It also resolves every `Review checkpoint` to a declared
checkpoint task or accepted checkpoint record, and matches `Audit inputs` against the notes a
record declares in both directions, so an unresolved note without an owning task is reported.
`plan_records.py` reads `docs/impl/records/` and requires each record to declare its own id, a
state and an index entry; filenames use `NNNN-<group>-<task-id>.md` (see
[record naming](../../guide/planning-workflow.md#record-file-naming)). An accepted record
additionally needs its fenced task snapshot, at least one acceptance-evidence row and an
audit-handoff result, and an accepted checkpoint record must
state both a refactor verdict -- `no refactor needed` is valid -- and a proceed-or-blocked decision.

Under-detected conditional wording only makes a dependency required, never optional, so the gate
fails safe. Plan-summary tests use isolated fixtures and do not pin the live repository's task
counts. The checker validates resolvable structure and declared evidence, not whether the evidence
behind a gate is technically sufficient; that stays with task-local review and checkpoints.

`src/arxiv_int/quality/doc_links.py` checks repository documentation before a Git commit is
required. It validates relative file targets and generated heading anchors while ignoring fenced
examples and external URLs.

The failure cases and the repository-wide assertions live under `tests/quality/`. The operating
workflow and full task template live in
[Planning workflow](../../guide/planning-workflow.md).

The [checkpoint and handoff revision](../records/0034-foundation-strengthen-checkpoints-and-human-proof-handoffs.md)
adds earlier bounded reviews before pipeline consumers, archive quality proofs, report integration
and scale pilots. Remaining tasks carry explicit approval dependencies and `Human review handoff`
fields identifying draft/final packet producers. AGENTS and the workflow require the completing
agent to report the human task, ready/pending state, packet/inspection path, decision and blocked
consumer. `make plan-status` resolves dependency readiness; it does not itself judge packet quality
or print these completion handoffs. Human judgment is not replaced by the structural checker.

The specification now defines Git-only deterministic identity obfuscation and pinned dynamic
ontology/geotemporal/domain semantics. The Git-bound exporter is implemented in
[record 0035](../records/0035-eval-found-implement-committed-proof-identity-obfuscation.md);
ontology/geotemporal contracts remain planned. Accepted records 0029-0033 and their runtime
behavior are preserved.

Documentation category directories use singular names: `design/`, `guide/`, and `impl/`. Page names
remain specific to their content, and each category `README.md` file provides its local index.

## Codebase review and durable task handoffs

[Codebase review and development handoffs](governance/codebase-review.md) records the subsequent
implementation audit, focused repair tasks, milestone checkpoints, and full task-record workflow.
The [record index](../records/README.md) retains task contracts and audit evidence outside the
forward plan. `make lint-spec-plan` now enforces the record, dependency, note and checkpoint rules
described above; see the
[record and checkpoint integrity record](../records/0004-foundation-enforce-task-record-and-checkpoint-integrity.md).
The review does not claim that identified code defects have been repaired.

## Specification and architecture audit

The specification and forward plan have been audited against the directory-to-knowledge pipeline,
single-CUDA-host deployment, financial/person/company relationships, product BOMs, supply chains,
analyst reports, anomaly triage, and the separate archive organization utility. This is a design and
planning result, not evidence that these product capabilities are available. Production modules,
dependencies, runtime configuration, and source archives are unchanged.

The audit compared `src/arxiv_int/cli.py`, `pipeline/steps.py`, domain interfaces, current-state
pages, Make workflows, and plan parsers with the requested behavior. The checkout provides
foundation/runtime primitives; no archive-to-report runner is available yet. The
[specification](../../design/spec.md) now states that boundary explicitly. The new
[execution architecture](../../design/architecture.md) defines the target DAG, module ownership,
artifact publication, source lookup, and first complete vertical slice.

| Finding | Design and plan result |
| --- | --- |
| End-to-end completion was implicit and proofs could be assembled from unrelated stage runs | Default investigation profile, required output manifest, explicit run/artifact states, coherent generation pointer, and actual single-command acceptance task |
| Companies/products/people were only implied by generic objects and equipment/supplier lists | Three required catalogs, document content overviews, stable unresolved anchors, role/type distinctions, and evidence drill-down |
| Financial extraction and BOM generation shared overly broad tasks | Separate financial/bookkeeping and product extraction tasks, party/allocation projections, and revision/unit-aware BOM and supply-chain projections |
| Anomaly detection had no specification section, registry entry, or tasks | Registered `anomaly-analysis` with constraint/statistical baselines, cohort guards, neutral evidence-based findings, review-budget evaluation, and valid negative outcomes |
| Stage interfaces came after stages needing them; semantic inputs were defined too late | Fixture-first control before corpus work, ontology/domain definitions under contracts, identity anchors before facts, separate fact validation, and dependency-aware delivery milestones |
| Source lookup existed only with the organizer | Shared read-only citation/source resolver scheduled under pipeline control, with portable path-event import |
| Archive placement was mixed into pipeline proofs and operational acceptance | Separate `archive-organization` capability, artifact-only operation, independent copy/move plans, and human-lane real placement |
| Hardlink copies and rollback could undermine source/edit preservation | Independent copied contents, safe duplicate-name policy, per-action checks, durable journals, and refusal to remove subsequently edited targets |
| All results were described as regenerable; proof paths disagreed | Retained/backed-up decision and path ledgers; one `$RESULTS_DIR/proofs/` convention; partial scans cannot retract missing evidence |
| Optional extensions/model choices could obstruct the baseline | Core image can run without AGE; vectors/viewers/generative answers are conditional; selected model fit needs actual one-device context/batch evidence |

Recorded upstream pins remain reference context, not fresh compatibility approval. The audit
rechecked the [ParadeDB extension list](https://www.paradedb.com/docs/deploy/third-party-extensions),
the [recorded AGE revision](https://github.com/apache/age/tree/0e30566226f017d53b7f52025803b38af3ad2b3f),
and the [UDC Summary](https://udcsummary.info/php/index.php?lang=en). These support retaining a
project-owned extension compatibility gate and a pinned authorized hierarchy. The ParadeDB vector
overview and recorded source revision were unavailable to the browser during this audit; vector
promotion still requires independent version and behavior verification. No image/model fit or
multi-terabyte performance claim was validated by this documentation change.

### Plan transition and verification

Open tasks changed from **63 to 77**: agent tasks **55 to 66**, human-assisted tasks **8 to 11**.
The increase makes previously implicit work and acceptance explicit; no implementation task was
completed or removed as shipped. Registry entries changed from 18 to 20; `anomaly-analysis` and
`archive-organization` are newly planned. The two shipped capabilities remain unchanged.

Ontology and domain contract definitions moved into `contract-governance`. Pipeline control now
precedes corpus implementation; lexical retrieval precedes classification; identity anchoring
precedes knowledge extraction. Semantic retrieval moved after required pipeline/recovery work,
and archive organization is last and independent. Physical placement execution moved from the agent
lane to the human-assisted lane. Domain projection scope was split into two focused tasks; the
deferred audit task was replaced by concrete ongoing evidence-freshness validation.

| Capability with changed task count | Before | After |
| --- | --- | --- |
| `contract-governance` | 3 | 5 |
| `pipeline-control` | 7 | 9 |
| `archive-classification` | 6 | 4 |
| `identity-ontology-graph` | 5 | 4 |
| `knowledge-extraction` | 4 | 6 |
| `anomaly-analysis` | 0 | 4 |
| `discovery-visualization` | 5 | 7 |
| `evaluation-evidence` | 4 | 5 |
| `archive-organization` | 0 | 4 |

A separate review of all multiline dependency fields finds 77 tasks and 196 explicit task-reference
edges, including conditional branches, with no cycles or dangling task ids. That was a snapshot
audit; the same classes of defect are now checked on every run by `make lint-spec-plan`.
Baseline/final counts, document snapshots, the dependency graph, and verification logs are under
`.data/spec-plan-audit/20260905/`, using an explicit workspace-local `DATA_DIR=.data` override.
The configured tooling volume was read-only; the operator's environment file was not changed.

`make lint-md`, documentation links, spec-plan integrity, plan status, typing, shell lint, and
`git diff --check` pass. `make -k ci DATA_DIR=.data` runs the remaining checks after failures and
reports **168 tests passed**. At audit time full CI was failing on pre-existing source
formatting/import ordering in `src/arxiv_int/runtime/__init__.py` and Radon complexity D (23) in
`tests/compose/test_profiles.py::test_rendered_topology_has_pins_health_stop_and_mount_isolation`,
and the complexity target stopped at Radon, so its subsequent cognitive-complexity check was
not established by that run. The
[quality baseline repair](../records/0003-foundation-restore-quality-gate-baseline.md) has since
fixed both; `make ci` and `make quality` now pass and both complexity subchecks run. These baseline
findings do not become new product capabilities or deferred audit tasks. Runtime/CUDA and
provided-archive proofs remain forward tasks. No services, model processes, ports, or external
resources were started by this audit.
