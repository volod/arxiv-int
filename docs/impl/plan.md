# arxiv-int Implementation Plan

Forward-only: this file contains only work that remains. Product behavior, boundaries, evaluation,
and delivery strategy belong in [the specification](../design/spec.md). Task structure, statuses,
ordering, and lifecycle rules belong in the
[planning workflow](../guide/planning-workflow.md). Available behavior and durable results belong in
[current-state documentation](current.md).

## Agent Implementation Tasks

### Contract governance -- `contract-governance`

#### establish-canonical-contract-registry

Define ODCS contracts, a canonical semantic model, dataset registry, and physical-to-canonical
mappings for the first pipeline entities.

- Serves: `contract-governance` --
[Contract-first data governance](../design/spec.md#contract-first-data-governance)
- Agent status: CLEAR
- Dependencies: The contract primitives and package/CLI identity documented in
[Project foundation](current/project-foundation.md#contract-primitives).
- User-visible outcome: Documents, spans, chunks, objects, mentions, facts, topics, ontology terms,
embeddings, and evaluation items have one reviewable schema source of truth.
- Scope boundary: Define contracts and semantic bindings; do not create live database tables or
infer domain-specific ontology terms from the corpus.
- Data and artifact paths: `contracts/registry.yaml`, `contracts/canonical/`, `contracts/datasets/`,
`contracts/mappings/`, and `src/arxiv_int/contracts/`.
- Execution path: Extend the existing registry and canonical-model interfaces with project-specific
ODCS 3.1 adapters; namespace project hints under `x-arxiv-int`; add Data Contract CLI validation and
Pydantic loaders that preserve unknown metadata.
- Acceptance gates: Official ODCS JSON Schema and Data Contract CLI lint pass; ids, versions,
references, canonical bindings, relationship targets, and required identities are unique and
complete.
- Documentation target: `docs/impl/current/contracts.md`

#### implement-deterministic-schema-generation

Generate physical schemas and model boundaries from ODCS while minimizing custom generator code.

- Serves: `contract-governance` -- [Generation](../design/spec.md#generation)
- Agent status: CLEAR
- Dependencies: `establish-canonical-contract-registry`.
- User-visible outcome: One contract change reproducibly updates Avro, Arrow/Parquet, PostgreSQL
baseline, search, graph, and structured-output schemas.
- Scope boundary: Generate baseline artifacts and extension DDL; do not apply migrations to an
existing database.
- Data and artifact paths: `contracts/generated/{avro,parquet,postgres,jsonschema,graph}/`,
`src/arxiv_int/contracts/generate/`, and `tests/contracts/golden/`.
- Execution path: Use Data Contract CLI exporters first; add focused adapters for partitions,
ParadeDB tokenizers/indexes, vector dimensions, AGE projections, provenance metadata, and
Pydantic/JSON Schema; normalize ordering and fingerprints.
- Acceptance gates: Generation is byte-stable; `make contracts-gen` and drift check pass; Avro
parses and round-trips; generated SQL parses against a disposable database; no source contract
metadata is silently lost.
- Documentation target: `docs/impl/current/contracts.md`

#### enforce-evolution-and-migration-policy

Add reviewed schema/semantic baselines, compatibility classification, ordered SQL migrations, and
live-store conformance checks.

- Serves: `contract-governance` -- [Evolution and migrations](../design/spec.md#evolution-and-migrations)
- Agent status: CLEAR
- Dependencies: `implement-deterministic-schema-generation`.
- User-visible outcome: Breaking, reindexing, and graph-rebuild consequences are reported before a
schema change can reach data.
- Scope boundary: Detect, classify, and prepare migrations; never auto-approve destructive or
table-rewriting changes.
- Data and artifact paths: `contracts/evolution/`, `db/migrations/`, `db/schema.sql`,
`src/arxiv_int/contracts/evolution.py`, and `tests/contracts/evolution/`.
- Execution path: Extend the existing adjacent-history and semantic-fingerprint primitives; invoke
Avro reader/writer compatibility and Data Contract CLI breaking checks; integrate dbmate; compare
generated baseline, migration dump, and live information schema.
- Acceptance gates: Fixtures prove identical, additive, breaking, tokenizer/reindex,
vector-dimension, semantic-retarget, and graph-projection cases; version rules fail closed;
out-of-order migrations and drift fail CI.
- Documentation target: `docs/impl/current/contracts.md`

### Canonical store -- `canonical-store`

#### build-pinned-paradedb-age-image

Build and verify a project-owned image containing one PostgreSQL major, ParadeDB/`pg_search`,
pgvector, and Apache AGE.

- Serves: `canonical-store` -- [Architecture decision](../design/spec.md#architecture-decision)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: Compose profiles and operator wrappers documented in
[Portable runtime](current/portable-runtime.md).
- User-visible outcome: The core database starts from a reproducible image and reports exact
extension/build identities; graph mode is enabled only when its compatibility suite passes.
- Scope boundary: Test extension coexistence, licensing, initialization, upgrade seam, and basic
operations; do not claim production multi-TB scale.
- Data and artifact paths: `docker/postgres/Dockerfile`, `docker/postgres/initdb/`,
`docker/postgres/NOTICE`, `tests/integration/extensions/`, and `$PGDATA_DIR` for the declared
disposable run.
- Execution path: Derive from a pinned ParadeDB Community digest; install a pinned AGE release for
the same PostgreSQL major; merge preload requirements; create `vector`, `pg_search`, and `age` in
order; run SQL, BM25, vector, Cypher, dump/restore, restart, and transaction probes.
- Acceptance gates: Image builds from a clean cache; extension versions match pins; combined probes
pass across restart and dump/restore; licenses are present. A valid negative result disables the
AGE profile and records the incompatibility without blocking relational graph work.
- Documentation target: `docs/impl/current/canonical-store.md`

#### create-canonical-relational-schema

Apply generated migrations for control, corpus, search, knowledge, ontology, and evaluation schemas
with partition and provenance constraints.

- Serves: `canonical-store` -- [PostgreSQL schemas](../design/spec.md#postgresql-schemas)
- Agent status: CLEAR
- Dependencies: `build-pinned-paradedb-age-image` can yield either AGE-enabled or AGE-disabled;
`enforce-evolution-and-migration-policy`.
- User-visible outcome: Canonical documents, assertions, reviews, and run state have constrained,
queryable tables independent of search and graph projections.
- Scope boundary: Create schema, roles, partitions, staging/load functions, and indexes required for
correctness; corpus-scale tuning belongs to evaluation.
- Data and artifact paths: `db/migrations/`, `db/schema.sql`, `src/arxiv_int/stores/postgres/`, and
`tests/integration/postgres/`.
- Execution path: Generate/apply migrations; define typed literal fact constraints,
bitemporal/provenance columns, stable hash partitioning, role grants, staging tables, and
idempotent upserts; add SQLAlchemy/psycopg typed adapters only where useful.
- Acceptance gates: Contract-to-live conformance passes; constraint and rollback fixtures reject
invalid fact shapes, missing provenance, duplicates, and cross-version vector mixing; migration
and clean-load schemas match.
- Documentation target: `docs/impl/current/canonical-store.md`

#### implement-rebuildable-search-and-graph-projections

Create projection lifecycle code for ParadeDB, pgvector candidates, and AGE without making any
projection canonical.

- Serves: `canonical-store` --
[Search and vector projections](../design/spec.md#search-and-vector-projections)
- Agent status: CLEAR
- Dependencies: `create-canonical-relational-schema`.
- User-visible outcome: Search/vector/graph projections can be built, validated, version-switched,
and dropped without losing canonical rows.
- Scope boundary: Implement lifecycle and correctness checks on fixtures; relevance and scale
promotion belong to later capabilities.
- Data and artifact paths: `src/arxiv_int/stores/projections/`, `db/migrations/`,
`tests/integration/projections/`, and `$RUNS_DIR/<run-id>/manifests/`.
- Execution path: Add versioned projection metadata, staging builds, row/count/checksum
reconciliation, sampled SQL/Cypher parity, active-pointer switch, and cleanup planning; preserve
full evidence relationally.
- Acceptance gates: Rebuild from normalized/canonical fixtures yields identical logical ids; failed
builds never replace active projections; graph-disabled mode supports recursive SQL and open
exports.
- Documentation target: `docs/impl/current/canonical-store.md`

### Local inference -- `local-inference`

#### implement-local-inference-adapters

Create a provider-neutral local client for Ollama and vLLM covering chat, structured output,
embeddings, health, model identity, timeout, and cancellation.

- Serves: `local-inference` -- [Local inference](../design/spec.md#local-inference)
- Agent status: CLEAR
- Dependencies: Feature groups and domain interfaces described in
[Project foundation](current/project-foundation.md#feature-groups); runtime roots documented in
[Portable runtime](current/portable-runtime.md).
- User-visible outcome: The same extraction/retrieval code can use the Ollama system service or an
optional vLLM container through explicit configuration.
- Scope boundary: Local endpoints only; no hosted fallback, implicit model pull, or systemd
mutation.
- Data and artifact paths: `src/arxiv_int/inference/`, `configs/models/`, generated
structured-output schemas, and `tests/inference/`.
- Execution path: Implement local API adapters, capability discovery, schema response validation,
bounded repair, streaming/cancel, retries, model digest capture, and fake servers for
deterministic tests.
- Acceptance gates: Provider conformance tests agree on typed results/statuses; unreachable and
incompatible models fail clearly; prompts and secrets are not logged; no remote hostname passes
local-only policy by default.
- Documentation target: `docs/impl/current/local-inference.md`

#### implement-model-resource-scheduler

Schedule GPU-heavy embedding, reranking, OCR, and generation sequentially by default and record
resource evidence.

- Serves: `local-inference` --
[Performance and scalability assumptions](../design/spec.md#performance-and-scalability-assumptions)
- Agent status: RUN NEEDED
- Dependencies: `implement-local-inference-adapters`.
- User-visible outcome: The 16 GB GPU does not thrash between models, and operators see why a model
ran, offloaded, skipped, or fell back.
- Scope boundary: Single-host resource coordination; no cluster scheduler and no unapproved service
stop.
- Data and artifact paths: `src/arxiv_int/inference/scheduler.py`, `ctl.resource_lease`, model
profiles, and `$RUNS_DIR/<run-id>/telemetry/`.
- Execution path: Detect GPU/RAM, estimate declared footprints, acquire one GPU lease, manage Ollama
keep-alive/unload through API when allowed, start/stop vLLM profile when requested, and record
load/throughput/VRAM/power through a narrow telemetry sink that later pipeline logging also
consumes.
- Acceptance gates: Simulated contention and real 16 GB smoke never overlap incompatible workloads;
cancellation releases leases; model-fit rejection is actionable; CPU fallback is explicit.
- Documentation target: `docs/impl/current/local-inference.md`

### Evaluation foundation -- `evaluation-foundation`

#### create-evaluation-fixtures-and-metrics

Build immutable extraction, classification, Russian retrieval, semantic, entity, fact, ontology,
graph, domain-artifact, and reporting fixtures plus paired evaluation utilities.

- Serves: `evaluation-foundation` -- [Evaluation and acceptance](../design/spec.md#evaluation-and-acceptance)
- Agent status: CLEAR
- Dependencies: `establish-canonical-contract-registry`; the evaluation and retrieval primitives
documented in [Project foundation](current/project-foundation.md#evaluation-and-retrieval-primitives).
- User-visible outcome: Every store/model/pipeline recommendation names the exact frozen items,
metrics, thresholds, and run artifacts that support it, and every usable stage can publish the same
proof-bundle shape.
- Scope boundary: Provide deterministic fixtures and measurement; human gold review remains in the
human lane.
- Data and artifact paths: `tests/fixtures/`, `eval.*`, `src/arxiv_int/evaluation/`,
`configs/evaluation/`, `configs/proofs/`, `Makefile`, `$RUNS_DIR/<run-id>/evaluation/`, and
`$RUNS_DIR/proofs/`.
- Execution path: Extend the existing metrics for recall@k, MRR, evidence intactness, p95, paired
bootstrap, extraction/span, hierarchical classification, linkage, domain artifact, graph parity,
resource cost, and adopt/retain/inconclusive verdicts; register the
`evaluate` stage body that writes the immutable evaluation bundle; add a typed proof manifest,
stage-to-validator registry, redaction, fingerprint freshness, proof summary helpers, and a shared
`make proof CAPABILITY=...` dispatcher.
- Acceptance gates: Split leakage and provenance checks pass; bootstrap seeds and item ledgers
replay; missing evidence refuses a verdict; metrics have positive/negative fixtures; proof bundles
reject stale fingerprints, missing artifact checksums, unvalidated usable stages, and private paths
or corpus content in repository summaries; proof target discovery and unknown capability tests pass.
- Documentation target: `docs/impl/current/evaluation-foundation.md`

### Corpus foundation -- `corpus-foundation`

#### implement-streaming-inventory

Build a content-addressed, restartable archive inventory with format, encoding, hash, and quarantine
metadata.

- Serves: `corpus-foundation` -- [Pipeline](../design/spec.md#pipeline)
- Agent status: RUN NEEDED
- Dependencies: Runtime roots documented in [Portable runtime](current/portable-runtime.md);
`establish-canonical-contract-registry`.
- User-visible outcome: The operator can inventory one or more multi-terabyte silos without loading
them into RAM and can see per-silo coverage, bytes, duplicates, and unsupported/encrypted inputs.
- Scope boundary: Read files and archive-member metadata only; no text extraction and no
modification of source files.
- Data and artifact paths: Declared source roots from `$ARCHIVE_DIR`, used without modification;
`$RESULTS_DIR/normalized/inventory/`; `$RUNS_DIR/<run-id>/`; `src/arxiv_int/pipeline/inventory/`.
- Execution path: Resolve the declared silo ids and roots; stream directory entries, carry silo id
with root-relative path metadata, detect MIME/encoding, compute configurable quick and strong hashes
once, enforce archive-bomb limits, shard by stable id, and write atomic Parquet manifests; register
the stage and expose `arxiv-int stage inventory` plus `make stage STAGE=inventory` in the same change,
then run that normal command against the configured archive and inspect its artifacts.
- Acceptance gates: Network-free fixtures cover large/sparse files, links, permission errors,
renamed duplicates, nested archives, encrypted files, interruption, and resume; two silos sharing one
root-relative path stay distinct while identical bytes resolve to one content identity; memory is
bounded independently of file count; the configured-archive run and artifact summary are recorded in
current-state documentation without private content or machine-specific paths.
- Documentation target: `docs/impl/current/corpus-foundation.md`

#### integrate-tiered-text-extraction

Compose Tika, Docling, and OCR/layout fallbacks behind one evidence-preserving extractor interface.

- Serves: `corpus-foundation` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Dependencies: `implement-streaming-inventory`; `implement-deterministic-schema-generation`.
- User-visible outcome: Supported documents become normalized source spans with page/table/offset
evidence; failures are quarantined with actionable reasons.
- Scope boundary: Integrate existing engines and selection policy; do not build a new parser or
promise every proprietary format.
- Data and artifact paths: `$RESULTS_DIR/normalized/documents/`, `$RESULTS_DIR/normalized/spans/`,
`$RESULTS_DIR/quarantine/`, `src/arxiv_int/extraction/`, and representative format fixtures.
- Execution path: Run Tika as breadth baseline; route layout/table PDFs to Docling and scanned PDFs
to OCR; preserve tool versions, coordinates, raw hashes, and extraction quality; bound temp files,
child processes, timeouts, and decompression; register `extract` with the normal stage interface and
run it immediately against the configured archive after deterministic checks pass.
- Acceptance gates: The reviewed extraction fixture reports per-format text, table, and anchor
coverage; corrupt/encrypted/oversized inputs fail safely; repeated content hashes reuse outputs;
source files remain unchanged; the normal `make stage STAGE=extract` run produces inspectable
artifacts on the configured archive, and its redacted result is recorded in current-state
documentation.
- Documentation target: `docs/impl/current/corpus-foundation.md`

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
register the normal stage commands and run them immediately against the configured archive.
- Acceptance gates: Golden offsets and table headers survive chunking; unchanged input yields stable
ids; dedupe precision is measured on labels; no suppression occurs without an overlay; out-of-core
memory and shard-resume tests pass; the configured-archive commands produce inspectable artifacts
whose redacted results are recorded in current-state documentation.
- Documentation target: `docs/impl/current/corpus-foundation.md`

#### prove-corpus-foundation-on-provided-archive

Run the completed corpus stages against the operator-provided archive and publish their first
current proof bundle.

- Serves: `corpus-foundation` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-normalization-dedupe-and-chunking`;
`implement-stage-dag-cli-and-make-targets`; `implement-evidence-based-pipeline-forecast`;
`create-evaluation-fixtures-and-metrics`; `approve-representative-corpus-and-gold`.
- User-visible outcome: The supplied file silos have inspectable inventory, extraction,
normalization, duplicate, and chunk artifacts backed by one reproducible proof id.
- Scope boundary: Read `PROOF_ARCHIVE_DIR` without mutation and stop after `chunk`; do not infer
downstream classification, retrieval, or knowledge quality from this proof.
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification, `$RESULTS_DIR`, and
`$RUNS_DIR/proofs/corpus-foundation/<proof-id>/`; only redacted summaries enter current docs.
- Execution path: Run a passing forecast; execute `inventory` through `chunk`; validate contracts,
counts, spans, offsets, quarantine reasons, and checksums; rerun the identical closure and capture
cache decisions plus resource/timing evidence.
- Acceptance gates: Every usable corpus stage is `passed` or contract-valid `empty`; every inventory
item is accounted for; artifacts and source anchors validate; the unchanged rerun executes no heavy
extraction/normalization work; failures keep the task open.
- Documentation target: `docs/impl/current/corpus-foundation.md`

### Pipeline control -- `pipeline-control`

#### implement-run-ledger-and-atomic-artifacts

Create run, stage, shard, lease, checkpoint, error, artifact-manifest, and transitive-lineage state
with deterministic reuse keys.

- Serves: `pipeline-control` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: `create-canonical-relational-schema`; `implement-streaming-inventory`.
- User-visible outcome: Every long operation has inspectable state; an interrupted shard resumes,
and an unchanged shard reuses validated output without loading its heavy implementation.
- Scope boundary: Implement generic control mechanics; stage-specific processing stays in its owning
capability.
- Data and artifact paths: `ctl.*` tables, `$RUNS_DIR/<run-id>/manifests/`,
`src/arxiv_int/pipeline/control/`, and `tests/pipeline/control/`.
- Execution path: Define stage-owned code/dependency/input fingerprints, transitive artifact edges,
cache validation, concurrent reuse leases, state transitions, atomic sibling writes, bounded retry
taxonomy, stale-lease recovery, and downstream invalidation planning.
- Acceptance gates: Property/state-machine tests reject illegal transitions; crash injection proves
no partial output is accepted; unchanged rerun validates manifests and does not invoke the heavy
worker; a changed owned fingerprint marks exactly the reachable closure stale; forced retry creates
a new attempt without overwriting evidence.
- Documentation target: `docs/impl/current/pipeline-control.md`

#### implement-stage-dag-cli-and-make-targets

Complete the dependency-aware stage registry, independent stage command, end-to-end and incremental
runners, resume, status, invalidate, rebuild, and stale-prune planning interfaces.

- Serves: `pipeline-control` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: `implement-run-ledger-and-atomic-artifacts`;
`implement-normalization-dedupe-and-chunking`.
- User-visible outcome: Operators can run or update one stage or a `--from`/`--to` dependency
closure, inspect invalidation, start a fresh generation, and resume by run id through CLI or Make.
- Scope boundary: Orchestrate in-process/local workers first; do not introduce Airflow, Prefect,
Celery, Redis, or Kubernetes.
- Data and artifact paths: `src/arxiv_int/cli.py`, `src/arxiv_int/pipeline/registry.py`, `Makefile`,
and `tests/pipeline/orchestration/`.
- Execution path: Extend the typed stage registry introduced with inventory; register dependencies;
resolve parameters; validate required
upstream manifests; add run/update/stage/status/resume/invalidate/rebuild and prune-plan commands;
keep Make wrappers thin and destructive application separately confirmed.
- Acceptance gates: DAG, range, skip, invalid dependency, update, resume, targeted invalidate,
fresh-generation rebuild, prune dry-run, force, and signal-handling tests pass; CLI help lists
defaults and precedence; end-to-end smoke produces the same manifests as independent stages.
- Documentation target: `docs/impl/current/pipeline-control.md`

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
- Acceptance gates: Normal empty, partial, quarantined, and schema-drifted run artifacts produce
stable summaries; inspection leaves checksums unchanged; summaries contain no secrets, unbounded
corpus text, development alias, or machine-specific path.
- Documentation target: `docs/impl/current/pipeline-control.md`

#### implement-incremental-reconciliation-and-stale-pruning

Reconcile archive and implementation deltas through artifact lineage, retract stale active data,
and provide safe partial update, full rebuild, and physical-prune paths.

- Serves: `pipeline-control` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: `implement-run-ledger-and-atomic-artifacts`;
`implement-stage-dag-cli-and-make-targets`; `implement-rebuildable-search-and-graph-projections`.
- User-visible outcome: Added, changed, renamed, or removed files and later analysis-code changes
update only affected descendants, while operators can deliberately rebuild everything or reclaim
obsolete derived storage.
- Scope boundary: Reconcile derived/canonical active views and prune only unreferenced stale data;
never delete archive sources, move ledgers, immutable review history, active generations, or the sole
recovery copy.
- Data and artifact paths: `ctl.artifact_lineage`, source delta/tombstone and prune-event contracts,
`src/arxiv_int/pipeline/reconcile/`, `src/arxiv_int/pipeline/prune/`, additive `db/migrations/`, and
`$RUNS_DIR/<run-id>/{delta,invalidation,rebuild,prune}/`.
- Execution path: Diff source manifests into add/content-change/path-rename/remove; compute the
minimal downstream closure; retract stale rows/edges from active views after replacements validate;
retain shared evidence; create isolated rebuild generations and atomic activation; make prune
two-phase with dry-run ids, reference/pin/backup checks, and compact retained lineage.
- Acceptance gates: Deterministic fixtures prove no-op updates invoke no heavy workers; additions
touch only new shards; path-only renames avoid content analysis; changes/removals retract exactly
dependent active outputs; stage fingerprint changes invalidate only owned descendants; rebuild
matches a clean baseline; prune refuses active, pinned, reviewed, rollback, or sole-backup data.
- Documentation target: `docs/impl/current/pipeline-control.md`

#### add-progress-logging-and-resource-telemetry

Provide serialized human logs, structured logs, periodic database progress, and bounded resource
metrics for every stage.

- Serves: `pipeline-control` --
[Logging, progress, and observability](../design/spec.md#logging-progress-and-observability)
- Agent status: CLEAR
- Dependencies: `implement-stage-dag-cli-and-make-targets`.
- User-visible outcome: Long runs continuously report processed/remaining items, bytes, throughput,
ETA, errors, and resource pressure without garbled concurrent output.
- Scope boundary: Record operational metadata; do not place document content, prompts, secrets, or
unbounded ids in logs/metric labels.
- Data and artifact paths: `src/arxiv_int/observability/`, `$RUNS_DIR/<run-id>/logs/`,
`ctl.stage_run`, Grafana provisioning, and logging tests.
- Execution path: Extend the existing logging and timing interfaces with time/count-throttled
progress, heartbeats, psutil/NVML/disk/Postgres metrics, redaction filters, JSONL schema, and final
manifests.
- Acceptance gates: Concurrent-log tests produce intact lines; redaction fixtures remove secrets and
corpus text; stalled worker and ETA states are distinguishable; metric labels have bounded
cardinality.
- Documentation target: `docs/impl/current/pipeline-control.md`

#### implement-evidence-based-pipeline-forecast

Implement a read-only command that predicts requested work, duration, output/peak storage, and
free-space safety before a pipeline run.

- Serves: `pipeline-control` --
[Pre-run forecast and resource refusal](../design/spec.md#pre-run-forecast-and-resource-refusal)
- Agent status: CLEAR
- Dependencies: `implement-incremental-reconciliation-and-stale-pruning`;
`add-progress-logging-and-resource-telemetry`; `implement-streaming-inventory`; runtime storage
evidence documented in [Portable runtime](current/portable-runtime.md).
- User-visible outcome: Before starting, an operator sees stage-by-stage cache hits, changed work,
time and data-size ranges, peak scratch/rebuild needs, accessible disk free space, confidence, and a
clear ready/degraded/blocked decision.
- Scope boundary: Perform inventory, sampling, manifest, telemetry, and filesystem checks only; do
not load heavy models, materialize production artifacts, invent precise estimates, or bypass hard
space reserves.
- Data and artifact paths: `src/arxiv_int/pipeline/forecast/`, `configs/capacity/`, forecast JSON
Schema/contracts, prior run manifests/telemetry, and `$RUNS_DIR/<forecast-id>/forecast/`.
- Execution path: Resolve cache and delta plans; select comparable runs and bounded format samples;
estimate lower/upper output, time, WAL, temp, staging, rebuild, rollback, backup, and
archive-reorganization target costs; deduplicate filesystem devices across the archive, results, and
database roots; read accessible free bytes; emit evidence/coefficient provenance and a fingerprinted
console/JSON decision; add stage-boundary free-space rechecks.
- Acceptance gates: Zero-history fixtures yield conservative low-confidence ranges; estimates replay
from captured evidence; shared devices are counted once; inaccessible paths and upper-bound peak plus
reserve shortfalls exit non-zero before heavy work; stale forecasts are rejected; simulated free-space
loss checkpoints before allocation without accepting partial output.
- Documentation target: `docs/impl/current/pipeline-control.md`

#### prove-pipeline-control-on-provided-archive

Exercise idempotency, incremental reconciliation, invalidation, forecasting, rebuild, and prune
planning with the supplied archive and publish the pipeline-control proof bundle.

- Serves: `pipeline-control` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-evidence-based-pipeline-forecast`;
`prove-corpus-foundation-on-provided-archive`; `create-evaluation-fixtures-and-metrics`.
- User-visible outcome: The supplied archive demonstrates that unchanged inputs skip heavy work,
deltas update only affected artifacts, stale data retracts safely, insufficient space blocks early,
and a clean generation can be rebuilt.
- Scope boundary: Do not modify `PROOF_ARCHIVE_DIR`; perform add/change/rename/remove and prune-apply
drills only on a bounded disposable proof copy; do not prune the sole proof or recovery generation.
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification, disposable
`$RESULTS_DIR/proof-work/pipeline-control/<proof-id>/`, and
`$RUNS_DIR/proofs/pipeline-control/<proof-id>/`.
- Execution path: Forecast and run the corpus closure; rerun unchanged; create controlled source
deltas and a stage-fingerprint bump; inspect minimal closures and active retractions; simulate low
space; rebuild into a fresh generation; compare checksums; dry-run pruning and apply it only to an
extra disposable stale generation.
- Acceptance gates: Proof records zero heavy invocations on the no-op rerun, exact affected/unaffected
shards for each delta, correct tombstones and active rows, targeted code invalidation, non-zero
resource refusal before allocation, clean-rebuild parity, protected-data prune refusal, and no write
to the supplied archive.
- Documentation target: `docs/impl/current/pipeline-control.md`

### Archive classification -- `archive-classification`

#### establish-versioned-udc-derived-scheme

Establish the authorized UDC-derived hierarchy, project extension namespace, special outcomes, and
evaluation labels used to classify archive files.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `establish-canonical-contract-registry`;
`create-evaluation-fixtures-and-metrics`.
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

#### implement-hierarchical-file-classification

Add a restartable stage that maps every inventoried physical file to primary and alternate
UDC-derived classes or one explicit exceptional outcome.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `establish-versioned-udc-derived-scheme`;
`implement-normalization-dedupe-and-chunking`; `implement-stage-dag-cli-and-make-targets`;
`approve-representative-corpus-and-gold`.
- User-visible outcome: Each source file has a searchable, evidence-backed hierarchical assignment,
while random text and extraction failures remain visibly `unclassified` or `unreadable`.
- Scope boundary: Produce mappings and review candidates only; do not move source files, classify
virtual archive members as independently movable files, or force low-confidence assignments.
- Data and artifact paths: `$RESULTS_DIR/normalized/classifications/`, `corpus.file_classification`,
additive `db/migrations/`, `src/arxiv_int/classification/`, classifier profiles, and
`$RUNS_DIR/<run-id>/evaluation/classification/`.
- Execution path: Combine metadata and normalized-text rules with a measured lightweight classifier;
allow bounded local-model assistance only when it improves held-out results; retain multi-label
scores, one primary ancestor path, decisive evidence, failure taxonomy, and complete fingerprints;
generate and apply the classification contract migration.
- Acceptance gates: Every inventory file appears exactly once; unreadability follows extraction
evidence; exact and ancestor-aware precision/recall, hierarchical distance, calibration, selective
coverage, exceptional-outcome confusion, reproducibility, throughput, and memory meet predeclared
gates. A high `unclassified` or `unreadable` rate is a valid reported result.
- Documentation target: `docs/impl/current/archive-classification.md`

#### implement-audited-archive-reorganization

Implement dry-run, apply, resume, rollback, and locate commands for classification-based archive
organization in both copy-to-target and in-place move modes.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: CLEAR
- Dependencies: `implement-hierarchical-file-classification`;
`implement-run-ledger-and-atomic-artifacts`.
- User-visible outcome: An authorized operator can build a classified tree of short meaningful ASCII
class directories -- copied to a target disk by default, or moved in place when that is the intent --
and still resolve every knowledge source to its initial and current path.
- Scope boundary: Default to dry-run and to `copy` mode, which reads one silo root read-only and
writes only under the declared target; `move` mode stays same-filesystem and atomic beneath one
explicitly writable silo root per plan. Never overwrite, silently recategorize, cross silos, follow
escaping links, write into the results or database roots, or run from the ordinary read-only
pipeline/Compose path.
- Data and artifact paths: `src/arxiv_int/archive/`, `corpus.document_path_event`, additive
`db/migrations/`, `$RUNS_DIR/<run-id>/archive-reorganization/{plan.json,ledger.parquet,journal/}`,
CLI and path-limit fixtures, the declared copy target, and the selected silo root only after
`--apply` in `move` mode.
- Execution path: Build ancestor directories from reversible class tokens and bounded ASCII slugs;
route safely placeable special outcomes to `_unclassified` and `_unreadable`; preflight
component/full-path limits, available hashes, links, devices, target overlap, target free space,
collisions, backup for `move`, and complete path accounting; add opt-in same-filesystem hardlink
placement for `copy`; generate the path-event migration; record unplaceable entries as blocked; seal
the ledger before journaling renames or verified copies; expose resume, verified rollback, and
`archive locate`.
- Acceptance gates: Dry-run is byte-for-byte reproducible; apply requires the exact accepted plan and
mode; fixtures prove no overwrite, byte-identical content in both modes, hash verification of every
copied file, one-to-one placed/blocked path accounting, collision and stale-hash refusal,
interruption/resume, reverse-order rollback that removes only ledger-proven target files, path-limit
compliance, unchanged source bytes after a `copy` run, and knowledge-source lookup. No production
archive is mutated by automated tests.
- Documentation target: `docs/impl/current/archive-classification.md`

#### prove-archive-classification-on-provided-archive

Classify the supplied archive, validate the complete mapping, and publish a non-mutating
reorganization proof bundle.

- Serves: `archive-classification` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-audited-archive-reorganization`;
`prove-pipeline-control-on-provided-archive`.
- User-visible outcome: Every supplied file has a UDC-derived or explicit exceptional result, and
the operator can inspect deterministic ASCII destinations, per-mode space requirements, and
initial/current source lookup before authorizing any placement.
- Scope boundary: Run classification, mapping validation, reorganize dry-run for both modes, and
locate only; never apply a placement to `PROOF_ARCHIVE_DIR`.
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/classifications/`, and
`$RUNS_DIR/proofs/archive-classification/<proof-id>/`.
- Execution path: Forecast the closure; run classification; validate coverage, hierarchy, evidence,
exceptions, and fingerprints; generate the move plan; check path/collision/device rules and lookup;
rerun unchanged and record classifier/model cache hits.
- Acceptance gates: Inventory-to-classification accounting is exact; every ordinary assignment or
exception validates; the plan covers placed/blocked entries with no unsafe destination and reports
target space for `copy` and backup readiness for `move`; supplied files remain unchanged; the
identical rerun invokes no heavy classifier; proof artifacts and checksums are complete.
- Documentation target: `docs/impl/current/archive-classification.md`

#### execute-authorized-archive-reorganization

Execute one authorized placement plan -- a copy into the target tree or an in-place move -- and prove
that every knowledge source still resolves afterwards.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: RUN NEEDED
- Dependencies: `approve-classification-and-reorganization-policy` for the recorded `apply` decision
and mode; `prove-archive-classification-on-provided-archive`;
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
- Documentation target: `docs/impl/current/archive-classification.md`

### Lexical retrieval -- `lexical-retrieval`

#### build-paradedb-lexical-load-and-query-path

Bulk-load selected document/chunk projection rows and implement lexical search, filters, snippets,
facets, and identifier lookup.

- Serves: `lexical-retrieval` --
[Search and vector projections](../design/spec.md#search-and-vector-projections)
- Agent status: RUN NEEDED
- Dependencies: `implement-rebuildable-search-and-graph-projections`;
`implement-stage-dag-cli-and-make-targets`.
- User-visible outcome: The full normalized corpus or chosen partition is searchable with
evidence-bearing results and stable filter behavior.
- Scope boundary: Establish the lexical path and lifecycle; semantic fusion is separate.
- Data and artifact paths: `search.*` tables/indexes, `src/arxiv_int/retrieval/lexical.py`,
`$RUNS_DIR/<run-id>/search/`, and retrieval fixtures.
- Execution path: Binary-COPY staging rows; create one covering ParadeDB index per partition/table
design; index Russian text plus literal ids and required filter fields; expose typed query and
explain/diagnostic modes.
- Acceptance gates: Load counts/checksums reconcile; result citations resolve to source spans;
concurrent index build/rebuild remains observable; query and index failures have actionable
diagnostics.
- Documentation target: `docs/impl/current/lexical-retrieval.md`

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

#### prove-lexical-retrieval-on-provided-archive

Build and query the lexical projection for the supplied archive and publish its proof bundle.

- Serves: `lexical-retrieval` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `calibrate-russian-tokenization-and-bm25`;
`prove-pipeline-control-on-provided-archive`.
- User-visible outcome: Supplied documents are searchable through the selected Russian lexical
profile, with filters, snippets, identifiers, and citations that resolve to source evidence.
- Scope boundary: Prove lexical load/query behavior and declared evaluation queries; do not claim
semantic retrieval or full-archive relevance from this test archive.
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification, lexical tables/indexes, and
`$RUNS_DIR/proofs/lexical-retrieval/<proof-id>/`.
- Execution path: Forecast; load/build the selected lexical projection; reconcile counts/checksums;
run archive-appropriate smoke and held-out queries; validate citations and limits; rerun unchanged
and record load/index cache decisions.
- Acceptance gates: Projection and source counts reconcile; required queries return valid evidence
under declared metrics; index/query manifests validate; unchanged rerun does not rebuild or reload
unchanged partitions; failures or missing citations keep the task open.
- Documentation target: `docs/impl/current/lexical-retrieval.md`

### Semantic retrieval -- `semantic-retrieval`

#### implement-selective-embedding-pipeline

Add policy-driven embedding tiers, provider-neutral batching, versioned artifacts, and pgvector load
without embedding the entire archive by default.

- Serves: `semantic-retrieval` --
[Search and vector projections](../design/spec.md#search-and-vector-projections)
- Agent status: RUN NEEDED
- Dependencies: `implement-stage-dag-cli-and-make-targets`; `implement-local-inference-adapters`;
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
- Acceptance gates: Interrupted batch resumes; input/model/config changes create new ids;
selected-tier reason is recorded; embedding output is deterministic within declared tolerance; 16
GB VRAM stays within budget.
- Documentation target: `docs/impl/current/semantic-retrieval.md`

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
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification, embedding/vector
artifacts, and
`$RUNS_DIR/proofs/semantic-retrieval/<proof-id>/`.
- Execution path: Forecast model and index resources; run selected embedding/load/query profiles;
validate vector identities, counts, paired retrieval evidence, and fallback; rerun unchanged and
record that model inference and index build are reused.
- Acceptance gates: A usable branch has checksum-valid vectors/indexes, cited queries, measured
quality/cost verdict, and no heavy work on identical rerun. `not-selected` is valid only with the
declared measured negative result and verified lexical fallback; other failures keep the task open.
- Documentation target: `docs/impl/current/semantic-retrieval.md`

### Russian NLP -- `russian-nlp`

#### build-russian-language-morphology-and-terminology-lane

Implement language identification, encoding/noise signals, token/morphological analysis, and
versioned dictionaries without changing source evidence.

- Serves: `russian-nlp` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Dependencies: `implement-normalization-dedupe-and-chunking`;
`implement-stage-dag-cli-and-make-targets`.
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
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/nlp/`, mention tables,
and `$RUNS_DIR/proofs/russian-nlp/<proof-id>/`.
- Execution path: Forecast; run NLP and mention extraction; validate schemas, language coverage,
offset/source mapping, per-type summaries, and model fingerprints; rerun unchanged and record
dictionary/model cache hits.
- Acceptance gates: All usable NLP outputs validate and resolve to source spans; unsupported and
ambiguous cases are counted; configured metrics are reported by present stratum; unchanged rerun
performs no heavy NER or morphology work; incomplete evidence keeps the task open.
- Documentation target: `docs/impl/current/russian-nlp.md`

### Knowledge extraction -- `knowledge-extraction`

#### implement-provenance-bearing-fact-extraction

Extract proposed facts with deterministic patterns/table rules first and validated local structured
LLM calls for bounded high-value lanes.

- Serves: `knowledge-extraction` --
[Canonical object and fact model](../design/spec.md#canonical-object-and-fact-model)
- Agent status: RUN NEEDED
- Dependencies: `evaluate-general-and-domain-ner`; `implement-local-inference-adapters`;
`create-canonical-relational-schema`.
- User-visible outcome: Design/revision, assembly/component, equipment, supplier, order, shipment,
invoice, payment, date, quantity, and other relations are queryable with exact source evidence and
extraction provenance.
- Scope boundary: Insert `proposed` assertions only; no automatic truth acceptance and no ontology
axiom invention.
- Data and artifact paths: `$RESULTS_DIR/normalized/facts/`, `kg.fact`, `kg.fact_qualifier`,
`src/arxiv_int/extraction/facts/`, generated output schemas, and prompt packages.
- Execution path: Implement typed rule/table extractors, including design/BOM and commercial
document lanes; define JSON-schema LLM envelopes; retrieve bounded evidence; validate source spans,
types, units, currencies, model output, and one bounded repair; batch and checkpoint by content hash.
- Acceptance gates: Malformed, unsupported, uncited, and span-mismatched outputs are retained as
typed failures, not facts; per-type precision/recall and citation validity are measured; rerun is
idempotent.
- Documentation target: `docs/impl/current/knowledge-extraction.md`

#### implement-fact-validation-conflict-and-review-overlays

Validate facts against ontology and temporal/unit rules, group duplicates/contradictions, and expose
reversible review state.

- Serves: `knowledge-extraction` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: CLEAR
- Dependencies: `implement-provenance-bearing-fact-extraction`;
`establish-versioned-ontology-assets`.
- User-visible outcome: Conflicting claims and uncertain facts remain visible and reviewable instead
of being silently collapsed into one value.
- Scope boundary: Validate and group; human acceptance thresholds and domain truth judgments remain
human-gated.
- Data and artifact paths: `kg.fact`, `kg.fact_conflict`, `kg.review_event`,
`$RESULTS_DIR/normalized/fact-findings/`, and `src/arxiv_int/extraction/validation/`.
- Execution path: Add domain/range, typed literal, unit, functional relation, temporal, duplicate,
contradiction, and evidence checks; create immutable decision events and reversible active views.
- Acceptance gates: Synthetic and gold contradictions are found with measured precision; every
active status derives from an audit event; rejected/superseded facts retain evidence; rules are
versioned and replayable.
- Documentation target: `docs/impl/current/knowledge-extraction.md`

#### prove-knowledge-extraction-on-provided-archive

Run fact extraction and validation on the supplied archive and publish the knowledge-extraction
proof bundle.

- Serves: `knowledge-extraction` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-fact-validation-conflict-and-review-overlays`;
`prove-russian-nlp-on-provided-archive`; `implement-evidence-based-pipeline-forecast`.
- User-visible outcome: Proposed design, commercial, and general facts from supplied files are
inspectable with exact evidence, validation findings, conflicts, and extractor/model provenance.
- Scope boundary: Exercise only forecast-approved deterministic and local-model lanes; do not
auto-accept facts or claim correctness for unreviewed domain assertions.
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/facts/`, knowledge
tables, and `$RUNS_DIR/proofs/knowledge-extraction/<proof-id>/`.
- Execution path: Forecast; run configured fact lanes and validators; reconcile input/output/failure
counts; sample evidence-span resolution and conflict grouping; rerun unchanged and capture rule/model
cache decisions.
- Acceptance gates: Every emitted fact passes shape and evidence validation or remains a typed
failure; conflicts and review states are preserved; present-type metrics and coverage are reported;
unchanged rerun does not invoke heavy extraction; proof checksums and fingerprints validate.
- Documentation target: `docs/impl/current/knowledge-extraction.md`

### Identity, ontology, and graph -- `identity-ontology-graph`

#### implement-probabilistic-entity-resolution

Build reversible object clusters from mentions using blocking, explainable comparisons, and labelled
operating points.

- Serves: `identity-ontology-graph` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Dependencies: `evaluate-general-and-domain-ner`; `create-canonical-relational-schema`;
`create-evaluation-fixtures-and-metrics`.
- User-visible outcome: Aliases such as organization names, suppliers, equipment models, and
transliterations resolve to canonical objects with match evidence and uncertainty.
- Scope boundary: Propose or apply reversible cluster overlays; never rewrite source mentions or
auto-merge below the approved precision threshold.
- Data and artifact paths: `kg.object`, `kg.alias`, `kg.resolution_edge`, `kg.cluster_version`,
`$RESULTS_DIR/normalized/linkage/`, and `src/arxiv_int/identity/`.
- Execution path: Use maintained Splink 4 directly behind the local seam with DuckDB; define
blocking and comparison specs; train/calibrate from reviewer labels; persist the model, thresholds,
pair probabilities, and cluster algorithm.
- Acceptance gates: Held-out pair and cluster metrics pass the predeclared auto-merge precision
floor; replay does not refit; uncertain/rejected pairs remain separate; rollback restores the
prior cluster view.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`

#### establish-versioned-ontology-assets

Create the controlled vocabulary, classes, predicates, semantic mappings, SHACL shapes, and open RDF
exports that validate the knowledge model.

- Serves: `identity-ontology-graph` -- [AGE graph projection](../design/spec.md#age-graph-projection)
- Agent status: CLEAR
- Dependencies: `establish-canonical-contract-registry`; representative domain vocabulary can begin
from reviewed fixtures.
- User-visible outcome: Object/fact semantics are inspectable, versioned, exportable, and testable
independently of AGE.
- Scope boundary: Establish a minimal evidence-backed ontology; do not claim automated ontology
induction is authoritative.
- Data and artifact paths: `contracts/canonical/`, `ontology/*.ttl`, `ontology/*.shacl.ttl`,
`ontology.*` tables, and `tests/ontology/`.
- Execution path: Define stable URIs, labels in source languages, domain/range, units, selected
disjoint/functional constraints, mappings, and deprecation/alias rules; validate with
rdflib/pySHACL and a second reasoner where practical.
- Acceptance gates: RDF parses; SHACL positive/negative fixtures agree with application validation;
every active predicate maps to a contract binding; breaking ontology changes follow evolution
policy.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`

#### build-and-validate-age-projection

Project accepted and selected proposed canonical objects/facts into a versioned AGE graph, with
recursive SQL and open export fallbacks.

- Serves: `identity-ontology-graph` -- [AGE graph projection](../design/spec.md#age-graph-projection)
- Agent status: RUN NEEDED
- Dependencies: `implement-probabilistic-entity-resolution`;
`implement-fact-validation-conflict-and-review-overlays`;
`implement-rebuildable-search-and-graph-projections`; `establish-versioned-ontology-assets`.
- User-visible outcome: Operators can run bounded Cypher traversals and inspect a graph whose nodes
and edges resolve back to canonical facts and evidence.
- Scope boundary: Projection and bounded query API only; no Neo4j GDS parity claim and no large text
duplication into AGE.
- Data and artifact paths: AGE graph schemas, `ctl.projection`, `$RUNS_DIR/<run-id>/graph/`,
`src/arxiv_int/graph/`, and GraphML/JSON-LD/Turtle exports.
- Execution path: Batch vertices/edges with stable ids; checkpoint high-water marks; validate
counts, ids, sampled paths, and SQL/Cypher results; switch active graph version atomically;
enforce depth/result/time limits.
- Acceptance gates: Rebuild is deterministic; sampled traversals match recursive SQL; evidence
lookup succeeds for every sampled edge; AGE-disabled mode exports the same logical graph; failed
build leaves prior graph active.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`

#### prove-identity-ontology-graph-on-provided-archive

Resolve identities, validate ontology assets, build the graph or fallback exports, and publish the
supplied-archive proof bundle.

- Serves: `identity-ontology-graph` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `build-and-validate-age-projection`;
`prove-knowledge-extraction-on-provided-archive`.
- User-visible outcome: Supplied-archive objects, aliases, candidate clusters, ontology terms, and
bounded graph paths are inspectable with reversible decisions and source evidence.
- Scope boundary: Use approved or explicitly proposed review states; do not silently merge uncertain
entities, publish disputed ontology changes, or require AGE when the declared fallback is active.
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification,
identity/ontology/graph stores and
exports, and `$RUNS_DIR/proofs/identity-ontology-graph/<proof-id>/`.
- Execution path: Forecast; run entity resolution and ontology validation; build the active AGE or
relational/open-export graph; reconcile counts and sampled SQL/path parity; resolve edge evidence;
rerun unchanged and capture linkage/reasoning/projection cache hits.
- Acceptance gates: Cluster and ontology validators pass at declared policies; graph/fallback counts
and sampled paths agree with canonical facts; every sampled edge has evidence; unchanged rerun avoids
heavy linkage and graph rebuild; failed projection never replaces the prior active version.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`

### Domain investigation artifacts -- `domain-investigation-artifacts`

#### define-domain-investigation-contracts-and-ontology

Define evidence semantics and output contracts for design relationships, bills of materials,
supply chains, invoices, payments, and their run-artifact registry entries.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: CLEAR
- Dependencies: `establish-versioned-ontology-assets`;
`implement-deterministic-schema-generation`.
- User-visible outcome: Operators see consistent definitions for `part-of`, supply roles, invoice
obligations, payment allocations, conflicts, and empty/partial results before graphs are generated.
- Scope boundary: Define source-asserted investigation semantics and schemas; do not infer missing
ownership, delivery, settlement, liability, engineering completeness, or accounting truth.
- Data and artifact paths: `contracts/datasets/domain-artifacts*.odcs.yaml`,
`contracts/canonical/`, `ontology/`, generated table/JSON/graph schemas, and domain fixtures.
- Execution path: Model designs, revisions, assemblies, components, materials, parties, locations,
orders, shipments, invoices, invoice lines, payments, currencies, quantities, allocations, and
typed relations; define evidence, review/inclusion, arithmetic, conflict, and artifact-status rules.
- Acceptance gates: Contract and ontology validation pass; positive and negative fixtures separate
reference from `part-of`, invoice from delivery, and amount/date similarity from payment; units,
currencies, direction, cardinality, and creation statuses are unambiguous and versioned.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`

#### build-evidence-backed-domain-artifacts

Project canonical objects and facts into relationship, BOM, supply-chain, and invoice/payment
tables and bounded graphical representations.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `define-domain-investigation-contracts-and-ontology`;
`implement-fact-validation-conflict-and-review-overlays`;
`implement-probabilistic-entity-resolution`; `build-and-validate-age-projection` may yield AGE or
the relational/open-export fallback; `approve-representative-corpus-and-gold`.
- User-visible outcome: When the archive contains qualifying evidence, operators receive cited
assembly trees, relationship graphs, supply networks, and invoice/payment flows with uncertainty and
conflicts visible.
- Scope boundary: Generate bounded derived views from selected review states; do not silently
promote proposed facts, reconcile currencies without a sourced rate, or claim completeness beyond
reported evidence coverage.
- Data and artifact paths: `$RESULTS_DIR/normalized/domain-artifacts/`,
`src/arxiv_int/domain_artifacts/`, `$RUNS_DIR/<run-id>/artifacts/`, reviewed domain fixtures, and
snapshot/render tests.
- Execution path: Build typed tabular/JSON projections; validate quantities, units, totals, and
allocations; emit Parquet/JSON, GraphML, and deterministic self-contained HTML or SVG through the
lightest accepted renderer; preserve fact ids, source spans, policy, confidence, and review state on
every element.
- Acceptance gates: Per-family relation precision/recall, BOM parent/child and quantity accuracy,
invoice arithmetic, payment-allocation accuracy, unresolved/conflict coverage, table/graph parity,
evidence links, deterministic bounded renders, and resource cost meet declared gates. Unsupported or
evidence-free families produce valid `partial` or `empty` results.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`

#### register-and-expose-domain-artifacts

Publish all domain artifacts through an atomic per-run registry and expose discovery links without
creating another source of truth.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: CLEAR
- Dependencies: `build-evidence-backed-domain-artifacts`;
`implement-run-ledger-and-atomic-artifacts`.
- User-visible outcome: Every run reaching the domain-artifact stage lists which special artifacts
were produced, partial, empty, or failed and provides a verified local path plus evidence/coverage
summary for each.
- Scope boundary: Register immutable outputs and read-only links; do not mark failed output
successful, embed unrestricted source text, or let dashboards become the canonical registry.
- Data and artifact paths: `ctl.artifact`, additive `db/migrations/`,
`$RUNS_DIR/<run-id>/artifacts/registry.{json,parquet}`, `src/arxiv_int/reporting/artifacts/`, CLI/API
responses, and registry contract tests.
- Execution path: Generate and apply additive artifact-registry migrations; assign stable artifact
ids; capture type/schema/generator/input/policy fingerprints, paths, media types, checksums, counts,
evidence coverage, status, and failure reason; validate output before one atomic registry
publication; add `run artifacts` listing and report links.
- Acceptance gates: Contract fixtures cover produced/partial/empty/failed states; every successful
row resolves to checksum-valid files and source evidence; missing or corrupt output prevents
publication; unchanged reruns reuse ids; CLI/API and manifest/SQL registries agree.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`

#### prove-domain-investigation-artifacts-on-provided-archive

Generate every applicable relationship, BOM, supply-chain, and invoice/payment artifact family from
the supplied archive and publish its proof bundle.

- Serves: `domain-investigation-artifacts` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `register-and-expose-domain-artifacts`;
`prove-identity-ontology-graph-on-provided-archive`.
- User-visible outcome: The run artifact registry exposes each applicable supplied-archive domain
view, its table/graph files, evidence coverage, conflicts, review policy, and production status.
- Scope boundary: Generate only evidence-supported bounded views; accept contract-valid `empty` or
`partial` families and never manufacture relations to make a graphical artifact non-empty.
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/domain-artifacts/`, and
`$RUNS_DIR/proofs/domain-investigation-artifacts/<proof-id>/`.
- Execution path: Forecast; build all configured artifact families; validate arithmetic,
table-to-graph parity, source links, renders, registry rows, and checksums; rerun unchanged and record
projection/render cache hits.
- Acceptance gates: Every configured family is honestly `produced`, `partial`, or `empty` with a
valid reason; no failed output is registered as successful; evidence and policy resolve for every
element; identical rerun performs no heavy extraction, projection, or rendering.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`

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

#### build-search-graph-and-report-interfaces

Expose bounded lexical/semantic/hybrid search, object/fact lookup, Cypher or SQL traversal, and
equipment/supplier reports through CLI and a small local API.

- Serves: `discovery-visualization` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: `calibrate-russian-tokenization-and-bm25`; `build-and-validate-age-projection`;
`register-and-expose-domain-artifacts`; `implement-scalable-topic-discovery`.
- User-visible outcome: An operator can find evidence, inspect objects and facts, traverse
relations, and open or export cited equipment, supplier, BOM, supply-chain, and invoice/payment
artifacts without writing SQL.
- Scope boundary: Read-only query/report boundary with limits; no public multi-user web product and
no hidden acceptance of proposed facts.
- Data and artifact paths: `src/arxiv_int/query/`, `src/arxiv_int/reporting/`,
`$RUNS_DIR/<run-id>/reports/`, and API/query tests.
- Execution path: Add typed query objects, pagination, filters, review-state controls, evidence
expansion, report definitions, CSV/Parquet/HTML exports, and explain modes; register the `report`
stage body behind `arxiv-int report build RUN_ID` and `search lexical|semantic|hybrid`; constrain
text/depth/result/time.
- Acceptance gates: Scenario fixtures return complete citations and declared inclusion rules; SQL
injection and path tests pass; large/unbounded requests are refused; exports conform to generated
contracts.
- Documentation target: `docs/impl/current/discovery-visualization.md`

#### provision-local-dashboards-and-age-viewer

Provision Grafana dashboards and the optional AGE Viewer profile without adding another canonical
store.

- Serves: `discovery-visualization` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Dependencies: `build-search-graph-and-report-interfaces`; Compose profiles documented in
[Portable runtime](current/portable-runtime.md).
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
- Acceptance gates: Fresh profile start needs no manual datasource setup; read-only roles cannot
mutate canonical rows; dashboards load fixture data; deleting `SERVICE_STATE_DIR` loses no
provisioned definition; graph profile absence degrades cleanly.
- Documentation target: `docs/impl/current/discovery-visualization.md`

#### prove-discovery-and-visualization-on-provided-archive

Run topic discovery, search/report scenarios, exports, and configured local views against supplied
archive artifacts and publish the discovery proof bundle.

- Serves: `discovery-visualization` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `provision-local-dashboards-and-age-viewer`;
`prove-domain-investigation-artifacts-on-provided-archive`;
`prove-lexical-retrieval-on-provided-archive`.
- User-visible outcome: Operators can navigate supplied-archive topics, searches, objects, facts,
graphs, and domain reports through bounded interfaces whose displayed evidence can be verified.
- Scope boundary: Prove local read-only scenarios and available profiles; do not expose services
publicly, require an optional UI/AGE profile with a valid fallback, or claim usability acceptance for
scenarios not executed.
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification,
topic/query/report/export artifacts, and
`$RUNS_DIR/proofs/discovery-visualization/<proof-id>/`.
- Execution path: Forecast; run topics and report generation; execute scripted lexical and available
hybrid, object/fact, graph, BOM, supply-chain, and invoice/payment scenarios; validate citations,
limits, exports, dashboards/views, and unchanged-rerun cache decisions.
- Acceptance gates: Every executed scenario resolves to bounded, policy-labelled source evidence;
exports and configured views validate; unavailable optional profiles have working fallbacks;
unchanged rerun avoids heavy topic/report recomputation; unresolved failures keep proof open.
- Documentation target: `docs/impl/current/discovery-visualization.md`

### Evaluation and evidence -- `evaluation-evidence`

#### publish-provided-archive-end-to-end-proof

Run evaluation and reporting over the supplied archive and publish one proof index covering every
usable pipeline stage and artifact family.

- Serves: `evaluation-evidence` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: `prove-archive-classification-on-provided-archive`;
`prove-semantic-retrieval-on-provided-archive`;
`prove-discovery-and-visualization-on-provided-archive`;
`create-evaluation-fixtures-and-metrics`.
- User-visible outcome: One command/report shows which pipeline stages have current proof on the
supplied file silos, which artifacts they produced, which optional branches were not selected, and
how every result resolves to evidence.
- Scope boundary: Evaluate and index bounded proof outputs; do not substitute this test archive for
representative-scale authorization or conceal failed, stale, blocked, or absent stages.
- Data and artifact paths: `$PROOF_ARCHIVE_DIR` used without modification, prior proof bundles, and
`$RUNS_DIR/proofs/evaluation-evidence/<proof-id>/` containing evaluation/report outputs and the
end-to-end proof index.
- Execution path: Require a passing forecast; verify prior proof fingerprints; run `evaluate` and
`report`; join stage, artifact, validation, error, resource, and cache evidence; rerun unchanged;
publish a machine-readable and human-readable coverage matrix with current-doc references.
- Acceptance gates: Every required usable stage has a current `passed` or valid-empty proof and
checksum-valid artifacts; optional not-selected branches cite verdicts and fallbacks; the end-to-end
report exposes all failures/coverage gaps; unchanged evaluation/report work is reused; private paths
and corpus content are absent from repository documentation.
- Documentation target: `docs/impl/current/evaluation.md`

#### run-representative-scale-pilots

Measure storage amplification, throughput, memory, WAL/temp growth, retrieval quality, resume, and
rebuild on two progressively larger corpus slices.

- Serves: `evaluation-evidence` --
[Performance and scalability assumptions](../design/spec.md#performance-and-scalability-assumptions)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: All required Phase 0-4 tasks for the selected pilot path;
`create-evaluation-fixtures-and-metrics`; `approve-representative-corpus-and-gold`;
`publish-provided-archive-end-to-end-proof`; `implement-evidence-based-pipeline-forecast`.
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

#### audit-published-claims-and-artifact-lineage

Verify artifact lineage and every number or architectural claim published in reports and
current-state docs.

- Serves: `evaluation-evidence` --
[Implementation boundaries](../design/spec.md#implementation-boundaries)
- Agent status: CLEAR
- Dependencies: `create-evaluation-fixtures-and-metrics`; every task that publishes an evaluated
artifact or current-state measurement.
- User-visible outcome: A stale run cannot continue to support a changed published claim.
- Scope boundary: Audit generated evidence and published claims; do not invent missing benchmarks.
- Data and artifact paths: `ctl.artifact`, run manifests, current-state measurements, and the docs
claim registry.
- Execution path: Link published metrics to run fields and content pins; list invalidations caused
by contract, model, profile, classification, or artifact changes.
- Acceptance gates: Every published number resolves to one immutable artifact field; implementation
boundaries remain explicit; orphan or stale claims fail CI.
- Documentation target: `docs/impl/current/evaluation.md`

### Operational recovery -- `operational-recovery`

#### harden-local-security-and-no-egress-mode

Enforce read-only input, loopback services, least-privilege roles, secret redaction, bounded paths,
container mounts, and a network-denied run mode.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: RUN NEEDED
- Dependencies: Compose profiles documented in [Portable runtime](current/portable-runtime.md);
`create-canonical-relational-schema`; `implement-local-inference-adapters`;
`implement-audited-archive-reorganization`.
- User-visible outcome: The local stack can process prepared inputs without unintended network
access or writable archive access, while the separate reorganization command cannot write without an
accepted exact plan.
- Scope boundary: Host-local hardening and verification; not a formal third-party penetration test
or multi-user internet deployment.
- Data and artifact paths: Compose security settings, database role migrations, `.env.example`,
`src/arxiv_int/security/`, and security integration fixtures.
- Execution path: Apply non-root/read-only mounts where supported, localhost ports, role separation,
URL/path allowlists, secret filters, image/model pin checks, and network-denied integration
profile.
- Acceptance gates: Prepared smoke succeeds with egress denied; pipeline archive writes fail;
reorganization writes without an accepted plan fail; UI role mutations fail; secrets/corpus snippets
do not appear in logs; dependency/image scan findings are triaged without suppressing gates.
- Documentation target: `docs/impl/current/operations.md`

#### implement-backup-restore-and-rebuild-runbook

Create and exercise backups for contracts/config, normalized artifacts, PostgreSQL, and projection
rebuild metadata.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: RUN NEEDED
- Dependencies: `implement-rebuildable-search-and-graph-projections`;
`harden-local-security-and-no-egress-mode`; `run-representative-scale-pilots` can use the first
pilot for the drill; `register-and-expose-domain-artifacts`.
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
manifests, archive move ledgers, artifact registries, checksums, and free-space requirements; restore
into a new directory, run contract/live-store/source-lookup checks, and rebuild disposable
projections.
- Acceptance gates: Clean-target restore reproduces canonical counts/checksums and sampled queries;
a backup missing a configured WAL or tablespace root fails as incomplete rather than restoring a
partial cluster; missing/corrupt backup parts fail before mutation; recovery time/space are recorded;
original data remains untouched.
- Documentation target: `docs/impl/current/operations.md`

#### test-failure-and-capacity-boundaries

Exercise disk pressure, database restart, worker death, corrupt artifacts, model timeout, invalid
index, and stale lease behavior before full-corpus authorization.

- Serves: `operational-recovery` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: RUN NEEDED
- Dependencies: `implement-backup-restore-and-rebuild-runbook`;
`add-progress-logging-and-resource-telemetry`; `implement-audited-archive-reorganization`;
`implement-evidence-based-pipeline-forecast`;
`implement-incremental-reconciliation-and-stale-pruning`.
- User-visible outcome: Known failures stop safely, preserve evidence, and provide a tested
resume/rebuild action instead of corrupting state.
- Scope boundary: Controlled disposable fixtures and pilot paths only; no destructive testing
against the real archive or sole backup.
- Data and artifact paths: Disposable test volumes under `$RESULTS_DIR/test/`,
`$RUNS_DIR/<run-id>/failure-tests/`, and recovery fixtures.
- Execution path: Inject bounded failures at artifact write, archive rename journal, COPY, index
build, AGE projection, model call, and shutdown boundaries; verify alerts, state transitions,
cleanup plans, source lookup, and recovery.
- Acceptance gates: No accepted partial artifact or duplicate canonical row results; retries are
bounded; invalid indexes/projections never become active; forecast and each large-stage recheck
refuse before the configured safety margin is consumed; stale cleanup never removes protected data.
- Documentation target: `docs/impl/current/operations.md`

## Human-Assisted Tasks

### Corpus foundation -- `corpus-foundation`

#### approve-representative-corpus-and-gold

Select a legally usable, distribution-representative corpus slice and adjudicate the gold
extraction, classification, dedupe, Russian query, entity, fact, ontology, domain-artifact, and
report samples.

- Serves: `corpus-foundation` -- [Evaluation datasets](../design/spec.md#evaluation-datasets)
- Agent status: BLOCKED BY HUMAN
- Dependencies: Inventory summary from `implement-streaming-inventory`; draft fixture tooling from
`create-evaluation-fixtures-and-metrics`.
- User-visible outcome: Expensive model/store decisions are evaluated on the archive's real formats,
languages, noise, and business questions rather than synthetic convenience data, and one approved
readable path is designated as `PROOF_ARCHIVE_DIR`.
- Scope boundary: Human selects and reviews bounded samples and confirms permission to process them;
no full-corpus authorization.
- Data and artifact paths: Private `$PROOF_ARCHIVE_DIR` used without modification, approved slices,
local review ledgers under `$RUNS_DIR/<run-id>/review/`, and frozen manifests without copied private
text or machine-specific paths in Git.
- Execution path: Produce stratified candidate manifests and draft labels; human reviews source
spans, file classes and exceptional outcomes, duplicate groups, queries, entities, facts, ontology
constraints, design/BOM, equipment, suppliers, invoices, and payments; seal tuning/final splits.
- Acceptance gates: Processing authorization and the readable proof path are explicit; coverage across
major bytes/file types/languages and high-value questions is documented; reviewer decisions and
disagreements are recorded; final split remains unopened for tuning.
- Documentation target: `docs/impl/current/evaluation.md`

### Archive classification -- `archive-classification`

#### approve-classification-and-reorganization-policy

Review the UDC-derived vocabulary, classification operating point, directory vocabulary, placement
mode, and one complete dry-run before any real archive reorganization.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: HUMAN-GATED
- Dependencies: `prove-archive-classification-on-provided-archive`;
`implement-backup-restore-and-rebuild-runbook` for the verified restore path; final classification
evaluation.
- User-visible outcome: The owner explicitly accepts which assignments may determine paths, chooses
between a copy into a target tree and an in-place move, and can `apply`, revise thresholds/slugs,
keep the mapping without placement, or stop.
- Scope boundary: Approve one versioned policy, mode, and plan; no automatic approval from
confidence, no licence waiver, and no mutation of the archive during review.
- Data and artifact paths: `configs/policy/classification.yaml`, vocabulary/licence manifest,
classification evaluation, `$RUNS_DIR/<run-id>/archive-reorganization/move-plan.json`, dry-run diff,
backup reference, and local decision ledger.
- Execution path: Present class and ancestor errors, `unclassified`/`unreadable` samples, coverage,
calibration, proposed ASCII paths, collisions/path lengths, placement counts/bytes, target free space
for `copy` against archive rewrite risk for `move`, source lookup, rollback drill, and UDC
attribution; record the exact accepted fingerprints, mode, and decision.
- Acceptance gates: Decision is `apply`, `mapping-only`, `revise`, or `stop`; `apply` names the exact
classification and plan ids, mode, silo root and device, copy target or verified backup, stop
conditions, and responsible operator; stale or unapproved plans remain non-writable.
- Documentation target: `docs/impl/current/archive-classification.md`

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

### Identity, ontology, and graph -- `identity-ontology-graph`

#### approve-entity-merge-and-ontology-policy

Review entity-resolution operating points and ontology terms/constraints that can change graph and
report meaning.

- Serves: `identity-ontology-graph` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: HUMAN-GATED
- Dependencies: `prove-identity-ontology-graph-on-provided-archive`; held-out linkage curves from
`implement-probabilistic-entity-resolution`; ontology review package from
`establish-versioned-ontology-assets`.
- User-visible outcome: Auto-merge thresholds and ontology semantics reflect the owner's precision
tolerance and domain meaning.
- Scope boundary: Approve bounded policies and terms; no manual editing of source mentions or
one-off hidden merges.
- Data and artifact paths: `configs/policy/identity.yaml`, versioned ontology assets, review
ledgers, and evaluation bundles.
- Execution path: Present pair/cluster errors, threshold curves, ambiguous aliases, term
definitions, domain/range, and constraint examples; record decisions as versioned configuration
and ontology commits.
- Acceptance gates: Auto-merge precision floor and review band are explicit; disputed terms remain
draft; every accepted change has rollback/deprecation behavior.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`

### Domain investigation artifacts -- `domain-investigation-artifacts`

#### approve-domain-artifact-semantics-and-inclusion

Review domain meanings and inclusion policies for relationship, BOM, supply-chain, invoice, and
payment artifacts before they are presented as accepted investigation results.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: HUMAN-GATED
- Dependencies: `prove-domain-investigation-artifacts-on-provided-archive`; approved fact and
identity/ontology policies; per-family final evaluation results.
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
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`

### Discovery and visualization -- `discovery-visualization`

#### accept-operator-discovery-workflows

Validate that a domain operator can complete representative topic, search, object/fact, graph,
equipment, supplier, BOM, supply-chain, and invoice/payment workflows with understandable evidence
and filters.

- Serves: `discovery-visualization` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: HUMAN-GATED
- Dependencies: `build-search-graph-and-report-interfaces`;
`provision-local-dashboards-and-age-viewer`;
`prove-discovery-and-visualization-on-provided-archive`; approved fact, identity, and
domain-artifact policies.
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

### Evaluation and evidence -- `evaluation-evidence`

#### authorize-full-corpus-run

Decide whether measured pilot quality, capacity, recovery, and review cost justify running the full
archive and which optional profiles are included.

- Serves: `evaluation-evidence` -- [Required acceptance gates](../design/spec.md#required-acceptance-gates)
- Agent status: HUMAN-GATED
- Dependencies: `run-representative-scale-pilots`; `implement-backup-restore-and-rebuild-runbook`;
approved discovery, classification, fact, identity, ontology, and domain-artifact policies.
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

### Operational recovery -- `operational-recovery`

#### accept-recovery-and-security-posture

Witness a clean-target restore and review local access, secret, network, retention, and
removable-disk procedures before treating the system as the archive's working knowledge platform.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: HUMAN-GATED
- Dependencies: `harden-local-security-and-no-egress-mode`;
`implement-backup-restore-and-rebuild-runbook`; `test-failure-and-capacity-boundaries`.
- User-visible outcome: The owner knows what is backed up, what is rebuildable, how moved sources are
located or restored, how long recovery takes, and which local risks remain accepted.
- Scope boundary: Owner acceptance of the documented single-host posture; not a certification of
high availability, enterprise support, or physical security.
- Data and artifact paths: Recovery report, security checklist, backup inventory, retention policy,
and local acceptance decision.
- Execution path: Observe restore, source lookup, artifact registry, and sampled query parity;
review ports, roles, mounts, reorganization authorization, secrets, model/image provenance, backup
separation, retention, and emergency stop/restart commands; record residual risks.
- Acceptance gates: Restore evidence and residual-risk list are signed off or rejected; rejected
items return to the owning capability; Community ParadeDB HA limitations remain explicit.
- Documentation target: `docs/impl/current/operations.md`
