# arxiv-int Implementation Plan

Forward-only: this file contains only work that remains. Product behavior, boundaries, evaluation,
and delivery strategy belong in [the specification](../design/spec.md). Task structure, statuses,
ordering, and lifecycle rules belong in the
[planning workflow](../guide/planning-workflow.md). Available behavior and durable results belong in
[current-state documentation](current.md).

## Agent Implementation Tasks

All schema and dataset work follows the specification's
[tool ownership and quality policy](../design/spec.md#data-transformations-and-quality):
contract-derived SQLAlchemy metadata and Alembic revisions, dbt models for relational
transformations, Polars/PyArrow for local batches, and Pandera/dbt validation before publication.
Each producer owns its domain models/checks and uses the shared implementations below. Transactional
queries, COPY, extension DDL, and Cypher retain the narrow exceptions defined in the specification.
Proof tasks retain tool/rule/model fingerprints and required quality outcomes; a skipped validator
cannot establish a pass. These requirements also apply to later additive contract/migration work.
Git-bound proof copies follow [identity obfuscation](../design/spec.md#identity-obfuscation-for-committed-proof-artifacts);
local proof data and human-review packets keep original identities. Each proof task declares its
export file list or records that no Git-bound source artifact is produced.
`Human review handoff` marks an agent producer of human-evaluation evidence; it is not approval or
a prerequisite on the producer. Follow the [handoff workflow](../guide/planning-workflow.md#human-review-handoffs)
and name ready/pending human decisions and the dependent work that must wait at task completion.

### Evaluation foundation -- `evaluation-foundation`

#### create-evaluation-fixtures-and-metrics

Build immutable extraction, classification, Russian retrieval, semantic, entity, fact, ontology,
graph, domain-artifact, company/product/person catalog, anomaly and reporting fixtures plus
paired evaluation utilities.

- Serves: `evaluation-foundation` -- [Evaluation and acceptance](../design/spec.md#evaluation-and-acceptance)
- Agent status: CLEAR
- Dependencies: [Contract data-quality checks](records/0019-contract-gov-implement-contract-data-quality-checks.md);
[Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
the evaluation and retrieval primitives
documented in [Project foundation](current/project-foundation.md#evaluation-and-retrieval-primitives).
[Evaluation bundle validation](records/0033-eval-found-refactor-evaluation-bundle-validation.md);
[Committed proof identities](records/0035-eval-found-implement-committed-proof-identity-obfuscation.md).
- User-visible outcome: Every store/model/pipeline recommendation names the exact frozen items,
metrics, thresholds, and run artifacts that support it, and every usable stage can publish the same
proof-bundle shape.
- Scope boundary: Provide deterministic fixtures and measurement; human gold review remains in the
human lane.
- Data and artifact paths: `tests/fixtures/`, `eval.*`, `src/arxiv_int/evaluation/`,
`configs/evaluation/`, `configs/proofs/`, `Makefile`, `$RUNS_DIR/<run-id>/evaluation/`, and
`$RESULTS_DIR/proofs/`.
- Execution path: Extend the existing metrics for recall@k, MRR, evidence intactness, p95, paired
bootstrap, extraction/span, hierarchical classification, linkage, financial/BOM arithmetic,
catalog parity, anomaly cohorts/false positives/review-budget
precision, domain artifact, graph parity,
resource cost, and adopt/retain/inconclusive verdicts; register the
`evaluate` stage body that writes the immutable evaluation bundle; add a typed proof manifest,
stage-to-validator registry, redaction, fingerprint freshness, proof summary helpers, and a shared
`make proof CAPABILITY=...` dispatcher.
Reuse shared data-quality result identities and fixtures for missing/global checks; keep
held-out accuracy metrics separate from Pandera/dbt structural validation.
Use the shared Git-bound exporter for committed source-derived fixtures; keep local gold originals
and human-review packets unchanged. Include dynamic ontology add/deprecate/draft cases, source-valid
versus recorded time, uncertain places/CRS, role intervals and revision/effectivity boundaries. Build
same-name nonmatches and domain non-implication cases; obfuscate labels and expected answers together.
- Acceptance gates: Split leakage and provenance checks pass; bootstrap seeds and item ledgers
replay; missing evidence refuses a verdict; metrics have positive/negative fixtures; proof bundles
reject stale fingerprints, missing artifact checksums, unvalidated usable stages, and private paths
or unobfuscated corpus content in repository summaries; proof target discovery and unknown capability
tests pass.
Committed copies pass the exporter gate with policy/export fingerprints; raw local quality and
transformed fixture metrics stay distinct. Temporal, location and domain negatives cannot become
valid merely through identity replacement.
- Documentation target: `docs/impl/current/evaluation-foundation.md`
- Review checkpoint: `review-inference-and-evaluation-boundaries`.

#### review-inference-and-evaluation-boundaries

Review inference, resource ownership and immutable evaluation inputs before pipeline integration.

- Serves: `evaluation-foundation` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: [Prior foundation checkpoint](records/0027-store-review-foundation-and-store-boundaries.md);
[Archive roots](records/0029-runtime-retire-separate-proof-archive-root.md);
[Pandera compatibility](records/0030-contract-gov-upgrade-pandera-polars-concat-compat.md);
[Inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Resource scheduler](records/0032-inference-implement-model-resource-scheduler.md);
[Bundle validation](records/0033-eval-found-refactor-evaluation-bundle-validation.md);
`create-evaluation-fixtures-and-metrics`;
[Committed proof identities](records/0035-eval-found-implement-committed-proof-identity-obfuscation.md).
- User-visible outcome:
Pipeline workers receive compatible typed inference, cancellation, resource and evidence contracts.
- Scope boundary:
Review accepted 0029-0033 with the new evaluation/export producers. Use deterministic local fixtures
and inspect retained CUDA evidence; a small-model smoke cannot establish another model's fit.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace local-only requests, leases across processes, cancel/exception release, declared CPU fallback,
footprint/model identity, no implicit pull/service control, and optional-import boundaries. Trace
metric denominators, split isolation, bundle immutability, missing evidence and Git-export identity
joins/format/anchors; ensure ontology and geotemporal fixture meanings survive export.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
Show contention/cancellation and model-mismatch refusals; empty/failed metrics cannot pass;
corrupt/stale bundles and leaking or inconsistent exports cannot publish. Existing accepted producer
checks remain evidence; missing cross-module cases receive targeted tests before DAG integration.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/evaluation-foundation.md`
- Review checkpoint: none; this is the bounded checkpoint.

### Pipeline control -- `pipeline-control`

#### refactor-stage-and-artifact-interface-contracts

Align foundational stage, extraction and artifact references before concrete adapters depend on them.

- Serves: `pipeline-control` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-codebase-13](records/0001-govern-codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
[Contract identity and reference validation](records/0009-contract-gov-refactor-contract-identity-and-reference-validation.md).
`review-inference-and-evaluation-boundaries`.
- User-visible outcome: Multi-silo inputs, structured source anchors, generation identities and honest
stage states
fit the shared interfaces rather than being hidden in string metadata or invented per adapter.
- Scope boundary: Refine existing Protocol/value types and fake conformance tests; do not implement domain
stages, a new orchestrator framework, or backend-specific logic in shared interfaces.
- Data and artifact paths: `src/arxiv_int/interfaces/{pipeline,stores,extraction}.py`, contract mappings,
`src/arxiv_int/features/catalog.py`, and `tests/interfaces/`.
- Execution path: Define typed source occurrences/anchors and generation-bearing artifact
references from
contracts; distinguish partial/empty/not-selected outcomes and conditional feature requirements;
keep fixture conformance dependency-light and adapters responsible for actual processing.
Include typed validation-result and transformation-run references in artifact interfaces; keep
Pandera/dbt implementation imports in optional adapters.
- Acceptance gates: Conformance fixtures cover duplicate paths across silos, cell/member anchors, distinct
generations of one partition, conditional GPU/UI features and failure/partial states; public
compatibility decisions are recorded; no optional heavy imports enter core; make ci passes.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.

#### implement-run-ledger-and-atomic-artifacts

Create run, stage, shard, lease, checkpoint, error, artifact-manifest, and transitive-lineage state
with deterministic reuse keys.

- Serves: `pipeline-control` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: [Canonical relational schema](records/0021-store-create-canonical-relational-schema.md);
fixture artifact contracts from
[Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md).
`refactor-stage-and-artifact-interface-contracts`.
[Foundation/store checkpoint](records/0027-store-review-foundation-and-store-boundaries.md).
- User-visible outcome: Every long operation has inspectable state; an interrupted shard resumes,
and an unchanged shard reuses validated output without loading its heavy implementation.
- Scope boundary: Implement generic control mechanics; stage-specific processing stays in its owning
capability.
- Data and artifact paths: `ctl.*` tables, `$RUNS_DIR/<run-id>/manifests/`,
`src/arxiv_int/pipeline/control/`, and `tests/pipeline/control/`.
- Execution path: Define stage-owned code/dependency/input fingerprints, transitive artifact edges,
cache validation, concurrent reuse leases, state transitions, atomic sibling writes, bounded retry
taxonomy, stale-lease recovery, and downstream invalidation planning.
Use Alembic-managed control tables and bound SQLAlchemy transactions; bind validation and dbt
model/input/rule fingerprints into reuse keys. Activation requires all applicable quality checks,
including global checks, and successful model results for the exact generation; warnings and
quarantine coverage remain visible.
- Acceptance gates: Property/state-machine tests reject illegal transitions; crash injection proves
no partial output is accepted; unchanged rerun validates manifests and does not invoke the heavy
worker; a changed owned fingerprint marks exactly the reachable closure stale; forced retry creates
a new attempt without overwriting evidence.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.

#### implement-stage-dag-cli-and-make-targets

Complete the dependency-aware stage registry, independent stage command, end-to-end and incremental
runners, resume, status, invalidate, rebuild, and stale-prune planning interfaces.

- Serves: `pipeline-control` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: `implement-run-ledger-and-atomic-artifacts`.
- User-visible outcome: Operators can run or update one stage or a `--from`/`--to` dependency
closure, inspect invalidation, start a fresh generation, and resume by run id through CLI or Make.
- Scope boundary: Orchestrate in-process/local workers first with fixture DAGs; full preflight,
forecast and publication assembly belongs to `implement-investigation-profile-and-output-manifest`.
Do not introduce Airflow, Prefect, Celery, Redis, or Kubernetes.
- Data and artifact paths: `src/arxiv_int/cli.py`, `src/arxiv_int/pipeline/registry.py`, `Makefile`,
and `tests/pipeline/orchestration/`.
- Execution path: Build the typed registry with fixture runners first; declare required/conditional
input contracts,
resource estimates, validators, and dependencies;
resolve parameters; validate required
upstream manifests; add run/update/stage/status/resume/invalidate/rebuild and prune-plan commands;
keep Make wrappers thin and destructive application separately confirmed. Provide `make run-create`
and `make stage STAGE=... RUN_ID=...`, backed by the same run-context/stage handlers as `make pipeline`.
Resolve defaults from `.env` without activation or manual exports; allocate a unique run id instead
of inheriting Make's developer `RUN_ID=local` fallback. Freeze profile/configuration for subsequent
atomic calls and refuse drift or stale upstream inputs. Reuse setup's declarative requirement seam;
do not maintain parallel feature/service lists. Document command order in the operator workflow.
Invoke the shared dbt runner for declared relational model selections and the common Pandera
validator at producer boundaries; propagate failed/not-run quality outcomes and generation leases
without introducing a second scheduler.
- Acceptance gates: DAG, range, skip, invalid dependency, update, resume, targeted invalidate,
fresh-generation rebuild, prune dry-run, force, and signal-handling tests pass; CLI help lists
defaults and precedence; bare Make and CLI defaults agree. Aggregate and independent fixture stages
sharing a run context produce equivalent logical manifests/lineage and refuse the same invalid
inputs; failure halts downstream work in both paths. Unregistered required
stages and stale upstream snapshots fail explicitly. The directory-to-report gate exercises concrete
stages after they become available.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.

#### add-progress-logging-and-resource-telemetry

Provide serialized human logs, structured logs, periodic database progress, and bounded resource
metrics for every stage.

- Serves: `pipeline-control` --
[Logging, progress, and observability](../design/spec.md#logging-progress-and-observability)
- Agent status: CLEAR
- Audit inputs: [AUD-codebase-15](records/0001-govern-codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: `implement-stage-dag-cli-and-make-targets`.
- User-visible outcome: Long runs continuously report processed/remaining items, bytes, throughput,
ETA, errors, and resource pressure without garbled concurrent output.
- Scope boundary: Record operational metadata; do not place document content, prompts, secrets, or
unbounded ids in logs/metric labels.
- Data and artifact paths: `src/arxiv_int/observability/`, `$RUNS_DIR/<run-id>/logs/`,
`ctl.stage_run`, Grafana provisioning, and logging tests.
- Execution path: Extend the existing logging and timing interfaces with time/count-throttled
progress, explicit queue bounds/overload behavior, heartbeats, psutil/NVML/disk/Postgres metrics,
redaction filters, JSONL schema, and final
manifests.
- Acceptance gates: Concurrent-log tests produce intact lines; redaction fixtures remove secrets and
corpus text; stalled worker and ETA states are distinguishable; metric labels have bounded
cardinality.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.

#### implement-evidence-based-pipeline-forecast

Implement a read-only command that predicts requested work, duration, output/peak storage, and
free-space safety before a pipeline run.

- Serves: `pipeline-control` --
[Pre-run forecast and resource refusal](../design/spec.md#pre-run-forecast-and-resource-refusal)
- Agent status: CLEAR
- Dependencies: `implement-run-ledger-and-atomic-artifacts`;
`add-progress-logging-and-resource-telemetry`; runtime storage evidence documented in
[Portable runtime](current/portable-runtime.md).
- User-visible outcome: Before starting, an operator sees stage-by-stage cache hits, changed work,
time and data-size ranges, peak scratch/rebuild needs, accessible disk free space, confidence, and a
clear ready/degraded/blocked decision.
- Scope boundary: Perform inventory, sampling, manifest, telemetry, and filesystem checks only; do
not load heavy models, materialize production artifacts, invent precise estimates, or bypass hard
space reserves.
- Data and artifact paths: `src/arxiv_int/pipeline/forecast/`, `configs/capacity/`, forecast JSON
Schema/contracts, prior run manifests/telemetry, and `$RUNS_DIR/<forecast-id>/forecast/`.
- Execution path: Implement estimators against fixture manifests before concrete stages; use
bounded directory
metadata sampling when no inventory exists, then consume inventory/delta and cache manifests when
available. Resolve comparable runs and bounded format samples;
estimate lower/upper output, time, WAL, temp, staging, rebuild, rollback, backup, and
selected pipeline output costs; the organizer estimates placement independently; deduplicate
filesystem devices across the archive, results, and
database roots; read accessible free bytes; emit evidence/coefficient provenance and a fingerprinted
console/JSON decision; add stage-boundary free-space rechecks. Expose `make forecast RUN_ID=...`
and the equivalent CLI option to use the created run's frozen inputs and retain its forecast under
that run. The aggregate command calls the same estimator and refusal handler; standalone forecasts
remain available without creating a production generation.
- Acceptance gates: Zero-history fixtures yield conservative low-confidence ranges; estimates replay
from captured evidence; shared devices are counted once; inaccessible paths and upper-bound peak plus
reserve shortfalls exit non-zero before heavy work; stale forecasts are rejected; simulated free-space
loss checkpoints before allocation without accepting partial output. Atomic and aggregate forecast
decisions agree for the same captured inputs; changed configuration cannot reuse a stale forecast.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.

#### implement-investigation-profile-and-output-manifest

Publish an explicit requested profile and coherent knowledge-base generation with honest completion states.

- Serves: `pipeline-control` -- [End-to-end run and output contract](../design/spec.md#end-to-end-run-and-output-contract)
- Agent status: CLEAR
- Dependencies: `implement-stage-dag-cli-and-make-targets`; `implement-evidence-based-pipeline-forecast`.
- User-visible outcome: The default investigation command names every required output and report
entry point; a
lexical-only request is visibly a smaller profile.
- Scope boundary: Implement profile selection, contract validation, publication, and exit semantics
using fixture
runners; do not claim concrete extraction or full-pipeline acceptance from mocks.
- Data and artifact paths: `configs/pipeline/`, `src/arxiv_int/pipeline/`, output-manifest contracts,
`$RUNS_DIR/<run-id>/knowledge-base.json`, and orchestration fixtures.
- Execution path: Declare required versus conditional stages and output families; seal
artifact/snapshot ids,
counts/checksums, coverage and report path; validate then switch one active generation pointer;
write diagnostic reports for partial/failed runs and reconcile orphan staging after crashes.
Connect concrete profile declarations to setup's shared requirement seam. Assemble bare
`make pipeline` / `arxiv-int pipeline run` from the same create, preflight, forecast, stage and
finalize handlers as the documented atomic chain. Expose `make run-finalize RUN_ID=...` and
`arxiv-int run finalize RUN_ID`; report rendering alone cannot activate a generation. Return the run
id, logical status, manifest/report paths and exact status/resume commands; enforce missing-provider,
quality, resource and authorization gates before dependent work. Update the operator workflow with
the actual profile order and availability while concrete stages remain pending.
- Acceptance gates: Fixtures cover complete, valid-empty, partial, failed, blocked, interrupted,
and not-selected
states, specified exit codes, stale dependency refusal, and crash recovery across file/database
publication; a partial run cannot replace the last complete generation. No-argument Make and CLI
runs read `.env` in fresh shells; the explicit atomic chain yields equivalent logical artifacts,
lineage, quality and final states. Missing setup/required stages refuse execution, optional disabled
branches stay explicit, and interruption preserves one resumable generation.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.

#### review-pipeline-publication-and-reuse-boundaries

Review fixture orchestration before concrete corpus workers depend on its publication protocol.

- Serves: `pipeline-control` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `refactor-stage-and-artifact-interface-contracts`; `implement-run-ledger-and-atomic-artifacts`;
`implement-stage-dag-cli-and-make-targets`; `add-progress-logging-and-resource-telemetry`;
`implement-evidence-based-pipeline-forecast`; `implement-investigation-profile-and-output-manifest`;
`review-inference-and-evaluation-boundaries`.
- User-visible outcome:
Concrete adapters inherit a checked run/lease/quality/publication boundary.
- Scope boundary:
Fixture DAG and disposable store integration only; source delta/prune and archive proofs stay in
the later corpus/control checkpoint, avoiding a dependency on workers this checkpoint gates.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace aggregate versus atomic execution, frozen parameters, exact-generation quality, file/database
publication order, concurrent reuse, forced attempts, expired leases, cancellation and reserve loss.
Inject failure around the active-pointer switch; reconcile logs, ledger and visible artifacts.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
Equivalent commands produce equivalent logical manifests; missing/global checks, stale forecasts,
partial or failed stages never activate. Cache hits skip heavy work; interrupted publication
preserves one resumable attempt and the prior complete generation.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: none; this is the bounded checkpoint.

#### add-stage-artifact-inspection

Report what a normal pipeline stage produced without recomputing it.

- Serves: `pipeline-control` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: RUN NEEDED
- Dependencies: `implement-stage-dag-cli-and-make-targets`.
- User-visible outcome: After any stage or complete pipeline run, the operator can inspect row and
byte counts, partitions, contract conformance, bounded source anchors, quarantines, and failures by
run id.
- Scope boundary: Read and summarize normal run artifacts; do not introduce development-only paths
or commands, rerun stages, mutate artifacts, or treat an inspection as proof acceptance.
- Data and artifact paths: `src/arxiv_int/inspect/`, `$RESULTS_DIR/normalized/`,
`$RUNS_DIR/<run-id>/`, `src/arxiv_int/cli.py`, `Makefile`, and inspection fixtures.
- Execution path: Add `arxiv-int inspect RUN_ID` and the matching run-artifact lookup using the
pipeline registry and contracts; render console and JSON summaries with bounded samples and masked
secrets; inspect the real run produced after each available stage implementation.
Read retained Pandera/dbt quality results and sanitized model lineage; show rule scope, failed
counts, quarantine references and not-run status without executing transformations.
- Acceptance gates: Normal empty, partial, quarantined, and schema-drifted run artifacts produce
stable summaries; inspection leaves checksums unchanged; summaries contain no secrets, unbounded
corpus text, development alias, or machine-specific path.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.

#### implement-incremental-reconciliation-and-stale-pruning

Reconcile archive and implementation deltas through artifact lineage, retract stale active data,
and provide safe partial update, full rebuild, and physical-prune paths.

- Serves: `pipeline-control` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: `implement-run-ledger-and-atomic-artifacts`;
`implement-stage-dag-cli-and-make-targets`; [0025](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
`implement-streaming-inventory`.
- User-visible outcome: Added, changed, renamed, or removed files and later analysis-code changes
update only affected descendants, while operators can deliberately rebuild everything or reclaim
obsolete derived storage.
- Scope boundary: Reconcile derived/canonical active views and prune only unreferenced stale data;
never delete archive sources, move ledgers, immutable review history, active generations, or the sole
recovery copy.
- Data and artifact paths: `ctl.artifact_lineage`, source delta/tombstone and prune-event contracts,
`src/arxiv_int/pipeline/reconcile/`, `src/arxiv_int/pipeline/prune/`,
additive `src/arxiv_int/migrations/versions/`, and
`$RUNS_DIR/<run-id>/{delta,invalidation,rebuild,prune}/`.
- Execution path: Diff complete comparable source manifests into add/content-change/path-rename/remove;
unavailable silos, partial scans, or unstable files cannot create removal tombstones; compute the
minimal downstream closure; retract stale rows/edges from active views after replacements validate;
retain shared evidence; create isolated rebuild generations and atomic activation; make prune
two-phase with dry-run ids, reference/pin/backup checks, and compact retained lineage.
Use Alembic Python revisions for new control fields and typed SQLAlchemy transactions for
tombstones/activation; place set-based derived-view recomputation in dbt models. Reconcile dbt
source/ref lineage with artifact edges and test deleted inputs, late corrections and model changes
against a clean build; successful quality checks precede every pointer switch.
- Acceptance gates: Deterministic fixtures prove no-op updates invoke no heavy workers; additions
touch only new shards; path-only renames avoid content analysis; changes/removals retract exactly
dependent active outputs; stage fingerprint changes invalidate only owned descendants; rebuild
matches a clean baseline; partial or unreadable scans retract nothing; merge/split/review and
source-removal updates preserve
shared evidence; prune refuses active, pinned, reviewed, rollback, decision-ledger, or sole-backup data.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.

#### implement-evidence-and-source-location-lookup

Resolve every content, fact and report citation to physical sources and exact member/page/cell anchors.

- Serves: `pipeline-control` -- [Source and evidence identity](../design/spec.md#source-and-evidence-identity)
- Agent status: CLEAR
- Dependencies: `implement-streaming-inventory`; `implement-run-ledger-and-atomic-artifacts`;
`implement-normalization-dedupe-and-chunking`.
- User-visible outcome: Search and report users can find original and current source locations,
including duplicate files, container members and renamed sources before any organizer is installed.
- Scope boundary: Read-only resolution and explicit path-event import; no placement executor,
reclassification, arbitrary filesystem opening, or requirement for live model/graph services.
- Data and artifact paths: `src/arxiv_int/query/evidence/`, source/path-event contracts,
`corpus.document_path_event`, portable source manifests, CLI and network-free resolver fixtures.
- Execution path: Expose `archive locate DOCUMENT_ID` and a typed citation resolver using canonical
rows or sealed manifests; map content to all source occurrences and original/normalized anchors;
validate root containment and current hashes; import portable organizer ledgers idempotently.
- Acceptance gates: Fixtures cover duplicate silos, sheet/cell and nested-member anchors, path-only
renames, missing/changed files, ambiguous locations, escaping links and repeated ledger import;
resolution never rewrites original provenance, changes bytes or requires placement services.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.

#### prove-pipeline-control-on-provided-archive

Exercise idempotency, incremental reconciliation, invalidation, forecasting, rebuild, and prune
planning with the supplied archive and publish the pipeline-control proof bundle.

- Serves: `pipeline-control` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-evidence-based-pipeline-forecast`;
`prove-corpus-foundation-on-provided-archive`; `create-evaluation-fixtures-and-metrics`;
`implement-evidence-and-source-location-lookup`.
- User-visible outcome: The supplied archive demonstrates that unchanged inputs skip heavy work,
deltas update only affected artifacts, stale data retracts safely, insufficient space blocks early,
and a clean generation can be rebuilt.
- Scope boundary: Do not modify `ARCHIVE_DIR`; perform add/change/rename/remove and prune-apply
drills only on a bounded disposable proof copy; do not prune the sole proof or recovery generation.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, disposable
`$RESULTS_DIR/proof-work/pipeline-control/<proof-id>/`, and
`$RESULTS_DIR/proofs/pipeline-control/<proof-id>/`.
- Execution path: Forecast and run the corpus closure; rerun unchanged; create controlled source
deltas and a stage-fingerprint bump; inspect minimal closures and active retractions; simulate low
space; rebuild into a fresh generation; compare checksums; dry-run pruning and apply it only to an
extra disposable stale generation.
- Acceptance gates: Proof records zero heavy invocations on the no-op rerun, exact affected/unaffected
shards for each delta, correct tombstones and active rows, targeted code invalidation, non-zero
resource refusal before allocation, clean-rebuild parity, protected-data prune refusal, and no write
to the supplied archive.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.

#### review-corpus-and-control-integrity

Review the integrated milestone before lexical loading, classification and NLP consumers.

- Serves: `pipeline-control` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `implement-normalization-dedupe-and-chunking`;
`implement-evidence-and-source-location-lookup`; `implement-investigation-profile-and-output-manifest`;
`add-progress-logging-and-resource-telemetry`; `create-evaluation-fixtures-and-metrics`.
`review-pipeline-publication-and-reuse-boundaries`; `implement-incremental-reconciliation-and-stale-pruning`.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
Use deterministic integration evidence and inspect provided-archive proofs when available;
this verdict permits fixture implementation, not real-data or CUDA promotion.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/proof artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace source immutability,
complete-scan semantics, cell/member coordinates, shard/generation
identity, cache invalidation, atomic publication, forecast/reserve refusal and bounded queues;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

### Corpus foundation -- `corpus-foundation`

#### implement-streaming-inventory

Build a content-addressed, restartable archive inventory with format, encoding, hash, and quarantine
metadata.

- Serves: `corpus-foundation` -- [Pipeline](../design/spec.md#pipeline)
- Agent status: RUN NEEDED
- Dependencies: Runtime roots documented in [Portable runtime](current/portable-runtime.md);
[Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
`implement-stage-dag-cli-and-make-targets`;
`implement-evidence-based-pipeline-forecast`.
`review-pipeline-publication-and-reuse-boundaries`.
- User-visible outcome: The operator can inventory one or more multi-terabyte silos without loading
them into RAM and can see per-silo coverage, bytes, duplicates, and unsupported/encrypted inputs.
- Scope boundary: Read files and archive-member metadata only; no text extraction and no
modification of source files.
- Data and artifact paths: Declared source roots from `$ARCHIVE_DIR`, used without modification;
`$RESULTS_DIR/normalized/inventory/`; `$RUNS_DIR/<run-id>/`; `src/arxiv_int/pipeline/inventory/`.
- Execution path: Resolve the declared silo ids and roots; stream directory entries, carry silo id
with root-relative path metadata, detect MIME/encoding, compute strong hashes for content identity
(quick hashes only select candidates), verify file
stability across reads, record completed source-set scope and container/member identities, enforce
archive-bomb limits, shard by stable id, and write atomic Parquet manifests; register
the stage in the existing registry and expose `arxiv-int stage inventory` plus
`make stage STAGE=inventory` in the same change,
then run that command on a bounded authorized archive when available and inspect its artifacts.
Use PyArrow batch writers and contract-derived Pandera checks before sealing partitions;
record completed global occurrence-key checks and reject batches with invalid provenance.
- Acceptance gates: Network-free fixtures cover large/sparse files, links, permission errors,
renamed duplicates, nested archives, encrypted files, interruption, and resume; two silos sharing one
root-relative path stay distinct while identical bytes resolve to one content identity; memory is
bounded independently of file count; fixture stage run and artifact summary are recorded without
private content or machine-specific
paths; provided-archive acceptance is tracked by its separate proof task.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.

#### integrate-tiered-text-extraction

Compose Tika, Docling, and OCR/layout fallbacks behind one evidence-preserving extractor interface.

- Serves: `corpus-foundation` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Dependencies: `implement-streaming-inventory`;
[Deterministic schema generation](records/0011-contract-gov-implement-deterministic-schema-generation.md).
- User-visible outcome: Supported documents become normalized source spans with page/table/offset
evidence; failures are quarantined with actionable reasons.
- Scope boundary: Integrate existing engines and selection policy; do not build a new parser or
promise every proprietary format.
- Data and artifact paths: `$RESULTS_DIR/normalized/documents/`, `$RESULTS_DIR/normalized/spans/`,
`$RESULTS_DIR/quarantine/`, `src/arxiv_int/extraction/`, and representative format fixtures.
- Execution path: Run Tika as breadth baseline; route layout/table PDFs to Docling and scanned PDFs
to OCR; preserve tool versions, page/table/bounding-box and spreadsheet sheet/cell anchors,
container/member paths, raw hashes, and extraction quality; never execute macros or active content;
bound temp files,
child processes, timeouts, and decompression; register `extract` with the normal stage interface and
run it against a bounded authorized archive when available after deterministic checks pass.
Validate emitted document/span batches with shared Pandera schemas and existing source-anchor
checks; preserve explicit quarantine and incomplete-coverage results.
- Acceptance gates: The reviewed extraction fixture reports per-format text, table, and anchor
coverage; corrupt/encrypted/oversized inputs fail safely; repeated content hashes reuse outputs;
source files remain unchanged; the normal `make stage STAGE=extract` run produces inspectable
artifacts on the declared fixture or authorized archive, and its redacted result is recorded in current-state
documentation.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.

#### implement-normalization-dedupe-and-chunking

Normalize extracted text, group exact/near duplicates and editions, and emit source-aligned chunks
without destructive corpus edits.

- Serves: `corpus-foundation` -- [Normalized data lake](../design/spec.md#normalized-data-lake)
- Agent status: RUN NEEDED
- Dependencies: `integrate-tiered-text-extraction`.
- User-visible outcome: Each unique document has searchable, table/structure-aware chunks and
reversible duplicate/edition overlays.
- Scope boundary: Normalize and propose duplicate groups; do not merge entities or delete
source/extracted records.
- Data and artifact paths: `$RESULTS_DIR/normalized/documents/`, `spans/`, `chunks/`, duplicate overlays,
`src/arxiv_int/pipeline/normalize/`, and `src/arxiv_int/pipeline/chunk/`.
- Execution path: Preserve original text; create NFC/casefold/search views; map
original-to-normalized offsets; detect language; run exact, normalized, MinHash/lexical, and
edition grouping; implement bounded structure/table/sentence chunkers with source breadcrumbs;
register the normal stage commands and run them against a bounded authorized archive when available.
Express tabular normalization and grouping with typed Polars expressions and PyArrow batches;
keep text/span algorithms in focused Python functions. Run generated Pandera checks, cross-partition
identity checks and bounded-memory tests before publishing.
- Acceptance gates: Golden offsets and table headers survive chunking; unchanged input yields stable
ids; dedupe precision is measured on labels; no suppression occurs without an overlay; out-of-core
memory and shard-resume tests pass; the declared fixture commands produce inspectable artifacts
whose redacted results are recorded in current-state documentation.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.

#### prove-corpus-foundation-on-provided-archive

Run the completed corpus stages against the operator-provided archive and publish their first
current proof bundle.

- Serves: `corpus-foundation` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-normalization-dedupe-and-chunking`;
`implement-stage-dag-cli-and-make-targets`; `implement-evidence-based-pipeline-forecast`;
`create-evaluation-fixtures-and-metrics`;
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md).
- User-visible outcome: The supplied file silos have inspectable inventory, extraction,
normalization, duplicate, and chunk artifacts backed by one reproducible proof id.
- Scope boundary: Read `ARCHIVE_DIR` without mutation and stop after `chunk`; do not infer
downstream classification, retrieval, or knowledge quality from this proof.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, `$RESULTS_DIR`, and
`$RESULTS_DIR/proofs/corpus-foundation/<proof-id>/`; only redacted summaries enter current docs.
- Execution path: Run a passing forecast; execute `inventory` through `chunk`; validate contracts,
counts, spans, offsets, quarantine reasons, and checksums; rerun the identical closure and capture
cache decisions plus resource/timing evidence.
- Acceptance gates: Every usable corpus stage is `passed` or contract-valid `empty`; every inventory
item is accounted for; artifacts and source anchors validate; the unchanged rerun executes no heavy
extraction/normalization work; failures keep the task open.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.

### Lexical retrieval -- `lexical-retrieval`

#### build-paradedb-lexical-load-and-query-path

Bulk-load selected document/chunk projection rows and implement lexical search, filters, snippets,
facets, and identifier lookup.

- Serves: `lexical-retrieval` --
[Search and vector projections](../design/spec.md#search-and-vector-projections)
- Agent status: RUN NEEDED
- Dependencies: [0025](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
`implement-stage-dag-cli-and-make-targets`.
`review-corpus-and-control-integrity`.
- User-visible outcome: The full normalized corpus or chosen partition is searchable with
evidence-bearing results and stable filter behavior.
- Scope boundary: Establish the lexical path and lifecycle; semantic fusion is separate.
- Data and artifact paths: `search.*` tables/indexes, `src/arxiv_int/retrieval/lexical.py`,
`$RUNS_DIR/<run-id>/search/`, and retrieval fixtures.
- Execution path: Binary-COPY staging rows; create one covering ParadeDB index per partition/table
design; index Russian text plus literal ids and required filter fields; expose typed query and
explain/diagnostic modes.
Reuse dbt-tested projection inputs and Pandera batch validation; use psycopg binary COPY and
bound SQLAlchemy queries. Keep ParadeDB index/search syntax in named engine assets and Alembic
operations, separate from business transformations.
- Acceptance gates: Load counts/checksums reconcile; result citations resolve to source spans;
concurrent index build/rebuild remains observable; query and index failures have actionable
diagnostics.
- Documentation target: `docs/impl/current/lexical-retrieval.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.

#### calibrate-russian-tokenization-and-bm25

Compare Unicode and ICU segmentation, Russian stemming/stopwords, exact identifier fields, aliases,
and query normalization on a held-out Russian query set.

- Serves: `lexical-retrieval` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `build-paradedb-lexical-load-and-query-path`;
`create-evaluation-fixtures-and-metrics` may begin with a minimal retrieval fixture.
- User-visible outcome: The default Russian lexical profile is backed by recall, MRR, evidence
intactness, latency, and index-size evidence rather than an English default.
- Scope boundary: Compare declared tokenizer/query profiles; do not tune on the final split or
silently rewrite source text.
- Data and artifact paths: `configs/retrieval/`, `eval.*`, `$RUNS_DIR/<run-id>/evaluation/lexical/`,
and `docs/impl/current/lexical-retrieval.md`.
- Execution path: Build comparable indexes on identical data; measure inflection, identifiers,
abbreviations, OCR noise, homoglyphs, e/yo variants, keyboard layout, transliteration, and
mixed-language cases; use paired bootstrap verdicts.
- Acceptance gates: One profile receives `adopt`, `retain baseline`, or `inconclusive`; final
metrics and costs cite immutable runs; profile changes name required reindex work.
- Documentation target: `docs/impl/current/lexical-retrieval.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.

#### prove-lexical-retrieval-on-provided-archive

Build and query the lexical projection for the supplied archive and publish its proof bundle.

- Serves: `lexical-retrieval` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `calibrate-russian-tokenization-and-bm25`;
`prove-pipeline-control-on-provided-archive`.
`review-retrieval-and-classification-boundaries`.
- User-visible outcome: Supplied documents are searchable through the selected Russian lexical
profile, with filters, snippets, identifiers, and citations that resolve to source evidence.
- Scope boundary: Prove lexical load/query behavior and declared evaluation queries; do not claim
semantic retrieval or full-archive relevance from this test archive.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, lexical tables/indexes, and
`$RESULTS_DIR/proofs/lexical-retrieval/<proof-id>/`.
- Execution path: Forecast; load/build the selected lexical projection; reconcile counts/checksums;
run archive-appropriate smoke and held-out queries; validate citations and limits; rerun unchanged
and record load/index cache decisions.
- Acceptance gates: Projection and source counts reconcile; required queries return valid evidence
under declared metrics; index/query manifests validate; unchanged rerun does not rebuild or reload
unchanged partitions; failures or missing citations keep the task open.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/lexical-retrieval.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Archive classification -- `archive-classification`

#### establish-versioned-udc-derived-scheme

Establish the authorized UDC-derived hierarchy, project extension namespace, special outcomes, and
evaluation labels used to classify archive files.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: [Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
`create-evaluation-fixtures-and-metrics`.
- Human review handoff:
[approve-classification-policy](#approve-classification-policy)
vocabulary, thresholds and exception examples.
Packet: `$RUNS_DIR/<run-id>/review/classification/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`
and `approve-archive-organization-plan`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept/revise the hierarchy, thresholds and exceptional outcomes, or retain unclassified.
- User-visible outcome: Operators can inspect the exact hierarchy, captions, parent links, licence,
local extensions, and version behind every file assignment.
- Scope boundary: Use the distributable UDC Summary or an operator-provided licensed MRF snapshot;
do not redistribute restricted schedules or label project extensions and exceptional outcomes as
official UDC notation.
- Data and artifact paths: `contracts/datasets/classification*.odcs.yaml`,
`configs/classification/`, `src/arxiv_int/classification/vocabulary/`, classification gold fixtures,
and `$RUNS_DIR/<run-id>/classification/`.
- Execution path: Import and checksum the selected vocabulary; parse simple hierarchy, auxiliaries,
and compound notation; define stable local extension ids plus `unclassified` and `unreadable`;
freeze multilingual captions, parent closure, path-safe tokens, and evaluation splits.
- Acceptance gates: Codes and parents round-trip; cycles, orphaned classes, namespace collisions,
missing attribution, and stale snapshots fail validation; the Summary-only baseline works without a
licence secret; unavailable deep schedules yield a documented Summary baseline rather than guessed
classes.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.

#### implement-hierarchical-file-classification

Add a restartable stage that maps every inventoried physical file to primary and alternate
UDC-derived classes or one explicit exceptional outcome.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `establish-versioned-udc-derived-scheme`;
`implement-normalization-dedupe-and-chunking`; `implement-stage-dag-cli-and-make-targets`.
Reviewed real-corpus quality is accepted by the separate proof/human tasks.
`review-corpus-and-control-integrity`.
- Human review handoff:
[approve-classification-policy](#approve-classification-policy)
vocabulary, thresholds and exception examples.
Packet: `$RUNS_DIR/<run-id>/review/classification/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`
and `approve-archive-organization-plan`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept/revise the hierarchy, thresholds and exceptional outcomes, or retain unclassified.
- User-visible outcome: Each source file has a searchable, evidence-backed hierarchical assignment,
while random text and extraction failures remain visibly `unclassified` or `unreadable`.
- Scope boundary: Produce mappings and review candidates only; do not move source files, classify
virtual archive members as independently movable files, or force low-confidence assignments.
- Data and artifact paths: `$RESULTS_DIR/normalized/classifications/`, `corpus.file_classification`,
additive `src/arxiv_int/migrations/versions/`, `src/arxiv_int/classification/`, classifier profiles,
and `$RUNS_DIR/<run-id>/evaluation/classification/`.
- Execution path: Combine metadata and normalized-text rules with a measured lightweight classifier;
allow bounded local-model assistance only when it improves held-out results; retain multi-label
scores, one primary ancestor path, decisive evidence, failure taxonomy, and complete fingerprints;
generate and apply reviewed classification Alembic Python revisions from the extended ODCS metadata;
use Polars for batch feature preparation and shared Pandera checks for classification outputs.
- Acceptance gates: Every inventory file appears exactly once; unreadability follows extraction
evidence; exact and ancestor-aware precision/recall, hierarchical distance, calibration, selective
coverage, exceptional-outcome confusion, reproducibility, throughput, and memory meet predeclared
gates. A high `unclassified` or `unreadable` rate is a valid reported result.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.

#### review-retrieval-and-classification-boundaries

Review searchable/classifiable corpus accounting before archive quality and policy review.

- Serves: `archive-classification` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `review-corpus-and-control-integrity`; `calibrate-russian-tokenization-and-bm25`;
`establish-versioned-udc-derived-scheme`; `implement-hierarchical-file-classification`;
`implement-evidence-and-source-location-lookup`.
- User-visible outcome:
Retrieval and classification proofs consume coherent source, vocabulary and query identities.
- Scope boundary:
Inspect fixture/store integration and retained calibration evidence before the provided-archive
proofs. This review neither accepts a classification policy nor authorizes file placement.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace source/chunk/query ids, Russian normalized versus literal identifiers, hierarchy/ancestor
metrics, excluded/unreadable/unclassified denominators, stale mappings, duplicate source occurrence
lookup and empty results. Verify candidate policy packets expose errors and exact fingerprints.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
Indexed, excluded and failed rows reconcile; snippets and class assignments resolve to sources;
unknown classes and low-confidence assignments stay exceptional; changed tokenizer/vocabulary
invalidates affected outputs. No relevance or classification-quality claim follows from counts.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: none; this is the bounded checkpoint.

#### prove-archive-classification-on-provided-archive

Classify the supplied archive and validate its complete hierarchical mapping and source references.

- Serves: `archive-classification` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-hierarchical-file-classification`;
`prove-pipeline-control-on-provided-archive`;
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md).
`implement-evidence-and-source-location-lookup`.
`review-retrieval-and-classification-boundaries`.
- Human review handoff:
[approve-classification-policy](#approve-classification-policy)
final errors, calibration, coverage and policy decision packet.
Packet: `$RUNS_DIR/<run-id>/review/classification/`.
Ready after this proof passes.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`
and `approve-archive-organization-plan`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept/revise the hierarchy, thresholds and exceptional outcomes, or retain unclassified.
- User-visible outcome: Every supplied file has a UDC-derived or explicit exceptional result, with hierarchy,
confidence, evidence/failure reasons, and initial source lookup.
- Scope boundary: Run classification and source-manifest validation only; archive placement and its dry-run
are accepted independently under `archive-organization`.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/classifications/`, and
`$RESULTS_DIR/proofs/archive-classification/<proof-id>/`.
- Execution path: Forecast the closure; classify and validate coverage, hierarchy, evidence, exceptions,
fingerprints, and physical/virtual source accounting; rerun unchanged and record cache hits.
- Acceptance gates: Every physical inventory item has one complete result; virtual members retain container
links; source references and calibration metrics validate; supplied bytes remain unchanged; the
identical rerun invokes no heavy classifier; proof artifacts and checksums are complete.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Russian NLP -- `russian-nlp`

#### build-russian-language-morphology-and-terminology-lane

Implement language identification, encoding/noise signals, token/morphological analysis, and
versioned dictionaries without changing source evidence.

- Serves: `russian-nlp` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Dependencies: `implement-normalization-dedupe-and-chunking`;
`implement-stage-dag-cli-and-make-targets`.
`review-corpus-and-control-integrity`.
- User-visible outcome: Russian and mixed-language documents expose normalized terms, lemmas where
useful, abbreviations, and corpus terminology for search and extraction.
- Scope boundary: Produce analysis views and mappings only; original text and offsets remain
authoritative.
- Data and artifact paths: `$RESULTS_DIR/normalized/nlp/`, `ontology.term`, `configs/nlp/`,
`src/arxiv_int/nlp/russian/`, and NLP fixtures.
- Execution path: Compare supported local language/morphology libraries; model Cyrillic/Latin,
e/yo variants, abbreviations, technical tokens, and mixed language; emit versioned term statistics
and
glossary proposals.
- Acceptance gates: Language and normalization metrics pass by fixture slice; offsets map to
original evidence; dictionary changes are versioned; unsupported/ambiguous tokens remain explicit.
- Documentation target: `docs/impl/current/russian-nlp.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### evaluate-general-and-domain-ner

Combine a CPU Russian NER baseline with a bounded multilingual/custom-label candidate for people,
organizations, locations, equipment, models, suppliers, materials, standards, and dates.

- Serves: `russian-nlp` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `build-russian-language-morphology-and-terminology-lane`;
`create-evaluation-fixtures-and-metrics`.
- User-visible outcome: Entity mentions carry type, confidence, original source span, model/version,
and an understood per-type error rate.
- Scope boundary: Detect mentions; canonical merging belongs to identity resolution and acceptance
does not rely on one aggregate F1.
- Data and artifact paths: `$RESULTS_DIR/normalized/mentions/`, `kg.mention`, `configs/nlp/ner/`, and
`$RUNS_DIR/<run-id>/evaluation/ner/`.
- Execution path: Measure Natasha/Slovnet or equivalent CPU baseline; compare GLiNER-style custom
labels on a bounded sample; calibrate thresholds per type; preserve overlapping mentions and
failure reasons.
- Acceptance gates: Per-type precision/recall and span-overlap metrics produce a declared profile;
high-impact low-precision types stay review-only; inference cost and fallback behavior fit the
resource budget.
- Documentation target: `docs/impl/current/russian-nlp.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### prove-russian-nlp-on-provided-archive

Run the language, morphology, terminology, and NER stages on supplied archive content and publish
their proof bundle.

- Serves: `russian-nlp` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `evaluate-general-and-domain-ner`;
`prove-pipeline-control-on-provided-archive`.
- User-visible outcome: The supplied Russian and mixed-language documents expose inspectable terms,
language/noise results, mentions, source offsets, model identities, and measured failure classes.
- Scope boundary: Prove configured NLP profiles on available archive languages/types; do not treat
unreviewed mentions as canonical objects or infer quality for absent strata.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/nlp/`, mention tables,
and `$RESULTS_DIR/proofs/russian-nlp/<proof-id>/`.
- Execution path: Forecast; run NLP and mention extraction; validate schemas, language coverage,
offset/source mapping, per-type summaries, and model fingerprints; rerun unchanged and record
dictionary/model cache hits.
- Acceptance gates: All usable NLP outputs validate and resolve to source spans; unsupported and
ambiguous cases are counted; configured metrics are reported by present stratum; unchanged rerun
performs no heavy NER or morphology work; incomplete evidence keeps the task open.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/russian-nlp.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

### Identity, ontology, and graph -- `identity-ontology-graph`

#### implement-ontology-snapshots-and-geotemporal-contracts

Bind evolving ontology and source-asserted place/time semantics to reproducible stage inputs.

- Serves: `identity-ontology-graph` -- [Ontology design](../design/spec.md#ontology-design);
[Geotemporal assertions](../design/spec.md#geotemporal-assertions).
- Agent status: CLEAR
- Dependencies: [Versioned ontology assets](records/0013-contract-gov-establish-versioned-ontology-assets.md);
[Domain contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
`implement-stage-dag-cli-and-make-targets`; `create-evaluation-fixtures-and-metrics`.
- Human review handoff:
[approve-entity-merge-and-ontology-policy](#approve-entity-merge-and-ontology-policy)
ontology/geotemporal candidate semantics and compatibility examples;
include ontology drafts from `review/ontology/`; merge curves come from the resolution producer.
Packet: `$RUNS_DIR/<run-id>/review/identity-ontology/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve/revise merge thresholds, ontology terms and geotemporal interpretation;
keep drafts unpublished.
- User-visible outcome: Every fact/graph/report run names one immutable ontology interpretation and
preserves asserted time/place uncertainty; new terms can be reviewed without changing active meaning.
- Scope boundary: Register the existing `ontology` configuration stage, versioned draft proposals,
and typed geotemporal contracts/validators. Reuse Location and domain terms; no autonomous axiom
acceptance, remote geocoder, GIS platform or extra database extension. Published vocabulary stays
separate from candidates; unknown terms stay proposed/unmapped until human review.
- Data and artifact paths: `ontology/`, `contracts/`, `src/arxiv_int/ontology/`, mirrored tests,
additive Alembic revisions where required, `$RUNS_DIR/<run-id>/{ontology,review/ontology}/`.
- Execution path: Seal term/mapping/shape/policy fingerprints; retain prior snapshots and explicit
replacement/deprecation mappings; bind ontology identity into validation and projection reuse keys.
Define source-valid versus recorded time, timezone/precision/open intervals, asserted locations,
CRS/axis/units/uncertainty and domain revision/effectivity qualifiers. Implement shared checks and
stage outputs; consumers reuse them. Emit draft-term and compatibility examples for human review.
- Acceptance gates: Additive terms preserve prior replay; changed active meaning, mixed/stale
snapshots and draft leakage refuse publication. Subclass-compatible consumers work; disjoint types
fail. Partial dates/unknown CRS stay uncertain; inverted intervals and invalid coordinates fail;
shared addresses do not merge people/companies; temporal role and product revision boundaries are
replayable. Schema changes follow existing contract/evolution/migration gates.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### implement-probabilistic-entity-resolution

Build reversible object clusters from mentions using blocking, explainable comparisons, and labelled
operating points.

- Serves: `identity-ontology-graph` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Dependencies: `evaluate-general-and-domain-ner`; [Canonical relational schema](records/0021-store-create-canonical-relational-schema.md);
`create-evaluation-fixtures-and-metrics`.
`implement-ontology-snapshots-and-geotemporal-contracts`.
- Human review handoff:
[approve-entity-merge-and-ontology-policy](#approve-entity-merge-and-ontology-policy)
merge curves and ontology/geo-time candidate semantics;
include ontology drafts from `review/ontology/`.
Packet: `$RUNS_DIR/<run-id>/review/identity-ontology/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve/revise merge thresholds, ontology terms and geotemporal interpretation;
keep drafts unpublished.
- User-visible outcome: Aliases such as organization names, suppliers, equipment models, and
transliterations resolve to canonical objects with match evidence and uncertainty.
- Scope boundary: Propose or apply reversible cluster overlays; never rewrite source mentions or
auto-merge below the approved precision threshold.
- Data and artifact paths: `kg.object`, `kg.alias`, `kg.resolution_edge`, `kg.cluster_version`,
`$RESULTS_DIR/normalized/linkage/`, and `src/arxiv_int/identity/`.
- Execution path: Create deterministic unresolved anchors before linkage; retain original
mention/fact anchors
through versioned merge/split overlays. Clusters are overlays over domain objects, not new ontology
classes; helper linkage tables stay hidden from catalogs and analyst graph labels per
[Ontology design](../design/spec.md#ontology-design).
Use the selected maintained Splink release directly behind
the local seam with DuckDB; define
blocking and comparison specs; train/calibrate from reviewer labels; persist the model, thresholds,
pair probabilities, and cluster algorithm.
Keep Splink-generated DuckDB SQL inside the maintained adapter; prepare inputs with Polars
and shared Pandera checks. Express relational cluster/alias projection models in dbt with
relationship and stable-key tests; persist review decisions through typed transactions.
- Acceptance gates: Fixture linkage and same-name/jurisdiction/identifier nonmatches pass; archive thresholds
remain proposals until reviewed; only an approved policy may apply automatic merges; replay does
not refit; uncertain/rejected pairs remain separate; rollback restores the
prior cluster view.
Time-bounded roles and shared/ambiguous locations cannot merge unrelated identities;
merge/split replay preserves source anchors, ontology snapshot and asserted validity.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### build-and-validate-age-projection

Project accepted and selected proposed canonical objects/facts into a versioned AGE graph, with
recursive SQL and open export fallbacks.

- Serves: `identity-ontology-graph` -- [AGE graph projection](../design/spec.md#age-graph-projection);
[Ontology design](../design/spec.md#ontology-design).
- Agent status: RUN NEEDED
- Dependencies: `implement-probabilistic-entity-resolution`;
`implement-fact-validation-conflict-and-review-overlays`;
[0025](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
[Versioned ontology assets](records/0013-contract-gov-establish-versioned-ontology-assets.md).
- User-visible outcome: Operators can run bounded Cypher traversals and inspect a graph whose nodes
and edges resolve back to canonical facts and evidence.
- Scope boundary: Projection and bounded query API only; no Neo4j GDS parity claim and no large text
duplication into AGE.
- Data and artifact paths: AGE graph schemas, `ctl.projection`, `$RUNS_DIR/<run-id>/graph/`,
`src/arxiv_int/graph/`, and GraphML/JSON-LD/Turtle exports.
- Execution path: Batch vertices/edges with stable ids; checkpoint high-water marks; validate
counts, ids, sampled paths, and SQL/Cypher results; switch active graph version atomically;
enforce depth/result/time limits.
Project only semantically meaningful ontology classes and predicates; hide helper/projection
bookkeeping from analyst-facing labels. Query exports may yield subclasses of a requested class;
do not invent parallel labels for existing terms.
Use dbt models and data tests for relational vertex/edge inputs, and named SQL/Cypher assets
for bounded parity probes. Alembic owns graph lifecycle metadata; the narrow AGE adapter owns
projection commands and quality results gate the active-pointer transaction.
- Acceptance gates: Rebuild is deterministic; sampled traversals match recursive SQL; evidence
lookup succeeds for every sampled edge; AGE-disabled mode exports the same logical graph; failed
build leaves prior graph active. Analyst-facing labels contain published domain classes only;
helper types are absent from catalogs and graph entry points.
Pinned ontology labels and source-valid/recorded-time/place filters agree with SQL. Draft/deprecated
term handling is explicit, stale snapshots cannot activate, and unknown place/time is not fabricated.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### prove-identity-ontology-graph-on-provided-archive

Resolve identities, validate ontology assets, build the graph or fallback exports, and publish the
supplied-archive proof bundle.

- Serves: `identity-ontology-graph` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `build-and-validate-age-projection`;
`prove-knowledge-extraction-on-provided-archive`.
- Human review handoff:
[approve-entity-merge-and-ontology-policy](#approve-entity-merge-and-ontology-policy)
sealed merge/ontology/geo-time review packet.
Packet: `$RUNS_DIR/<run-id>/review/identity-ontology/`.
Ready after this proof and its named producer inputs pass.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve/revise merge thresholds, ontology terms and geotemporal interpretation;
keep drafts unpublished.
- User-visible outcome: Supplied-archive objects, aliases, candidate clusters, ontology terms, and
bounded graph paths are inspectable with reversible decisions and source evidence.
- Scope boundary: Use approved or explicitly proposed review states; do not silently merge uncertain
entities, publish disputed ontology changes, or require AGE when the declared fallback is active.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
identity/ontology/graph stores and
exports, and `$RESULTS_DIR/proofs/identity-ontology-graph/<proof-id>/`.
- Execution path: Forecast; run entity resolution and ontology validation; build the active AGE or
relational/open-export graph; reconcile counts and sampled SQL/path parity; resolve edge evidence;
rerun unchanged and capture linkage/reasoning/projection cache hits.
Apply [Ontology design](../design/spec.md#ontology-design): additive terms only, hidden helpers,
and producer/consumer typing on sampled catalog and graph labels.
- Acceptance gates: Cluster and ontology validators pass at declared policies; graph/fallback counts
and sampled paths agree with canonical facts; every sampled edge has evidence; unchanged rerun avoids
heavy linkage and graph rebuild; failed projection never replaces the prior active version.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### review-knowledge-and-identity-integrity

Review the integrated milestone before domain projection builders.

- Serves: `identity-ontology-graph` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `build-and-validate-age-projection`;
`implement-fact-validation-conflict-and-review-overlays`;
`extract-financial-and-bookkeeping-records`; `extract-product-and-assembly-records`.
`implement-ontology-snapshots-and-geotemporal-contracts`.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
Use deterministic integration evidence and inspect provided-archive proofs when available;
this verdict permits fixture implementation, not real-data or CUDA promotion.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/proof artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace mention anchors versus clusters,
merge/split replay, exact fact evidence, ontology/domain
constraints including [Ontology design](../design/spec.md#ontology-design) (domain terms, hidden
helpers, additive extension, producer/consumer typing), financial/product roles, review overlays
and SQL/graph parity;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
Review dynamic ontology proposal/publish/deprecate and invalidation/replay boundaries. Verify
source-valid versus recorded time, partial dates/timezones, location/CRS uncertainty, role changes
and product revision/effectivity across facts, SQL and AGE. Distinguish party/account/transaction,
product model/revision/equipment instance and explicit assembly relations; do not expose helper types.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
An additive ontology change preserves old-snapshot answers; stale or incompatible meanings refuse;
geotemporal filters agree across engines. Same-name/shared-address entities stay separable; temporal
coincidence and amount/model similarity cannot invent domain relations or accepted facts.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

### Knowledge extraction -- `knowledge-extraction`

#### implement-provenance-bearing-fact-extraction

Extract proposed facts with deterministic patterns/table rules first and validated local structured
LLM calls for bounded high-value lanes.

- Serves: `knowledge-extraction` --
[Canonical object and fact model](../design/spec.md#canonical-object-and-fact-model)
- Agent status: RUN NEEDED
- Dependencies: `evaluate-general-and-domain-ner`;
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
`implement-probabilistic-entity-resolution`; [Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
[Canonical relational schema](records/0021-store-create-canonical-relational-schema.md).
`implement-ontology-snapshots-and-geotemporal-contracts`.
- Human review handoff:
[approve-fact-review-and-publication-policy](#approve-fact-review-and-publication-policy)
per-type outcomes, conflicts, interval/place ambiguity and proposed inclusion states.
Packet: `$RUNS_DIR/<run-id>/review/facts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: choose auto-accepted/proposed/review-required fact types and conflict treatment.
- User-visible outcome: Design/revision, assembly/component, equipment, supplier, order, shipment,
invoice, payment, date, quantity, and other relations are queryable with exact source evidence and
extraction provenance.
- Scope boundary: Insert `proposed` assertions only; no automatic truth acceptance and no ontology
axiom invention.
- Data and artifact paths: `$RESULTS_DIR/normalized/facts/`, `kg.fact`, `kg.fact_qualifier`,
`src/arxiv_int/extraction/facts/`, generated output schemas, and prompt packages.
- Execution path: Implement generic typed rule/table extractors and unresolved-object bindings; domain-specific
financial and product adapters are separate tasks; register ontology asset validation and facts
through the stage registry; define JSON-schema LLM envelopes; retrieve
bounded evidence; validate source spans,
types, units, currencies, model output, and one bounded repair; batch and checkpoint by content hash.
Reuse existing ontology predicates; do not invent equivalent terms or write disjoint types into
domain/range slots ([Ontology design](../design/spec.md#ontology-design)).
Use generated structured-output validation followed by shared Pandera batch checks; preserve
evidence/semantic validators and write proposed rows through typed SQLAlchemy/COPY adapters.
Consume the pinned ontology and shared geotemporal contracts. Preserve source-valid and recorded
time separately; keep timezone/precision/place uncertainty and raw assertion provenance. An unknown
term or ambiguous place/time remains proposed/unknown, never a newly accepted ontology axiom.
- Acceptance gates: Malformed, unsupported, uncited, and span-mismatched outputs are retained as
typed failures, not facts; per-type precision/recall and citation validity are measured; rerun is
idempotent.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### extract-financial-and-bookkeeping-records

Extract structured financial records and evidenced legal-entity/person roles before reconciliation.

- Serves: `knowledge-extraction` -- [Financial, bookkeeping, and party relationship semantics](../design/spec.md#financial-bookkeeping-and-party-relationship-semantics)
- Agent status: RUN NEEDED
- Dependencies: `implement-provenance-bearing-fact-extraction`; [Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md).
- User-visible outcome: Invoices, payments, bookkeeping postings, corrections and party roles
become typed
proposed records with exact table/cell/page evidence and scoped identifiers.
- Scope boundary: Extract source assertions and candidate links; do not equate co-occurrence with ownership,
same names with identity, an invoice with delivery, or a paid label with a bank event.
- Data and artifact paths: `src/arxiv_int/extraction/financial/`, financial contracts and fixtures,
`$RESULTS_DIR/normalized/facts/`, and `$RUNS_DIR/<run-id>/evaluation/financial/`.
- Execution path: Integrate table/document adapters for invoice and bank records, journal/ledger exports,
credit notes/reversals and contracts; preserve raw/decimal values, currency, debit/credit, dates,
formulas/cached values, role direction, and evidence; expose the lane under the registered facts stage.
Normalize tabular values with typed Polars expressions and explicit decimal/currency schemas;
reuse Pandera and existing domain rules without float arithmetic or silent coercion.
- Acceptance gates: Network-free fixtures cover same-name parties, multi-page/sheet tables,
OCR decimal errors,
negative/reversed entries, mixed currency and missing identifiers; no macros execute; per-field/type
metrics, typed failures, evidence anchors, stable ids and bounded resource usage are recorded.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### extract-product-and-assembly-records

Extract product descriptions, revisions and explicit assembly/component assertions with quantities.

- Serves: `knowledge-extraction` -- [Product, BOM, and supply-chain semantics](../design/spec.md#product-bom-and-supply-chain-semantics)
- Agent status: RUN NEEDED
- Dependencies: `implement-provenance-bearing-fact-extraction`; [Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md).
- User-visible outcome: Products, model/revision identifiers, equipment instances, components,
materials and
manufacturer claims remain distinguishable and evidence-backed.
- Scope boundary: Propose source assertions only; marketing mentions and related accessories do not imply
required components, quantities, manufacturing capability, or actual supply.
- Data and artifact paths: `src/arxiv_int/extraction/products/`, product/assembly fixtures and contracts,
`$RESULTS_DIR/normalized/facts/`, and `$RUNS_DIR/<run-id>/evaluation/products/`.
- Execution path: Parse product and assembly tables through existing extraction adapters; preserve
part number,
revision/effectivity, alternatives, quantity per parent and units; keep unknown values null;
register the bounded product lane under facts and measure against frozen examples.
Use typed Polars/PyArrow batches and shared Pandera quantity/unit/key checks; retain domain
validators for revision/effectivity and evidence semantics.
- Acceptance gates: Fixtures separate model from physical instance, explicit part-of from mention,
alternatives
from mandatory components, and incompatible revisions; citation validity and per-type/quantity
metrics pass; descriptions lacking BOM evidence yield no invented component assertions.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### implement-fact-validation-conflict-and-review-overlays

Validate facts against ontology and temporal/unit rules, group duplicates/contradictions, and expose
reversible review state.

- Serves: `knowledge-extraction` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: CLEAR
- Dependencies: `implement-provenance-bearing-fact-extraction`;
`extract-financial-and-bookkeeping-records`; `extract-product-and-assembly-records`;
[Versioned ontology assets](records/0013-contract-gov-establish-versioned-ontology-assets.md).
- Human review handoff:
[approve-fact-review-and-publication-policy](#approve-fact-review-and-publication-policy)
per-type outcomes, conflicts, interval/place ambiguity and proposed inclusion states.
Packet: `$RUNS_DIR/<run-id>/review/facts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: choose auto-accepted/proposed/review-required fact types and conflict treatment.
- User-visible outcome: Conflicting claims and uncertain facts remain visible and reviewable instead
of being silently collapsed into one value.
- Scope boundary: Validate and group; human acceptance thresholds and domain truth judgments remain
human-gated.
- Data and artifact paths: `kg.fact`, `kg.fact_conflict`, `kg.review_event`,
`$RESULTS_DIR/normalized/fact-findings/`, and `src/arxiv_int/extraction/validation/`.
- Execution path: Add domain/range, typed literal, unit, functional relation, temporal, duplicate,
contradiction, and evidence checks; create immutable decision events and reversible active views;
register `validate-facts` separately
from the upstream ontology configuration stage.
Honor producer/consumer typing: extractors may emit subclasses; validators accept the declared
domain/range or a declared superclass handler and reject disjoint types
([Ontology design](../design/spec.md#ontology-design)).
Reuse generated Pandera checks and existing ontology/domain predicates; express relational
duplicate/conflict groups and active review views as described dbt models with data tests. Keep
immutable review-event writes in typed SQLAlchemy transactions.
Reuse the ontology-stage geotemporal validators for interval, timezone, CRS/axis and uncertainty
semantics; no duplicate interpretation in extraction, SQL or graph. Pin rule/ontology snapshots in
review events and invalidate affected views on evolution while retaining historical replay.
- Acceptance gates: Synthetic and gold contradictions are found with measured precision; every
active status derives from an audit event; rejected/superseded facts retain evidence; rules are
versioned and replayable. Domain/range fixtures accept subclass instances and reject disjoint types.
Test open/partial/inverted time, unknown/invalid coordinates, conflicting location evidence and
role/revision boundary cases; as-of results distinguish source-valid from recorded time.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### prove-knowledge-extraction-on-provided-archive

Run fact extraction and validation on the supplied archive and publish the knowledge-extraction
proof bundle.

- Serves: `knowledge-extraction` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-fact-validation-conflict-and-review-overlays`;
`prove-russian-nlp-on-provided-archive`; `implement-evidence-based-pipeline-forecast`.
- Human review handoff:
[approve-fact-review-and-publication-policy](#approve-fact-review-and-publication-policy)
final measured type thresholds, evidence and review-cost packet.
Packet: `$RUNS_DIR/<run-id>/review/facts/`.
Ready after this proof passes.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: choose auto-accepted/proposed/review-required fact types and conflict treatment.
- User-visible outcome: Proposed design, commercial, and general facts from supplied files are
inspectable with exact evidence, validation findings, conflicts, and extractor/model provenance.
- Scope boundary: Exercise only forecast-approved deterministic and local-model lanes; do not
auto-accept facts or claim correctness for unreviewed domain assertions.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/facts/`, knowledge
tables, and `$RESULTS_DIR/proofs/knowledge-extraction/<proof-id>/`.
- Execution path: Forecast; run configured fact lanes and validators; reconcile input/output/failure
counts; sample evidence-span resolution and conflict grouping; rerun unchanged and capture rule/model
cache decisions.
- Acceptance gates: Every emitted fact passes shape and evidence validation or remains a typed
failure; conflicts and review states are preserved; present-type metrics and coverage are reported;
unchanged rerun does not invoke heavy extraction; proof checksums and fingerprints validate.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

### Domain investigation artifacts -- `domain-investigation-artifacts`

#### build-party-and-transaction-artifacts

Project party relationships and financial events into cited relationship and invoice/payment tables
and bounded graphs.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: [Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
`implement-fact-validation-conflict-and-review-overlays`; `implement-probabilistic-entity-resolution`.
`review-knowledge-and-identity-integrity`.
- Human review handoff:
[approve-domain-artifact-semantics-and-inclusion](#approve-domain-artifact-semantics-and-inclusion)
family semantics, graph/table reconciliation, valid-empty/conflict and inclusion examples.
Packet: `$RUNS_DIR/<run-id>/review/domain-artifacts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve per-family semantics/inclusion, or retain partial/review-only/disabled families.
- User-visible outcome: Analysts can trace directed legal-entity/person roles, financial events,
invoice balances
and payment allocation candidates to their source evidence.
- Scope boundary: Generate bounded derived views from selected review states; do not silently
promote proposed facts, reconcile currencies without a sourced rate, or claim completeness beyond
reported evidence coverage.
- Data and artifact paths: `$RESULTS_DIR/normalized/domain-artifacts/`,
`src/arxiv_int/domain_artifacts/`, `$RUNS_DIR/<run-id>/artifacts/`, reviewed domain fixtures, and
snapshot/render tests.
- Execution path: Project canonical participants/roles relationally; calculate decimal invoice
totals and
many-to-many allocations with currency, tolerance, credit/reversal and time constraints; distinguish
matched, partial, overallocated, disputed, duplicate and unmatched states; render bounded graphs
from the same tables without requiring AGE.
Put reconciliation joins, allocations, balances and party views in named dbt models with grain,
decimal/currency definitions, source/ref dependencies and domain data tests; use typed Polars for
local export preparation and shared quality checks before publishing.
- Acceptance gates: Frozen positive/negative fixtures prove party direction, no inferred ownership
from payment,
no over-allocation silently accepted, partial/reversed/multi-invoice payments, source arithmetic,
uncertainty, exact evidence and graph/table parity. Empty requires processed eligible inputs;
unsupported or failed extraction remains partial/failed. Archive proof is separate from fixtures.
Party roles use asserted validity and the pinned ontology/identity snapshot; shared addresses,
nearby dates and equal amounts cannot establish identity, delivery or settlement without evidence.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### build-product-bom-and-supply-chain-artifacts

Build revision-aware BOM hierarchies and evidence-scoped supply-chain analysis from product facts.

- Serves: `domain-investigation-artifacts` -- [Product, BOM, and supply-chain semantics](../design/spec.md#product-bom-and-supply-chain-semantics)
- Agent status: RUN NEEDED
- Dependencies: `implement-fact-validation-conflict-and-review-overlays`;
[Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
`implement-probabilistic-entity-resolution`.
`review-knowledge-and-identity-integrity`.
- Human review handoff:
[approve-domain-artifact-semantics-and-inclusion](#approve-domain-artifact-semantics-and-inclusion)
family semantics, graph/table reconciliation, valid-empty/conflict and inclusion examples.
Packet: `$RUNS_DIR/<run-id>/review/domain-artifacts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve per-family semantics/inclusion, or retain partial/review-only/disabled families.
- User-visible outcome: An analyst can inspect assemblies, cumulative component requirements when justified,
supplier/customer paths and concentration within a stated product/time scope.
- Scope boundary: Use only explicit component and commercial-stage evidence; do not complete
missing BOMs
or infer actual shipment from a catalog or quote. AGE is not required.
- Data and artifact paths: `src/arxiv_int/domain_artifacts/products/`, BOM/supply fixtures,
`$RESULTS_DIR/normalized/domain-artifacts/`, and `$RUNS_DIR/<run-id>/artifacts/`.
- Execution path: Build typed part-of edges and parent quantities; detect cycles and separate
alternatives and
revision/effectivity; derive rollups only with compatible units and retain operands; project quoted,
ordered, invoiced, shipped, received and paid stages; calculate concentration with denominators.
Use described dbt models for relational BOM/supply projections and aggregation, with explicit
unit/revision grain and cycle/rollup tests. Keep traversal algorithms in focused typed Python where
needed; validate export batches through Pandera and reuse existing domain rules.
- Acceptance gates: Fixtures cover repeated components, multi-level rollups, cycles, unknown
quantities, mixed
units, alternatives, conflicting revisions and incomplete supplier coverage; tables/graphs match,
derivations resolve, outputs are bounded and repeatable; marketing-only descriptions allow empty BOM.
Pin ontology, identity and revision/effectivity scope; cross-revision components and temporally
incompatible supplier roles remain conflicts/unknown. Mention, co-location and marketing similarity
never imply assembly membership or actual supply.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### register-and-expose-domain-artifacts

Publish all domain artifacts through an atomic per-run registry and expose discovery links without
creating another source of truth.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: CLEAR
- Dependencies: `build-party-and-transaction-artifacts`;
`build-product-bom-and-supply-chain-artifacts`; `implement-run-ledger-and-atomic-artifacts`.
- Human review handoff:
[approve-domain-artifact-semantics-and-inclusion](#approve-domain-artifact-semantics-and-inclusion)
family semantics, graph/table reconciliation, valid-empty/conflict and inclusion examples.
Packet: `$RUNS_DIR/<run-id>/review/domain-artifacts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve per-family semantics/inclusion, or retain partial/review-only/disabled families.
- User-visible outcome: Every run reaching the domain-artifact stage lists which special artifacts
were produced, partial, empty, or failed and provides a verified local path plus evidence/coverage
summary for each.
- Scope boundary: Register immutable outputs and read-only links; do not mark failed output
successful, embed unrestricted source text, or let dashboards become the canonical registry.
- Data and artifact paths: `ctl.artifact`, additive `src/arxiv_int/migrations/versions/`,
`$RUNS_DIR/<run-id>/artifacts/registry.{json,parquet}`, `src/arxiv_int/reporting/artifacts/`, CLI/API
responses, and registry contract tests.
- Execution path: Generate and apply additive artifact-registry Alembic Python revisions; assign
stable artifact ids; capture type/schema/generator/input/policy fingerprints, paths, media types,
checksums, counts, evidence coverage, status, and failure reason; validate output before one atomic registry
publication; add `run artifacts` listing and report links.
Use contract-derived Alembic Python revisions and typed SQLAlchemy registry transactions; bind
model lineage and shared quality evidence to each artifact fingerprint before publication.
- Acceptance gates: Contract fixtures cover produced/partial/empty/failed states; every successful
row resolves to checksum-valid files and source evidence; missing or corrupt output prevents
publication; unchanged reruns reuse ids; CLI/API and manifest/SQL registries agree.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### prove-domain-investigation-artifacts-on-provided-archive

Generate every applicable relationship, BOM, supply-chain, and invoice/payment artifact family from
the supplied archive and publish its proof bundle.

- Serves: `domain-investigation-artifacts` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `register-and-expose-domain-artifacts`;
`prove-identity-ontology-graph-on-provided-archive`.
`review-domain-artifact-and-triage-boundaries`; `approve-entity-merge-and-ontology-policy`;
`approve-fact-review-and-publication-policy`.
- Human review handoff:
[approve-domain-artifact-semantics-and-inclusion](#approve-domain-artifact-semantics-and-inclusion)
sealed per-family metrics and decision packet.
Packet: `$RUNS_DIR/<run-id>/review/domain-artifacts/`.
Ready after this proof and its required fact/ontology decisions pass.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve per-family semantics/inclusion, or retain partial/review-only/disabled families.
- User-visible outcome: The run artifact registry exposes each applicable supplied-archive domain
view, its table/graph files, evidence coverage, conflicts, review policy, and production status.
- Scope boundary: Generate only evidence-supported bounded views; accept contract-valid `empty` or
`partial` families and never manufacture relations to make a graphical artifact non-empty.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/domain-artifacts/`, and
`$RESULTS_DIR/proofs/domain-investigation-artifacts/<proof-id>/`.
- Execution path: Forecast; build all configured artifact families; validate arithmetic,
table-to-graph parity, source links, renders, registry rows, and checksums; rerun unchanged and record
projection/render cache hits.
- Acceptance gates: Every configured family is honestly `produced`, `partial`, or `empty` with a
valid reason; no failed output is registered as successful; evidence and policy resolve for every
element; identical rerun performs no heavy extraction, projection, or rendering.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Anomaly analysis -- `anomaly-analysis`

#### implement-explainable-anomaly-detectors

Create deterministic constraint and bounded statistical detectors with evidence and cohort guards.

- Serves: `anomaly-analysis` -- [Anomaly detection and triage](../design/spec.md#anomaly-detection-and-triage)
- Agent status: CLEAR
- Dependencies: `register-and-expose-domain-artifacts`; `create-evaluation-fixtures-and-metrics`.
- Human review handoff:
[approve-anomaly-triage-policy](#approve-anomaly-triage-policy)
detector coverage, hard negatives, review replay and proposed budgets.
Packet: `$RUNS_DIR/<run-id>/review/anomalies/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: enable, retain constraints only, revise or disable each detector and its review budget.
- User-visible outcome: Analysts receive explainable data, financial, relationship/supply-chain
and BOM findings
with observed versus expected values and coverage limits.
- Scope boundary: No fraud verdicts, hidden identity merges, source edits or ML training;
unsupported cohorts
produce insufficient-evidence and a detector may yield no useful findings.
- Data and artifact paths: `src/arxiv_int/analytics/`, `configs/anomalies/`, finding contracts,
`$RESULTS_DIR/normalized/anomalies/`, and deterministic positive/negative fixtures.
- Execution path: Generate finding schemas and register anomalies; implement constraints, comparable-currency
amount cohorts, duplicate/unmatched candidates, graph concentration/cycles and BOM consistency;
retain rule/version, operands, source ids, denominator, time window, sample floor and rank rationale.
Define relational cohorts and deterministic aggregate rules in described dbt models; use
Polars expressions for local batch calculations. Reuse Pandera/domain checks for input validity,
and distinguish expected detector findings from data-quality failures.
- Acceptance gates: Fixtures prove exact expected flags and hard negatives, decimal/unit
correctness, minimum
cohort and temporal-leakage guards, source/derivation validity, deterministic grouping, and bounded
memory; per-detector accuracy and review-budget metrics use predeclared thresholds.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### implement-anomaly-review-and-triage-exports

Publish findings, reversible review events and bounded explanation views for analyst triage.

- Serves: `anomaly-analysis` -- [Anomaly detection and triage](../design/spec.md#anomaly-detection-and-triage)
- Agent status: CLEAR
- Dependencies: `implement-explainable-anomaly-detectors`; `implement-incremental-reconciliation-and-stale-pruning`.
- Human review handoff:
[approve-anomaly-triage-policy](#approve-anomaly-triage-policy)
detector coverage, hard negatives, review replay and proposed budgets.
Packet: `$RUNS_DIR/<run-id>/review/anomalies/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: enable, retain constraints only, revise or disable each detector and its review budget.
- User-visible outcome: Analysts can filter and inspect flags, see why each ranked, and record explained/dismissed
outcomes without changing evidence.
- Scope boundary: Reuse canonical review/artifact interfaces; no new truth store, autonomous accusations,
implicit feedback training, or unrestricted graph queries.
- Data and artifact paths: `src/arxiv_int/analytics/`, `kg.review_event`, registry contracts,
`$RUNS_DIR/<run-id>/artifacts/anomalies/`, and review/export fixtures.
- Execution path: Expose anomalies list/show and explicit review operations; publish JSON/Parquet, comparison
tables and bounded subgraphs; preserve stable finding groups and review reasons across reruns;
invalidate computations after source, identity, policy or cohort changes.
Keep triage projections in tested dbt models, review writes in typed SQLAlchemy transactions,
and export batch validation in the shared Pandera adapter.
- Acceptance gates: Review replay and undo retain source facts; stale findings are labelled and recomputed;
rank/filter definitions and skipped/insufficient counts are present; empty outputs validate; exports
and canonical counts agree; changed evidence cannot inherit a misleading resolved state.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### review-domain-artifact-and-triage-boundaries

Review domain semantics, registry publication and triage accounting before report integration.

- Serves: `anomaly-analysis` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `review-knowledge-and-identity-integrity`; `register-and-expose-domain-artifacts`;
`implement-explainable-anomaly-detectors`; `implement-anomaly-review-and-triage-exports`.
- User-visible outcome:
Reports and human packets inherit consistent evidenced domain relations and honest anomaly states.
- Scope boundary:
Review fixtures and existing producer evidence; do not accept domain policies, certify financial
truth, or require nonempty anomaly findings. Archive proofs and human judgments remain separate.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace party/account roles, product model/revision/instance, BOM alternatives/units/effectivity,
invoice arithmetic and payment allocation against exact fact evidence. Check pinned ontology and
geotemporal joins, registry/graph/table parity, triage denominators and review replay after changes.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
No mention or similarity becomes part-of/supplier/paid; wrong revision/time joins fail; empty,
partial and conflicted outputs retain meaning. Missing evidence or failed validation blocks
publication; no unsupported anomaly allegation appears. Candidate review packets reconcile to data.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: none; this is the bounded checkpoint.

#### prove-anomaly-analysis-on-provided-archive

Run configured detectors on the provided archive and publish honest quality and review-cost evidence.

- Serves: `anomaly-analysis` -- [Anomaly detection and triage](../design/spec.md#anomaly-detection-and-triage)
- Agent status: RUN NEEDED
- Dependencies: `implement-anomaly-review-and-triage-exports`;
`prove-domain-investigation-artifacts-on-provided-archive`;
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md).
`review-domain-artifact-and-triage-boundaries`.
- Human review handoff:
[approve-anomaly-triage-policy](#approve-anomaly-triage-policy)
sealed enable/constraints-only/revise/disable packet.
Packet: `$RUNS_DIR/<run-id>/review/anomalies/`.
Ready after this proof passes.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: enable, retain constraints only, revise or disable each detector and its review budget.
- User-visible outcome: The archive has cited anomaly candidates, or an explicit no-findings/insufficient-data
result, with per-detector coverage and an interpretable review workload.
- Scope boundary: No claims of wrongdoing or anomaly-free data; only bounded authorized source
scope and
predeclared final evaluation, without tuning on the final split.
- Data and artifact paths: `$RESULTS_DIR/proofs/anomaly-analysis/<proof-id>/`, frozen detector profiles,
review labels and normal finding artifacts.
- Execution path: Forecast; run constraints and eligible cohort detectors; verify citations and input
snapshots; score per-detector precision/recall and precision at review budget; rerun unchanged
and capture cache hits, time and memory; report retain-constraints or not-selected where justified.
- Acceptance gates: Every detector has evaluated/skipped/insufficient counts and a replayable
verdict; hard
negatives, cohort leakage and review burden are reported; findings/empty outputs validate; no
heavy work on the identical rerun and no private source content in repository summaries.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Discovery and visualization -- `discovery-visualization`

#### implement-scalable-topic-discovery

Build CPU-first topic discovery and drift tracking with an optional bounded embedding-based lane.

- Serves: `discovery-visualization` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `implement-normalization-dedupe-and-chunking`;
`build-russian-language-morphology-and-terminology-lane`; optional
`implement-selective-embedding-pipeline` for the embedding lane.
- User-visible outcome: The archive exposes stable topics, representative documents, terms,
hierarchy candidates, and change across partitions/time.
- Scope boundary: Topic labels are proposals and sampling is explicit; do not run BERTopic/HDBSCAN
over all chunks without a bounded design.
- Data and artifact paths: `$RESULTS_DIR/normalized/topics/`, `search.topic`, `search.topic_assignment`,
`configs/topics/`, and `$RUNS_DIR/<run-id>/evaluation/topics/`.
- Execution path: Compare TF-IDF/NMF and MiniBatchKMeans on stratified samples or document
centroids; optionally compare embedding clustering; persist centroids/terms/representatives; align
versions and measure drift/stability.
- Acceptance gates: Stability, coherence proxy, coverage, outlier rate, runtime, and expert sample
review are reported; repeated seeded run is reproducible within tolerance; topic ids are
versioned.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### build-company-product-and-person-catalogs

Produce the three required entity catalogs and related equipment/supplier views from pinned snapshots.

- Serves: `discovery-visualization` -- [Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: CLEAR
- Dependencies: `implement-probabilistic-entity-resolution`; `implement-fact-validation-conflict-and-review-overlays`;
`implement-scalable-topic-discovery`.
- User-visible outcome: Company, product and person lists expose identifiers, aliases, roles,
evidence counts,
unresolved identities and time-qualified relation drill-down.
- Scope boundary: Catalog views do not create new identities or infer legal form, ownership
or actual supply.
Keep organization/person, product/model/revision, and equipment instances distinct.
- Data and artifact paths: `src/arxiv_int/query/catalogs/`, catalog contracts, `$RESULTS_DIR/normalized/catalogs/`,
and `$RUNS_DIR/<run-id>/artifacts/catalogs/`.
- Execution path: Register catalogs and catalog company/product/person; implement filtered/paginated
CSV/Parquet/JSON exports and bounded relation/evidence views; publish one registry entry per required
catalog including empty states, snapshot fingerprints, coverage and review inclusion policy.
Build catalog relations as named dbt models with documented grain, source/ref, inclusion policy,
stable keys and relationship/count tests. Typed query adapters handle pagination and export;
Pandera validates exported batches against the same contracts.
- Acceptance gates: Fixtures prove role versus entity distinctions, same-name nonmatches,
aliases and identifiers,
source/identity merge-split/removal updates, counts against canonical views, complete citations,
empty categories and bounded query/export behavior.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### build-search-graph-and-report-interfaces

Expose bounded lexical/semantic/hybrid search, object/fact lookup, Cypher or SQL traversal, and
company/product/person catalogs and the analyst entry report through CLI and a small local API.

- Serves: `discovery-visualization` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: `calibrate-russian-tokenization-and-bm25`; `build-and-validate-age-projection`;
`register-and-expose-domain-artifacts`; `build-company-product-and-person-catalogs`;
`implement-anomaly-review-and-triage-exports`; `implement-investigation-profile-and-output-manifest`.
`implement-evidence-and-source-location-lookup`.
`review-domain-artifact-and-triage-boundaries`.
- Human review handoff:
[accept-operator-discovery-workflows](#accept-operator-discovery-workflows)
scenario instructions, entry points and evidence/state drill-down examples.
Packet: `$RUNS_DIR/<run-id>/acceptance/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept the cited investigation scenarios or record blocking usability/domain failures.
- User-visible outcome: An operator can find evidence, inspect objects and facts, traverse
relations, open the portable `reports/index.html`, see important supported findings and coverage, and
drill through catalogs, anomalies, BOM, supply-chain, invoice/payment and relation graphs to source
cells/pages without writing SQL or running viewer services.
- Scope boundary: Read-only query/report boundary with limits; no public multi-user web product and
no hidden acceptance of proposed facts.
- Data and artifact paths: `src/arxiv_int/query/`, `src/arxiv_int/reporting/`,
`$RUNS_DIR/<run-id>/reports/`, and API/query tests.
- Execution path: Add typed query objects, pagination, filters, review-state controls, evidence
expansion, escaped source snippets, deterministic summary/rank definitions, no-evidence/partial
report sections, per-document content overviews with extractive snippets and section/table pointers,
CSV/Parquet/HTML exports, and explain modes; register the `report`
stage body behind `arxiv-int report build RUN_ID` and `search lexical|semantic|hybrid`; constrain
text/depth/result/time.
Consume dbt-tested report/catalog marts and retained quality/lineage artifacts; use bound
SQLAlchemy query expressions for filters and pagination, reviewed SQL/Cypher assets for engine
queries, and Polars/PyArrow with Pandera for bounded exports. No report business transformations
are embedded in Python strings or dashboard query text.
- Acceptance gates: Scenario fixtures return complete citations and declared inclusion rules; SQL
injection and path tests pass; large/unbounded requests are refused; exports conform to generated
contracts; report manifest and pinned canonical snapshots agree; source snippets cannot execute
HTML/scripts or direct model/tool actions; portable report works without Grafana/AGE Viewer.
Time/place filters expose uncertainty and source-valid versus recorded scope; ontology/identity
snapshots are visible. Domain labels and same-name entities remain distinct across catalogs,
graphs, tables and source drill-down.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### provision-local-dashboards-and-age-viewer

Provision Grafana dashboards and the optional AGE Viewer profile without adding another canonical
store.

- Serves: `discovery-visualization` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Dependencies: `build-search-graph-and-report-interfaces`; Compose profiles documented in
[Portable runtime](current/portable-runtime.md).
- Human review handoff:
[accept-operator-discovery-workflows](#accept-operator-discovery-workflows)
scenario instructions, entry points and evidence/state drill-down examples.
Packet: `$RUNS_DIR/<run-id>/acceptance/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept the cited investigation scenarios or record blocking usability/domain failures.
- User-visible outcome: Local dashboards show pipeline progress, topics, entities, facts, conflicts,
and bounded graph views; AGE Viewer supports exploratory Cypher when enabled.
- Scope boundary: Provision read-only local tools; no internet exposure, corpus-bearing telemetry
export, or tool-owned source of truth.
- Data and artifact paths: `docker/grafana/`, `docker/age-viewer/`, Compose profiles, read-only
database role migrations, `$SERVICE_STATE_DIR/<service>/` for mutable service state, and
screenshot/query smoke fixtures.
- Execution path: Provision PostgreSQL datasource and dashboards as code from the repository, keep
only mutable service state under `SERVICE_STATE_DIR`; create read-only views; configure AGE Viewer;
document loopback URLs and lifecycle; add health and bounded-query smoke tests.
Read described dbt marts through bounded parameterized dashboard queries; keep metric
transformations in dbt models and provision role changes through Alembic Python revisions.
- Acceptance gates: Fresh profile start needs no manual datasource setup; read-only roles cannot
mutate canonical rows; dashboards load fixture data; deleting `SERVICE_STATE_DIR` loses no
provisioned definition; graph profile absence degrades cleanly.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### prove-discovery-and-visualization-on-provided-archive

Run topic discovery, search/report scenarios, exports, and configured local views against supplied
archive artifacts and publish the discovery proof bundle.

- Serves: `discovery-visualization` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `build-search-graph-and-report-interfaces`;
`prove-domain-investigation-artifacts-on-provided-archive`; `prove-anomaly-analysis-on-provided-archive`;
`prove-lexical-retrieval-on-provided-archive`. Viewer smoke is conditional on selecting that profile.
- Human review handoff:
[accept-operator-discovery-workflows](#accept-operator-discovery-workflows)
executable scenario packet, results and issue ledger.
Packet: `$RUNS_DIR/<run-id>/acceptance/`.
Ready after this proof and the listed policy decisions; name any still pending.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept the cited investigation scenarios or record blocking usability/domain failures.
- User-visible outcome: Operators can navigate supplied-archive topics, searches, objects, facts,
graphs, and domain reports through bounded interfaces whose displayed evidence can be verified.
- Scope boundary: Prove local read-only scenarios and available profiles; do not expose services
publicly, require an optional UI/AGE profile with a valid fallback, or claim usability acceptance for
scenarios not executed.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
topic/query/report/export artifacts, and
`$RESULTS_DIR/proofs/discovery-visualization/<proof-id>/`.
- Execution path: Forecast; run topics, company/product/person catalogs, anomaly views and
entry report generation; execute scripted lexical and available
hybrid, object/fact, graph, BOM, supply-chain, and invoice/payment scenarios; validate citations,
limits, exports, dashboards/views, and unchanged-rerun cache decisions.
- Acceptance gates: Every executed scenario resolves to bounded, policy-labelled source evidence;
exports and configured views validate; unavailable optional profiles have working fallbacks;
unchanged rerun avoids heavy topic/report recomputation; unresolved failures keep proof open.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### review-investigation-and-report-integrity

Review the integrated milestone before provided-archive end-to-end proof and scale pilots.

- Serves: `discovery-visualization` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `build-search-graph-and-report-interfaces`;
`implement-directory-to-knowledge-base-acceptance`; `implement-anomaly-review-and-triage-exports`.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
Use deterministic integration evidence and inspect provided-archive proofs when available;
this verdict permits fixture implementation, not real-data or CUDA promotion.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/proof artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace company/product/person catalogs,
invoice allocations, BOM units/revisions, supply roles,
anomaly cohorts/ranks, graph-table parity, one-generation reports and source drill-down;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

#### add-cited-local-question-answering (optional)

Provide bounded local questions and generative summary refinement only when citation quality
justifies it.

- Serves: `discovery-visualization` -- [Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Dependencies: `build-search-graph-and-report-interfaces`;
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md).
Lexical retrieval suffices; selected vectors are conditional.
- User-visible outcome: Analysts may ask questions over selected evidence and receive cited
answers or explicit
abstention without leaving the host.
- Scope boundary: Optional refinement; deterministic reports remain sufficient. No unrestricted SQL,
filesystem access, source edits, unsupported claims, or acceptance of instructions from documents.
- Data and artifact paths: `src/arxiv_int/query/answers/`, answer evaluation profiles, and
`$RUNS_DIR/<run-id>/evaluation/answers/`.
- Execution path: Retrieve bounded lexical evidence with optional selected hybrid inputs; generate schema-valid
answers with source-span references; validate citations and abstain on missing/conflicting evidence;
measure supported claims, refusal and cost on held-out questions.
- Acceptance gates: Fixtures and held-out questions cover hallucination, conflicting evidence,
prompt injection
and no-answer cases; local resource budget and citation validity pass or retain deterministic
reports with a recorded negative verdict.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Evaluation and evidence -- `evaluation-evidence`

#### implement-published-evidence-freshness-checks

Implement replayable lineage/freshness validation for measured claims published by reports and
current-state evidence references.

- Serves: `evaluation-evidence` --
[Implementation boundaries](../design/spec.md#implementation-boundaries)
- Agent status: CLEAR
- Dependencies: `create-evaluation-fixtures-and-metrics`; `implement-run-ledger-and-atomic-artifacts`.
- User-visible outcome: A stale run cannot continue to support a changed published claim.
- Scope boundary: Build ongoing evidence validation; routine review of each change remains part of that
change, not a deferred audit. Do not invent missing benchmarks.
- Data and artifact paths: `ctl.artifact`, run manifests, current-state measurements, and the docs
claim registry.
- Execution path: Link published metrics to run fields and content pins; list invalidations caused
by contract, model, profile, classification, or artifact changes.
Include Alembic revision identity, dbt model/input hashes and required Pandera/dbt rule outcomes
in freshness checks; a missing, stale or skipped validation report cannot certify an artifact.
- Acceptance gates: Every published number resolves to one immutable artifact field; implementation
boundaries remain explicit; orphan or stale claims fail CI.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

#### implement-directory-to-knowledge-base-acceptance

Exercise the complete investigation command on a mixed deterministic fixture and validate its entry report.

- Serves: `evaluation-evidence` -- [End-to-end run and output contract](../design/spec.md#end-to-end-run-and-output-contract)
- Agent status: CLEAR
- Dependencies: `build-search-graph-and-report-interfaces`; `implement-hierarchical-file-classification`;
`implement-investigation-profile-and-output-manifest`; `create-evaluation-fixtures-and-metrics`.
- User-visible outcome: One directory-to-report command proves every required family is wired
through real baseline
stage adapters, independent of optional vectors, viewers and archive organization.
- Scope boundary: Network-free bounded integration acceptance; mocked inference error cases do not prove
real CUDA model fit or archive quality. External host proof is a separate task.
- Data and artifact paths: `tests/integration/pipeline/`, mixed source fixtures, `configs/pipeline/`,
Make integration
target, and disposable configured runtime roots.
- Execution path: Use a text/document, financial table, product assembly, ambiguous parties,
malformed source
and cross-file relation; configure their roots in `.env`, run bare `make pipeline`, validate
manifest/report and every source anchor, then compare with the documented atomic chain on isolated
equivalent inputs. Rerun unchanged and test a source change/removal plus an interrupted publication.
- Acceptance gates: Required catalog/domain/anomaly entries, expected relations/amounts/BOM and valid-empty
cases match frozen expectations; exit/state semantics, bounded resources, no source writes,
cache reuse, coherent generation updates and source-level report drill-down all pass. No shell
activation, exports, separate forecast or post-run report/validation command is needed; aggregate
and atomic results agree logically. README availability changes only after the corresponding gates.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

#### publish-provided-archive-end-to-end-proof

Run evaluation and reporting over the supplied archive and publish one proof index covering every
usable pipeline stage and artifact family.

- Serves: `evaluation-evidence` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-directory-to-knowledge-base-acceptance`;
`prove-archive-classification-on-provided-archive`; `prove-discovery-and-visualization-on-provided-archive`;
`prove-anomaly-analysis-on-provided-archive`;
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md);
`create-evaluation-fixtures-and-metrics`. Semantic proof is required only for a selected vector branch.
`review-investigation-and-report-integrity`.
`approve-classification-policy`; `approve-entity-merge-and-ontology-policy`;
`approve-fact-review-and-publication-policy`; `approve-domain-artifact-semantics-and-inclusion`;
`approve-anomaly-triage-policy`; `accept-operator-discovery-workflows`.
- User-visible outcome: One command/report shows which pipeline stages have current proof on the
supplied file silos, which artifacts they produced, which optional branches were not selected, and
how every result resolves to evidence.
- Scope boundary: Evaluate and index bounded proof outputs; do not substitute this test archive for
representative-scale authorization or conceal failed, stale, blocked, or absent stages.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, prior proof bundles, and
`$RESULTS_DIR/proofs/evaluation-evidence/<proof-id>/` containing evaluation/report outputs and the
end-to-end proof index.
- Execution path: Set the authorized bounded archive scope and selected local inference lane in
`.env`; run `make setup` with edits/retries until ready, then bare `make pipeline` on one CUDA host.
Retain the automatic preflight/forecast and setup evidence; verify required
outputs, entry report and exact source anchors; capture actual device/model resources; join current
stage proofs for quality context, rerun unchanged and publish the coverage/provenance matrix.
- Acceptance gates: Every required usable stage has a current `passed` or valid-empty proof and
checksum-valid artifacts; every required output resolves through one knowledge-base generation;
optional disabled
branches cite selection reasons and fallbacks (measured verdicts for comparative claims); the end-to-end
report exposes all failures/coverage gaps; unchanged evaluation/report work is reused; private paths
and corpus content are absent from repository documentation.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

#### run-representative-scale-pilots

Measure storage amplification, throughput, memory, WAL/temp growth, retrieval quality, resume, and
rebuild on two progressively larger corpus slices.

- Serves: `evaluation-evidence` --
[Performance and scalability assumptions](../design/spec.md#performance-and-scalability-assumptions)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `publish-provided-archive-end-to-end-proof`; `implement-evidence-based-pipeline-forecast`;
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md);
`implement-backup-restore-and-rebuild-runbook`;
`test-failure-and-capacity-boundaries`. Optional branches participate only when selected.
`review-recovery-before-scale-pilots`.
- Human review handoff:
[authorize-full-corpus-run](#authorize-full-corpus-run)
pilot ranges, pins, scope, stop conditions and proposed decision.
Packet: `$RUNS_DIR/<run-id>/authorization/`.
Packet prepared here; approval remains pending `review-production-readiness-and-recovery` and human prerequisites.
Blocked consumer:
full-corpus execution (not another implicit agent implementation task).
Report readiness using the human-handoff workflow; never self-approve.
Decision: authorize-next, resize/reconfigure, subset-only or stop for the exact pins and budget.
- User-visible outcome: A capacity plan predicts normalized, classification, registered domain
artifact, heap, lexical, vector, graph, WAL, temp, backup, wall-time, and operator-review costs
before the full archive runs.
- Scope boundary: Run only approved representative slices; do not authorize the full corpus or
extrapolate without uncertainty and format mix.
- Data and artifact paths: Approved `$ARCHIVE_DIR` slices, `$RESULTS_DIR`, `$PGDATA_DIR`,
`$RUNS_DIR/<run-id>/pilot/`, and generated capacity report.
- Execution path: Run 0.1-1% or 50-200 GB pilot, tune bounded parameters, then a larger partition;
inject interruption; measure extraction yield, classification coverage, dedupe, chunks, indexes,
updates, reindex, vector tiers, domain artifacts, graph, and recovery. Archive reorganization stays
a separately authorized drill and is not implied by the pilot.
- Acceptance gates: Both runs remain within declared resource safety margins; estimates include
uncertainty and concurrent-rebuild space; every failure and excluded format is counted; report
ends in authorize-next, resize/reconfigure, retain-subset, or stop.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

### Operational recovery -- `operational-recovery`

#### harden-local-security-and-no-egress-mode

Enforce read-only input, loopback services, least-privilege roles, secret redaction, bounded paths,
container mounts, and a network-denied run mode.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: RUN NEEDED
- Dependencies: Compose profiles documented in [Portable runtime](current/portable-runtime.md);
[Canonical relational schema](records/0021-store-create-canonical-relational-schema.md);
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
`build-search-graph-and-report-interfaces`. Organizer hardening is accepted in its own capability.
- Human review handoff:
[accept-recovery-and-security-posture](#accept-recovery-and-security-posture)
access/retention checklist, restore inventory, reproduction commands and residual risks.
Packet: `$RUNS_DIR/<run-id>/review/recovery/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`review-recovery-before-scale-pilots`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: witness restore and accept/reject the exact posture and residual risks.
- User-visible outcome: The local stack can process prepared inputs without unintended network
access or writable archive access, with bounded read-only evidence and report queries.

- Scope boundary: Host-local hardening and verification; not a formal third-party penetration test
or multi-user internet deployment.
- Data and artifact paths: Compose security settings, database role migrations, `.env.example`,
`src/arxiv_int/security/`, and security integration fixtures.
- Execution path: Apply non-root/read-only mounts where supported, localhost ports, role separation,
URL/path allowlists, secret filters, image/model pin checks, and network-denied integration
profile.
- Acceptance gates: Prepared smoke succeeds with egress denied; pipeline archive writes fail;
document instructions cannot trigger tools, source writes, unbounded queries or external requests;
UI role mutations fail; secrets/corpus snippets
do not appear in logs; dependency/image scan findings are triaged without suppressing gates.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: `review-recovery-before-scale-pilots`.

#### implement-backup-restore-and-rebuild-runbook

Create and exercise backups for contracts/config, normalized artifacts, PostgreSQL, and projection
rebuild metadata.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: RUN NEEDED
- Dependencies: [0025](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
`harden-local-security-and-no-egress-mode`; `register-and-expose-domain-artifacts`.
Run the initial restore on disposable fixture/small-proof data before scale pilots.
- Human review handoff:
[accept-recovery-and-security-posture](#accept-recovery-and-security-posture)
access/retention checklist, restore inventory, reproduction commands and residual risks.
Packet: `$RUNS_DIR/<run-id>/review/recovery/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`review-recovery-before-scale-pilots`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: witness restore and accept/reject the exact posture and residual risks.
- User-visible outcome: A documented command sequence restores canonical state, classifications,
move/source lookup, and artifact registries, then validates or rebuilds search and graph projections
on a clean target path.
- Scope boundary: Single-host backup/restore and removable-disk workflow; no HA or enterprise
replica claim.
- Data and artifact paths: `scripts/backup/`, `scripts/restore/`, `Makefile` for `make backup` and
`make restore-check`, backup manifests outside `$PGDATA_DIR`, `$RUNS_DIR/<run-id>/recovery/`, and
`docs/guide/recovery.md`.
- Execution path: Capture extension/image/model ids, migrations and logical/physical backup covering
`PGDATA_DIR` with any configured WAL and tablespace roots as one unit, normalized/classification
manifests, review/identity/anomaly dispositions, configured policies, path-event ledgers, artifact
registries, checksums, and free-space requirements; restore
into a new directory, run contract/live-store/source-lookup checks, and rebuild disposable
projections.
Capture Alembic heads and immutable revisions, contract/model/rule versions, and sanitized dbt
lineage/quality reports. Verify the restored live catalog without blind stamping; rebuild dbt
derived generations and run shared quality tests before activating restored projections.
- Acceptance gates: Clean-target restore reproduces canonical counts/checksums and sampled queries;
a backup missing a configured WAL or tablespace root fails as incomplete rather than restoring a
partial cluster; missing/corrupt backup parts fail before mutation; recovery time/space are recorded;
original data remains untouched.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: `review-recovery-before-scale-pilots`.

#### test-failure-and-capacity-boundaries

Exercise disk pressure, database restart, worker death, corrupt artifacts, model timeout, invalid
index, and stale lease behavior before full-corpus authorization.

- Serves: `operational-recovery` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: RUN NEEDED
- Dependencies: `implement-backup-restore-and-rebuild-runbook`;
`add-progress-logging-and-resource-telemetry`; `implement-evidence-based-pipeline-forecast`;
`implement-incremental-reconciliation-and-stale-pruning`. Organizer failure injection is separate.
- Human review handoff:
[accept-recovery-and-security-posture](#accept-recovery-and-security-posture)
seal
`$RUNS_DIR/<run-id>/review/recovery/` with restore/failure evidence and residual-risk decisions.
Ready after this task and its security/restore prerequisites pass;
blocks `review-recovery-before-scale-pilots`.
Also contributes capacity/stop-condition evidence to [authorize-full-corpus-run](#authorize-full-corpus-run);
that decision remains pending pilots and the production checkpoint. Print both states.
Decision: witness restore and accept/reject the exact posture and residual risks.
- User-visible outcome: Known failures stop safely, preserve evidence, and provide a tested
resume/rebuild action instead of corrupting state.
- Scope boundary: Controlled disposable fixtures and pilot paths only; no destructive testing
against the real archive or sole backup.
- Data and artifact paths: Disposable test volumes under `$RESULTS_DIR/test/`,
`$RUNS_DIR/<run-id>/failure-tests/`, and recovery fixtures.
- Execution path: Inject bounded failures at artifact write, COPY, index
build, AGE projection, model call, and shutdown boundaries; verify alerts, state transitions,
cleanup plans, source lookup, and recovery.
- Acceptance gates: No accepted partial artifact or duplicate canonical row results; retries are
bounded; invalid indexes/projections never become active; forecast and each large-stage recheck
refuse before the configured safety margin is consumed; stale cleanup never removes protected data.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: `review-recovery-before-scale-pilots`.

#### review-recovery-before-scale-pilots

Review recovery and refusal behavior before pilot scale increases exposure and resource cost.

- Serves: `operational-recovery` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `harden-local-security-and-no-egress-mode`; `implement-backup-restore-and-rebuild-runbook`;
`test-failure-and-capacity-boundaries`; `publish-provided-archive-end-to-end-proof`;
`accept-recovery-and-security-posture`.
- User-visible outcome:
Pilot runs start with a verified restore boundary, current limits and a recorded human posture decision.
- Scope boundary:
Use completed disposable/small-proof recovery and failure evidence. This precedes scale pilots;
the later production checkpoint evaluates their measured results and cannot be replaced here.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace backup inventory versus rebuildable projections, ontology/identity/review snapshots,
source lookup, clean-target restore, power/process failure claims, no-egress and space/WAL reserves.
Verify the human acceptance names the exact evidence and residual risks; changed pins invalidate it.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
Restored facts, policy/ontology versions and historical geotemporal answers reconcile; cancellation
and low-space refusal preserve active data. Missing/stale restore evidence or human acceptance
blocks scale pilots; no full-corpus authorization follows from this checkpoint.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: none; this is the bounded checkpoint.

#### review-production-readiness-and-recovery

Review the integrated milestone before full-corpus authorization.

- Serves: `operational-recovery` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `run-representative-scale-pilots`; `test-failure-and-capacity-boundaries`;
`implement-backup-restore-and-rebuild-runbook`.
`review-recovery-before-scale-pilots`.
- Human review handoff:
[authorize-full-corpus-run](#authorize-full-corpus-run)
reviewed pilot/recovery verdict and exact decision packet.
Packet: `$RUNS_DIR/<run-id>/authorization/`.
After this checkpoint, report ready or list remaining policy decisions; never authorize automatically.
Blocked consumer:
full-corpus execution (not another implicit agent implementation task).
Report readiness using the human-handoff workflow; never self-approve.
Decision: authorize-next, resize/reconfigure, subset-only or stop for the exact pins and budget.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/proof artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace one-CUDA-host model/resource
evidence, no-egress boundaries, backup completeness, decision
retention, source lookup, restore parity, cancellation and disk/WAL/rebuild headroom;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

### Semantic retrieval -- `semantic-retrieval`

#### implement-selective-embedding-pipeline

Add policy-driven embedding tiers, provider-neutral batching, versioned artifacts, and pgvector load
without embedding the entire archive by default.

- Serves: `semantic-retrieval` --
[Search and vector projections](../design/spec.md#search-and-vector-projections)
- Agent status: RUN NEEDED
- Dependencies: `implement-stage-dag-cli-and-make-targets`;
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md);
`build-paradedb-lexical-load-and-query-path`.
- User-visible outcome: Operators can embed a bounded, explainable corpus slice and resume batches
while preserving model/profile identity.
- Scope boundary: Implement tier selection and stable pgvector baseline; do not promote a
model/index before comparison.
- Data and artifact paths: `$RESULTS_DIR/normalized/embeddings/`, `search.embedding_profile`,
`search.chunk_embedding`, `src/arxiv_int/retrieval/embedding/`, and model configs.
- Execution path: Select unique/high-value/evaluation/miss-driven chunks; batch through Ollama,
vLLM, or local encoder; validate dimensions and normalization; write Parquet then binary COPY;
create no cross-profile index.
Use PyArrow/Polars batches with contract-derived Pandera profile/dimension checks before COPY;
manage selected vector schema/index changes through reviewed Alembic operations.
- Acceptance gates: Interrupted batch resumes; input/model/config changes create new ids;
selected-tier reason is recorded; embedding output is deterministic within declared tolerance; 16
GB VRAM stays within budget.
- Documentation target: `docs/impl/current/semantic-retrieval.md`
- Review checkpoint: `review-semantic-branch-integrity`.

#### compare-pgvector-paradedb-native-and-fallback-seam

Benchmark pgvector HNSW/IVFFlat/quantized candidates and ParadeDB native vector/hybrid search on the
same selected tier; exercise the Qdrant escape-hatch interface without deploying it by default.

- Serves: `semantic-retrieval` --
[Promotion and fallback gates](../design/spec.md#promotion-and-fallback-gates)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `implement-selective-embedding-pipeline`; `create-evaluation-fixtures-and-metrics`.
- User-visible outcome: The project has a measured vector/hybrid choice or an explicit lexical-only
decision, plus a bounded fallback if Postgres cannot meet requirements.
- Scope boundary: Compare recall, filtering, fusion, lifecycle, and cost; do not add Qdrant unless
both Postgres candidates fail a declared mandatory gate.
- Data and artifact paths: `configs/retrieval/vector/`, `$RUNS_DIR/<run-id>/evaluation/vector/`,
projection manifests, and optional adapter tests.
- Execution path: Hold chunks/embeddings/queries constant; sweep index/search parameters and RRF;
record build time, WAL/temp, disk, RAM, p95 latency, recall, updates, vacuum/rebuild, and restore;
run paired answer-side check for promoted candidates.
- Acceptance gates: A predeclared adopt/retain/inconclusive rule is applied; native beta status is
visible; fallback addition requires a failed mandatory gate and its own integration plan.
- Documentation target: `docs/impl/current/semantic-retrieval.md`
- Review checkpoint: `review-semantic-branch-integrity`.

#### prove-semantic-retrieval-on-provided-archive

Run the selected semantic/hybrid branch on a bounded supplied-archive tier and publish its proof or
measured not-selected verdict.

- Serves: `semantic-retrieval` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `compare-pgvector-paradedb-native-and-fallback-seam`;
`prove-lexical-retrieval-on-provided-archive`; `implement-evidence-based-pipeline-forecast`.
- User-visible outcome: Operators can inspect actual archive embeddings, vector/hybrid results,
resource cost, and citations, or see why the branch remains disabled with lexical fallback working.
- Scope boundary: Use only the forecast-approved selected tier and configured local models; do not
embed the complete supplied archive or treat an unavailable/failed branch as successful proof.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, embedding/vector
artifacts, and
`$RESULTS_DIR/proofs/semantic-retrieval/<proof-id>/`.
- Execution path: Forecast model and index resources; run selected embedding/load/query profiles;
validate vector identities, counts, paired retrieval evidence, and fallback; rerun unchanged and
record that model inference and index build are reused.
- Acceptance gates: A usable branch has checksum-valid vectors/indexes, cited queries, measured
quality/cost verdict, and no heavy work on identical rerun. `not-selected` is valid only with the
declared measured negative result and verified lexical fallback; other failures keep the task open.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/semantic-retrieval.md`
- Review checkpoint: `review-semantic-branch-integrity`.

#### review-semantic-branch-integrity

Review the integrated milestone before promotion of the selected semantic branch.

- Serves: `semantic-retrieval` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `prove-semantic-retrieval-on-provided-archive`;
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md).
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/proof artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace vector/profile isolation,
conditional model loading, no default all-corpus embeddings,
paired relevance evidence, resource lifecycle, citation validity and lexical fallback;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/semantic-retrieval.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

### Separate archive organization -- `archive-organization`

#### implement-audited-archive-reorganization

Implement dry-run, apply, resume, rollback, and locate commands for classification-based archive
organization in both copy-to-target and in-place move modes.

- Serves: `archive-organization` --
[Separate archive organization utility](../design/spec.md#separate-archive-organization-utility)
- Agent status: CLEAR
- Dependencies: `implement-hierarchical-file-classification`;
`implement-run-ledger-and-atomic-artifacts`; `implement-backup-restore-and-rebuild-runbook`
for move recovery semantics; use disposable roots for acceptance.
`implement-evidence-and-source-location-lookup`.

- Human review handoff:
[approve-archive-organization-plan](#approve-archive-organization-plan)
dry-run plan/diff, source lookup, rollback and mode instructions.
Packet: `$RUNS_DIR/<run-id>/archive-reorganization/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`execute-authorized-archive-reorganization`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: apply, mapping-only, revise or stop for the exact plan, mode and scope.
- User-visible outcome: An authorized operator can build a classified tree of short meaningful ASCII
class directories -- copied to a target disk by default, or moved in place when that is the intent --
and still resolve every knowledge source to its initial and current path.
- Scope boundary: Default to dry-run and to `copy` mode, which reads one silo root read-only and
writes only under the declared target; `move` mode uses per-file atomic renames on one filesystem
beneath one
explicitly writable silo root per plan. Never overwrite, silently recategorize, cross silos, follow
escaping links, write into the results or database roots, or run from the ordinary read-only
pipeline/Compose path.
- Data and artifact paths: `src/arxiv_int/archive/`, `corpus.document_path_event`, additive
`src/arxiv_int/migrations/versions/`,
`$RUNS_DIR/<run-id>/archive-reorganization/{plan.json,ledger.parquet,journal/}`,
CLI and path-limit fixtures, the declared copy target, and the selected silo root only after
`--apply` in `move` mode.
- Execution path: Build ancestor directories from reversible class tokens and bounded ASCII slugs;
route safely placeable special outcomes to `_unclassified` and `_unreadable`; preflight
component/full-path limits, available hashes, links, devices, target overlap, target free space,
collisions, backup for `move`, and complete path accounting; use independent verified copies on
either same or different filesystems; exclude hardlinks;
consume sealed exports without live database/model services; generate the path-event migration;
record unplaceable entries as blocked; enforce a silo placement lease, stable duplicate-name
suffixes, filesystem identity checks, and idempotent path-ledger import; seal
the ledger before journaling renames or verified copies; expose resume and verified rollback;
reuse the shared read-only
`archive locate` resolver.
Generate the path-event change as a reviewed Alembic Python revision; use typed Polars/Arrow
ledger operations and shared Pandera checks on sealed inputs and output ledgers. The placement
executor remains independent of live dbt/database services.
- Acceptance gates: Dry-run is byte-for-byte reproducible; apply requires the exact accepted plan and
mode; fixtures prove no overwrite, byte-identical content in both modes, hash verification of every
copied file, one-to-one placed/blocked path accounting, collision and stale-hash refusal,
interruption/resume, reverse-order rollback that removes only ledger-proven and still-hash-matching
target files,
refusal to overwrite subsequent edits, journal/directory durability, offline artifact-only operation,
path-limit
compliance, unchanged source bytes after a `copy` run, and knowledge-source lookup. No production
archive is mutated by automated tests.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: `review-archive-organization-integrity`.

#### prove-archive-organization-on-provided-artifacts

Prove the organizer consumes pipeline exports independently and produces safe reviewable plans.

- Serves: `archive-organization` -- [Separate archive organization utility](../design/spec.md#separate-archive-organization-utility)
- Agent status: RUN NEEDED
- Dependencies: `implement-audited-archive-reorganization`; `prove-archive-classification-on-provided-archive`.
- Human review handoff:
[approve-archive-organization-plan](#approve-archive-organization-plan)
provide
`$RUNS_DIR/<run-id>/archive-reorganization/` plan/diff, fingerprints, source lookup and recovery drill.
After the proof, checkpoint and classification decision pass, report ready for apply/mapping-only/revise/stop.
Also prepare the exact command, target/mode/backup checks and rollback instructions for
[execute-authorized-archive-reorganization](#execute-authorized-archive-reorganization).
Execution remains blocked by the human plan decision; never interpret a draft packet as authorization.
Decision: apply, mapping-only, revise or stop for the exact plan, mode and scope.
- User-visible outcome: The operator can inspect copy and move plans and resolve source paths
without starting
model, search, or graph services.
- Scope boundary: Dry-run only on the provided archive; execute/resume/rollback solely on
disposable copies.
No acceptance of this utility is a prerequisite for the pipeline.
- Data and artifact paths: Classification/source manifests, `$RESULTS_DIR/proofs/archive-organization/<proof-id>/`,
and `$RESULTS_DIR/proof-work/archive-organization/`.
- Execution path: Validate exported fingerprints offline; generate both mode plans; test verified independent
copies, same-filesystem moves, journal recovery and idempotent ledger import on disposable roots;
edit a placed file and prove rollback refuses to remove it.
- Acceptance gates: Plans are deterministic with placed/blocked accounting, safe names and
collision handling;
no provided source changes; no model/database dependency; source hashes, lookup, and recovery
match the contract; missing backup blocks move application without blocking copy planning.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: `review-archive-organization-integrity`.

#### review-archive-organization-integrity

Review the integrated milestone before any real copy/move plan authorization.

- Serves: `archive-organization` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Audit inputs: [AUD-safe-runtime-root-boundaries-1](records/0005-runtime-refactor-safe-runtime-root-boundaries.md#audit-handoff).
- Dependencies: `prove-archive-organization-on-provided-artifacts`;
[Safe runtime root boundaries](records/0005-runtime-refactor-safe-runtime-root-boundaries.md).
- Human review handoff:
[approve-archive-organization-plan](#approve-archive-organization-plan)
provide
`$RUNS_DIR/<run-id>/archive-reorganization/` plan/diff, fingerprints, source lookup and recovery drill.
After the proof, checkpoint and classification decision pass, report ready for apply/mapping-only/revise/stop.
Also prepare the exact command, target/mode/backup checks and rollback instructions for
[execute-authorized-archive-reorganization](#execute-authorized-archive-reorganization).
Execution remains blocked by the human plan decision; never interpret a draft packet as authorization.
Decision: apply, mapping-only, revise or stop for the exact plan, mode and scope.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/proof artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace artifact-only execution,
complete classification accounting, source/destination identity,
independent copies, protected roots, durable move journal, edited-target rollback refusal and lookup;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

## Human-Assisted Tasks

### Archive classification -- `archive-classification`

#### approve-classification-policy

Review the hierarchy and confidence/exception policy without authorizing any file placement.

- Serves: `archive-classification` -- [Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: HUMAN-GATED
- Dependencies: `prove-archive-classification-on-provided-archive`.
- User-visible outcome: The owner accepts the classification operating point, vocabulary,
exceptional outcomes,
and coverage limits for use in archive browsing and future organization plans.
- Scope boundary: Approve one versioned classification policy only; this neither chooses a
destination nor
authorizes copying or moving files.
- Data and artifact paths: `configs/policy/classification.yaml`, vocabulary manifest, and
`$RUNS_DIR/<run-id>/review/classification/`.
- Execution path: Present hierarchical errors, ancestor metrics, ambiguous/exception samples, thresholds,
calibration, attribution and review effort; record accept, revise, or retain-unclassified.
- Acceptance gates: The exact vocabulary/profile/policy fingerprints and decision are recorded; low-confidence
files remain exceptional; no filesystem mutation is requested.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Identity, ontology, and graph -- `identity-ontology-graph`

#### approve-entity-merge-and-ontology-policy

Review entity-resolution operating points and ontology terms/constraints that can change graph and
report meaning.

- Serves: `identity-ontology-graph` --
[Ontology design](../design/spec.md#ontology-design)
- Agent status: HUMAN-GATED
- Dependencies: `prove-identity-ontology-graph-on-provided-archive`; held-out linkage curves from
`implement-probabilistic-entity-resolution`; ontology review package from
[Versioned ontology assets](records/0013-contract-gov-establish-versioned-ontology-assets.md).
`implement-ontology-snapshots-and-geotemporal-contracts`.
- User-visible outcome: Auto-merge thresholds and ontology semantics reflect the owner's precision
tolerance and domain meaning.
- Scope boundary: Approve bounded policies and terms; no manual editing of source mentions or
one-off hidden merges.
- Data and artifact paths: `configs/policy/identity.yaml`, versioned ontology assets, review
ledgers, and evaluation bundles.
- Execution path: Present pair/cluster errors, threshold curves, ambiguous aliases, term
definitions, domain/range, and constraint examples; record decisions as versioned configuration
and ontology commits.
Review terms against domain meaning, hidden helpers, the rule of three, additive extension, and
producer/consumer typing.
Review draft/published term differences, compatibility/deprecation mappings, geotemporal type and
uncertainty examples, source-valid versus recorded scope, and cross-version answer changes.
Acceptance publishes a new pinned interpretation; rejection leaves candidate terms unpublished.
- Acceptance gates: Auto-merge precision floor and review band are explicit; disputed terms remain
draft; every accepted change has rollback/deprecation behavior. New terms meet the rule of three
or a required specification type; helper/non-semantic objects are not published as classes.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

### Knowledge extraction -- `knowledge-extraction`

#### approve-fact-review-and-publication-policy

Choose which fact types may be auto-accepted, remain proposed, or always require review, including
how conflicts affect equipment and supplier reports.

- Serves: `knowledge-extraction` --
[Canonical object and fact model](../design/spec.md#canonical-object-and-fact-model)
- Agent status: HUMAN-GATED
- Dependencies: `prove-knowledge-extraction-on-provided-archive`; per-type final metrics from
`implement-provenance-bearing-fact-extraction` and conflict examples from
`implement-fact-validation-conflict-and-review-overlays`.
- User-visible outcome: Reports clearly distinguish evidence-backed accepted claims, uncertain
proposals, conflicts, and exclusions according to an owner-approved risk policy.
- Scope boundary: Human policy decision over measured types and thresholds; it does not alter source
evidence or waive provenance requirements.
- Data and artifact paths: `configs/policy/facts.yaml`, reviewed metric bundle, local decision
ledger, and report policy documentation.
- Execution path: Present per-type precision/recall, false-positive examples, coverage, and review
cost; record policy with version, rationale, effective scope, and rollback.
- Acceptance gates: Every high-impact type has an explicit state/threshold; conflicts and unreviewed
facts have explicit report treatment; policy version is included in query/report provenance.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

### Domain investigation artifacts -- `domain-investigation-artifacts`

#### approve-domain-artifact-semantics-and-inclusion

Review domain meanings and inclusion policies for relationship, BOM, supply-chain, invoice, and
payment artifacts before they are presented as accepted investigation results.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: HUMAN-GATED
- Dependencies: `prove-domain-investigation-artifacts-on-provided-archive`;
`approve-fact-review-and-publication-policy`; `approve-entity-merge-and-ontology-policy`.
- User-visible outcome: Operators can distinguish evidence-backed `part-of`, supplier, invoiced,
paid, partial, disputed, and unmatched states using domain-approved meanings.
- Scope boundary: Approve measured semantics, inclusion states, and display language; do not repair
source records, waive evidence requirements, or certify engineering, accounting, or legal truth.
- Data and artifact paths: `configs/policy/domain-artifacts.yaml`, reviewed examples and metric
bundles, `$RUNS_DIR/<run-id>/review/domain-artifacts/`, and local decision ledger.
- Execution path: Present false relation examples, BOM quantity/unit conflicts, ambiguous party
roles, invoice arithmetic, payment allocation candidates, coverage gaps, empty results, and graph
labels; record per-family thresholds, allowed review states, warnings, and rollback.
- Acceptance gates: Every enabled family has approved semantics and inclusion rules; weak families
remain partial, review-only, or disabled; conflicts/unresolved links stay visible; policy version is
present in each registry row and render.
Revision/effectivity and time-bounded party/location roles are explicit; domain distinctions and
non-implication examples are reviewed against the exact ontology snapshot.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Anomaly analysis -- `anomaly-analysis`

#### approve-anomaly-triage-policy

Choose measured thresholds, rank policy and review budget for source-evidenced anomaly triage.

- Serves: `anomaly-analysis` -- [Anomaly detection and triage](../design/spec.md#anomaly-detection-and-triage)
- Agent status: HUMAN-GATED
- Dependencies: `prove-anomaly-analysis-on-provided-archive`.
- User-visible outcome: The analyst sees only explicitly enabled detectors with understood
false-positive burden,
coverage limits and neutral labels.
- Scope boundary: Approve triage policy, not allegations or financial/legal conclusions; statistical
detectors may remain disabled while deterministic constraints stay available.
- Data and artifact paths: `configs/policy/anomalies.yaml`, reviewed metric bundle and
`$RUNS_DIR/<run-id>/review/anomalies/`.
- Execution path: Present hard negatives, precision at budget, missed cases, cohort sufficiency, rank
explanations and review cost; record enable, constraints-only, revise, or disable per detector.
- Acceptance gates: Each selected detector names its threshold, population, review budget
and policy version;
zero useful statistical detectors is valid; review dispositions preserve provenance.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Discovery and visualization -- `discovery-visualization`

#### accept-operator-discovery-workflows

Validate that a domain operator can complete representative topic, search, object/fact, graph,
company, product, person, equipment, supplier, BOM, supply-chain, invoice/payment and anomaly
workflows with understandable evidence
and filters.

- Serves: `discovery-visualization` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: HUMAN-GATED
- Dependencies: `build-search-graph-and-report-interfaces`;
`provision-local-dashboards-and-age-viewer` only for a selected viewer;
`prove-discovery-and-visualization-on-provided-archive`; `approve-fact-review-and-publication-policy`;
`approve-entity-merge-and-ontology-policy`; `approve-domain-artifact-semantics-and-inclusion`;
`approve-anomaly-triage-policy`.
- User-visible outcome: The available interfaces answer the actual investigation questions without
requiring knowledge of internal table layouts.
- Scope boundary: Usability and domain correctness review on bounded tasks; not a public UI
accessibility or multi-user deployment certification.
- Data and artifact paths: Local scenario script, `$RUNS_DIR/<run-id>/acceptance/`,
screenshots/redacted notes, and issue ledger.
- Execution path: Run predeclared scenarios; record task success, time, wrong/missing evidence,
confusing controls, and desired exports; route true capability gaps back to the specification.
- Acceptance gates: Required scenarios reach cited results and expose review state; blockers are
classified as bug, data gap, policy gap, or new capability; no silent workaround is accepted.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Evaluation and evidence -- `evaluation-evidence`

#### authorize-full-corpus-run

Decide whether measured pilot quality, capacity, recovery, and review cost justify running the full
archive and which optional profiles are included.

- Serves: `evaluation-evidence` -- [Required acceptance gates](../design/spec.md#required-acceptance-gates)
- Agent status: HUMAN-GATED
- Dependencies: `run-representative-scale-pilots`; `test-failure-and-capacity-boundaries`;
`accept-recovery-and-security-posture`; `accept-operator-discovery-workflows`;
`approve-classification-policy`; `approve-fact-review-and-publication-policy`;
`approve-entity-merge-and-ontology-policy`; `approve-domain-artifact-semantics-and-inclusion`;
`approve-anomaly-triage-policy`; `review-production-readiness-and-recovery`.
`review-semantic-branch-integrity` only if the semantic branch is selected.
Archive placement authorization is independent.
- User-visible outcome: The multi-terabyte run begins with an explicit disk/time/risk budget and
selected lexical/vector/graph/model profiles, or is intentionally limited.
- Scope boundary: Authorization only; it does not weaken safety margins or imply cloud/HA scope.
- Data and artifact paths: Pilot capacity report, immutable profile ids, backup location,
`$RUNS_DIR/<run-id>/authorization/decision.yaml`.
- Execution path: Review forecast ranges, free space, expected duration, classification exceptions,
unsupported bytes, domain-artifact coverage, energy/review costs, recovery time, and negative-result
alternatives; record authorize-next, resize/reconfigure, subset-only, or stop.
- Acceptance gates: Decision names exact profile/contract/code pins, paths, minimum free-space
margin, stop conditions, backup, and responsible operator; an unapproved or stale pilot cannot
launch full scope.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

### Operational recovery -- `operational-recovery`

#### accept-recovery-and-security-posture

Witness a clean-target restore and review local access, secret, network, retention, and
removable-disk procedures before treating the system as the archive's working knowledge platform.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: HUMAN-GATED
- Dependencies: `harden-local-security-and-no-egress-mode`;
`implement-backup-restore-and-rebuild-runbook`; `test-failure-and-capacity-boundaries`.
- User-visible outcome: The owner knows what is backed up, what is rebuildable, how source
locations and review decisions are
restored, how long recovery takes, and which local risks remain accepted.
- Scope boundary: Owner acceptance of the documented single-host posture; not a certification of
high availability, enterprise support, or physical security.
- Data and artifact paths: Recovery report, security checklist, backup inventory, retention policy,
and local acceptance decision.
- Execution path: Observe restore, source lookup, artifact registry, and sampled query parity;
review ports, roles, mounts, source access, secrets, model/image provenance, backup
separation, retention, and emergency stop/restart commands; record residual risks.
- Acceptance gates: Restore evidence and residual-risk list are signed off or rejected; rejected
items return to the owning capability; Community ParadeDB HA limitations remain explicit.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

### Separate archive organization -- `archive-organization`

#### approve-archive-organization-plan

Review the UDC-derived vocabulary, classification operating point, directory vocabulary, placement
mode, and one complete dry-run before any real archive reorganization.

- Serves: `archive-organization` --
[Separate archive organization utility](../design/spec.md#separate-archive-organization-utility)
- Agent status: HUMAN-GATED
- Dependencies: `prove-archive-organization-on-provided-artifacts`;
`approve-classification-policy`; verified move backup from
`implement-backup-restore-and-rebuild-runbook` only when move mode is selected.
`review-archive-organization-integrity`.
- User-visible outcome: The owner explicitly accepts which assignments may determine paths, chooses
between a copy into a target tree and an in-place move, and can `apply`, revise thresholds/slugs,
keep the mapping without placement, or stop.
- Scope boundary: Approve one versioned policy, mode, and plan; no automatic approval from
confidence, no licence waiver, and no mutation of the archive during review.
- Data and artifact paths: `configs/policy/classification.yaml`, vocabulary/licence manifest,
classification evaluation, `$RUNS_DIR/<run-id>/archive-reorganization/plan.json`, dry-run diff,
backup reference, and local decision ledger.
- Execution path: Present class and ancestor errors, `unclassified`/`unreadable` samples, coverage,
calibration, proposed ASCII paths, collisions/path lengths, placement counts/bytes, target free space
for `copy` against archive rewrite risk for `move`, source lookup, rollback drill, and UDC
attribution; record the exact accepted fingerprints, mode, and decision.
- Acceptance gates: Decision is `apply`, `mapping-only`, `revise`, or `stop`; `apply` names the exact
classification and plan ids, mode, silo root and device, copy target or verified backup, stop
conditions, and responsible operator; stale or unapproved plans remain non-writable.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: `review-archive-organization-integrity`.

#### execute-authorized-archive-reorganization

Execute one authorized placement plan -- a copy into the target tree or an in-place move -- and prove
that every knowledge source still resolves afterwards.

- Serves: `archive-organization` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: HUMAN-GATED
- Dependencies: `approve-archive-organization-plan` for the recorded `apply` decision
and mode; `prove-archive-organization-on-provided-artifacts`;
`implement-backup-restore-and-rebuild-runbook` for the verified backup a `move` decision requires.
- User-visible outcome: The authorized silo is organized by its primary class hierarchy -- in a target
tree or in place -- and every document, fact, and report still resolves from its original path to its
current path.
- Scope boundary: Run only the exact accepted classification id, plan id, and mode, on the one silo
the decision names, into the target it names; never re-plan, widen scope, place blocked entries,
switch modes, or touch a silo the decision does not name. A `move` decision additionally requires its
verified backup. A `mapping-only`, `revise`, or `stop` decision closes this task with that recorded
result and no placement.
- Data and artifact paths: The declared copy target or the authorized writable silo root,
`$RUNS_DIR/<run-id>/archive-reorganization/{plan.json,ledger.parquet,journal/}`,
`corpus.document_path_event`, and the post-placement verification report.
- Execution path: Revalidate the plan fingerprint, mode, source paths, hashes, destinations, device,
and free space; confirm the backup reference for `move`; seal the ledger; apply journaled renames or
hash-verified copies; reconcile placed, blocked, and skipped counts against the plan; re-resolve a
sampled set of documents, facts, search citations, and registered artifacts through `archive locate`;
record timing, failures, and the rollback command that remains available.
- Acceptance gates: Placed and blocked entries account for the plan exactly with no overwrite and no
byte change; a `copy` run leaves every source byte and path intact; path events record initial and
current locations for every placed file; sampled knowledge sources resolve afterwards; an
interruption resumes or reverses only from the sealed ledger; a failed precondition refuses before
the first rename or copy.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: `review-archive-organization-integrity`.
