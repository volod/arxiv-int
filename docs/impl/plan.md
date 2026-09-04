# arxiv-int Implementation Plan

Forward-only: this file describes work that remains. Product behavior, boundaries, and evaluation
belong in [the specification](../design/spec.md). As capabilities become available, durable implementation
detail and evidence move to `docs/impl/current/`; finished tasks are removed from this plan.

Every task serves a capability from the [capability registry](../design/spec.md#capability-registry).
Capability groups follow registry order in both lanes. Take the first required task in the earliest
group whose dependencies are satisfied. Within a group, required tasks precede optional work and
cheap deterministic work precedes expensive runs.

Statuses follow the project planning workflow:

- `CLEAR`: an agent can implement and verify the task locally.
- `RUN NEEDED`: implementation is deterministic, but acceptance includes a declared heavier run.
- `BLOCKED BY HUMAN`: a person must supply an artifact or decision before acceptance.
- `HUMAN-GATED`: the outcome itself requires human judgment, authorization, or risk acceptance.
- `Research: yes` means a well-supported negative result is acceptable.



## Delivery phases and dependency spine


| Phase                       | Outcome                                                          | Capability span                                          | Exit signal                                                     |
| --------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------- |
| 0 - Foundation              | Personalized repo, portable paths, contracts, one database image | `project-foundation` through `canonical-store`           | Fresh-copy service and contract smoke passes                    |
| 1 - Local evidence seams    | Local inference adapters and replayable evaluation fixtures      | `local-inference`, `evaluation-foundation`               | Provider and metric conformance tests pass                      |
| 2 - Corpus substrate        | Rebuildable normalized lake and restartable stages               | `corpus-foundation`, `pipeline-control`                  | Representative extraction run resumes without duplication       |
| 3 - Retrieval and NLP       | Russian lexical baseline, selected vectors, mentions             | `lexical-retrieval` through `russian-nlp`                | Held-out lexical and NLP baselines are readable                 |
| 4 - Knowledge and discovery | Facts, identity, ontology, graph, topics, reports, UI            | `knowledge-extraction` through `discovery-visualization` | Evidence-bearing operator scenarios pass                        |
| 5 - Evidence and operations | Comparative scale evidence and recovery                          | `evaluation-evidence`, `operational-recovery`            | Staged pilot and restore drill support an adopt/retain decision |


The critical path is:

```text
project foundation
  -> portable runtime
  -> contract governance
  -> canonical store
  -> local inference and evaluation foundation
  -> corpus foundation
  -> pipeline control
  -> lexical retrieval
  -> Russian NLP
  -> knowledge extraction
  -> identity/ontology/graph
  -> discovery and visualization
  -> evaluation and operational recovery
```

Semantic retrieval and vLLM are evaluated branches. They must not block a useful lexical, CPU-first
system when their valid result is `retain baseline`.

## Agent Implementation Tasks



### Project foundation -- `project-foundation`



#### establish-domain-dependency-seams

Define the smallest core dependency set and optional extras so heavy extraction, NLP, graph, UI,
evaluation, and GPU stacks stay isolated.

- Serves: `project-foundation` -- [Design principles](../design/spec.md#design-principles)
- Agent status: CLEAR
- Dependencies: Personalized package and CLI identity documented in
[Project foundation](current/project-foundation.md#project-identity).
- User-visible outcome: A fresh operator can install the core CLI quickly and add only the feature
groups required for the selected pipeline stage.
- Scope boundary: Define extras and adapter protocols; do not download models or run services.
- Data and artifact paths: `pyproject.toml`, `uv.lock`, `src/arxiv_int/interfaces/`,
`docs/guide/development.md`, and dependency-license notices.
- Execution path: Add typed protocols for extractors, embedders, inference providers, stores, and
stage runners; declare non-conflicting extras; pin output-sensitive tooling; document system
dependencies.
- Acceptance gates: Core import has no optional heavy imports; missing extras produce actionable
messages; lock resolution, license inventory, unit tests, and `make ci` pass.
- Documentation target: `docs/impl/current/project-foundation.md`



### Portable runtime -- `portable-runtime`



#### implement-layered-configuration-and-path-safety

Implement the `.env` and CLI precedence model plus safe resolution of checkout-independent,
multi-SSD paths.

- Serves: `portable-runtime` --
[Configuration and multi-SSD paths](../design/spec.md#configuration-and-multi-ssd-paths)
- Agent status: CLEAR
- Dependencies: `establish-domain-dependency-seams`.
- User-visible outcome: The same checkout runs with archive, normalized data, PostgreSQL, run,
model-cache, and scratch paths on different disks.
- Scope boundary: Resolve and validate configuration; do not create corpus artifacts or start
containers.
- Data and artifact paths: `.env.example`, `.gitignore`, `src/arxiv_int/config.py`,
`src/arxiv_int/paths.py`, `scripts/shared/common.sh`, and `tests/config/`.
- Execution path: Adapt the documented repository and `selfsuvis` env helper patterns; implement
CLI > environment > `.env` > default precedence; resolve relative paths from project root; add
symlink, overlap, root-target, permissions, device-id, and free-space checks.
- Acceptance gates: Unit tests cover multiple current directories, two checkout roots, spaces,
symlinks, separate device ids, CLI overrides, redaction, missing values, and dangerous roots; no
machine-specific path is committed.
- Documentation target: `docs/impl/current/portable-runtime.md`



#### define-compose-profiles-and-operator-wrappers

Create the pinned Compose topology and Make wrappers for core, graph, UI, observability, and vLLM
profiles.

- Serves: `portable-runtime` --
[Docker and local-service topology](../design/spec.md#docker-and-local-service-topology)
- Agent status: CLEAR
- Dependencies: `implement-layered-configuration-and-path-safety`.
- User-visible outcome: `make services-up`, `make services-status`, `make logs`, and
`make services-down` behave consistently from a copied checkout.
- Scope boundary: Define services, healthchecks, mounts, networks, profiles, and wrappers; the AGE
compatibility result belongs to the canonical-store task.
- Data and artifact paths: `compose.yaml`, `docker/`, `Makefile`, `.env.example`,
`scripts/shared/common.sh`, and `tests/compose/`.
- Execution path: Pin images by immutable version/digest, bind service ports to loopback, mount the
archive read-only, use absolute resolved host paths, add host-gateway handling for Ollama, and
render `docker compose config` in CI without starting GPU services.
- Acceptance gates: Compose config validates for each profile and combined supported profiles;
mounts resolve to configured SSD paths; healthchecks and stop behavior are defined; secrets are
absent from rendered test output.
- Documentation target: `docs/impl/current/portable-runtime.md`



#### add-fresh-copy-doctor

Implement a preflight command that turns configuration, tool, device, model endpoint, extension, and
free-space failures into one readiness report.

- Serves: `portable-runtime` --
[Configuration and multi-SSD paths](../design/spec.md#configuration-and-multi-ssd-paths)
- Agent status: CLEAR
- Dependencies: `define-compose-profiles-and-operator-wrappers`.
- User-visible outcome: Before a long run, the operator sees exactly what is ready, degraded,
missing, or unsafe and the command needed next.
- Scope boundary: Read-only diagnostics only; doctor does not install packages, pull models, mutate
services, or create migrations.
- Data and artifact paths: `src/arxiv_int/doctor/`, `tests/doctor/`, and `docs/guide/setup.md`.
- Execution path: Check Python/uv/Docker/Compose, paths and filesystems, RAM/GPU/disk, service
health, extension versions, Ollama/vLLM APIs, contract state, migrations, and model availability;
emit console and JSON reports.
- Acceptance gates: Network-free fixtures cover pass, degraded, and fail states; secrets are masked;
exit codes distinguish ready/degraded/blocked; checks have timeouts.
- Documentation target: `docs/impl/current/portable-runtime.md`



### Contract governance -- `contract-governance`



#### establish-canonical-contract-registry

Define ODCS contracts, a canonical semantic model, dataset registry, and physical-to-canonical
mappings for the first pipeline entities.

- Serves: `contract-governance` --
[Contract-first data governance](../design/spec.md#contract-first-data-governance)
- Agent status: CLEAR
- Dependencies: Personalized package and CLI identity documented in
[Project foundation](current/project-foundation.md#project-identity).
- User-visible outcome: Documents, spans, chunks, objects, mentions, facts, topics, ontology terms,
embeddings, and evaluation items have one reviewable schema source of truth.
- Scope boundary: Define contracts and semantic bindings; do not create live database tables or
infer domain-specific ontology terms from the corpus.
- Data and artifact paths: `contracts/registry.yaml`, `contracts/canonical/`, `contracts/datasets/`,
`contracts/mappings/`, and `src/arxiv_int/contracts/`.
- Execution path: Adapt the MIT `fl-op` registry/canonical-model patterns to ODCS 3.1; namespace
project hints under `x-arxiv-int`; add Data Contract CLI validation and Pydantic loaders that
preserve unknown metadata.
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
- Execution path: Adapt `fl-op` adjacent-history and semantic-fingerprint checks; invoke Avro
reader/writer compatibility and Data Contract CLI breaking checks; integrate dbmate; compare
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
- Dependencies: `define-compose-profiles-and-operator-wrappers`;
`enforce-evolution-and-migration-policy`.
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
- Dependencies: `establish-domain-dependency-seams`;
`implement-layered-configuration-and-path-safety`.
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

Build immutable extraction, Russian retrieval, semantic, entity, fact, ontology, graph, and
reporting fixtures plus paired evaluation utilities.

- Serves: `evaluation-foundation` -- [Evaluation and acceptance](../design/spec.md#evaluation-and-acceptance)
- Agent status: CLEAR
- Dependencies: `establish-canonical-contract-registry`.
- User-visible outcome: Every store/model/pipeline recommendation names the exact frozen items,
metrics, thresholds, and run artifacts that support it.
- Scope boundary: Provide deterministic fixtures and measurement; human gold review remains in the
human lane.
- Data and artifact paths: `tests/fixtures/`, `eval.*`, `src/arxiv_int/evaluation/`,
`configs/evaluation/`, and `$RUNS_DIR/<run-id>/evaluation/`.
- Execution path: Adapt loc-lm-bench evidence patterns for recall@k, MRR, evidence intactness, p95,
paired bootstrap, extraction/span metrics, linkage, graph parity, resource cost, and
adopt/retain/inconclusive verdicts.
- Acceptance gates: Split leakage and provenance checks pass; bootstrap seeds and item ledgers
replay; missing evidence refuses a verdict; metrics have positive/negative fixtures.
- Documentation target: `docs/impl/current/evaluation-foundation.md`



### Corpus foundation -- `corpus-foundation`



#### implement-streaming-inventory

Build a content-addressed, restartable archive inventory with format, encoding, hash, and quarantine
metadata.

- Serves: `corpus-foundation` -- [Pipeline](../design/spec.md#pipeline)
- Agent status: CLEAR
- Dependencies: `implement-layered-configuration-and-path-safety`;
`establish-canonical-contract-registry`.
- User-visible outcome: The operator can inventory a multi-terabyte tree without loading it into RAM
and can see coverage, bytes, duplicates, and unsupported/encrypted inputs.
- Scope boundary: Read files and archive-member metadata only; no text extraction and no
modification of source files.
- Data and artifact paths: `$ARCHIVE_DIR` read-only; `$NORMALIZED_DIR/inventory/`;
`$RUNS_DIR/<run-id>/`; `src/arxiv_int/pipeline/inventory/`.
- Execution path: Stream directory entries, normalize relative-path metadata, detect MIME/encoding,
compute configurable quick and strong hashes once, enforce archive-bomb limits, shard by stable
id, and write atomic Parquet manifests.
- Acceptance gates: Network-free fixtures cover large/sparse files, links, permission errors,
renamed duplicates, nested archives, encrypted files, interruption, and resume; memory is bounded
independently of file count.
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
- Data and artifact paths: `$NORMALIZED_DIR/documents/`, `$NORMALIZED_DIR/spans/`,
`$NORMALIZED_DIR/quarantine/`, `src/arxiv_int/extraction/`, and representative format fixtures.
- Execution path: Run Tika as breadth baseline; route layout/table PDFs to Docling and scanned PDFs
to OCR; preserve tool versions, coordinates, raw hashes, and extraction quality; bound temp files,
child processes, timeouts, and decompression.
- Acceptance gates: The reviewed extraction fixture reports per-format text, table, and anchor
coverage; corrupt/encrypted/oversized inputs fail safely; repeated content hashes reuse outputs;
source files remain unchanged.
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
- Data and artifact paths: `$NORMALIZED_DIR/documents/`, `spans/`, `chunks/`, duplicate overlays,
`src/arxiv_int/pipeline/normalize/`, and `src/arxiv_int/pipeline/chunk/`.
- Execution path: Preserve original text; create NFC/casefold/search views; map
original-to-normalized offsets; detect language; run exact, normalized, MinHash/lexical, and
edition grouping; implement bounded structure/table/sentence chunkers with source breadcrumbs.
- Acceptance gates: Golden offsets and table headers survive chunking; unchanged input yields stable
ids; dedupe precision is measured on labels; no suppression occurs without an overlay; out-of-core
memory and shard-resume tests pass.
- Documentation target: `docs/impl/current/corpus-foundation.md`



### Pipeline control -- `pipeline-control`



#### implement-run-ledger-and-atomic-artifacts

Create run, stage, shard, lease, checkpoint, error, and artifact-manifest state with deterministic
reuse keys.

- Serves: `pipeline-control` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: `create-canonical-relational-schema`; `implement-streaming-inventory`.
- User-visible outcome: Every long operation has inspectable state and an interrupted shard resumes
or reuses prior valid output safely.
- Scope boundary: Implement generic control mechanics; stage-specific processing stays in its owning
capability.
- Data and artifact paths: `ctl.*` tables, `$RUNS_DIR/<run-id>/manifests/`,
`src/arxiv_int/pipeline/control/`, and `tests/pipeline/control/`.
- Execution path: Define fingerprints and state transitions, transaction/lease rules, atomic sibling
writes, output validation, bounded retry taxonomy, stale-lease recovery, and downstream
invalidation planning.
- Acceptance gates: Property/state-machine tests reject illegal transitions; crash injection proves
no partial output is accepted; unchanged rerun is a cache hit; forced retry creates a new attempt
without overwriting evidence.
- Documentation target: `docs/impl/current/pipeline-control.md`



#### implement-stage-dag-cli-and-make-targets

Build the dependency-aware stage registry, independent stage command, end-to-end runner, resume, and
status interfaces.

- Serves: `pipeline-control` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: `implement-run-ledger-and-atomic-artifacts`;
`implement-normalization-dedupe-and-chunking`.
- User-visible outcome: Operators can run one stage or a `--from`/`--to` dependency closure and
resume by run id through CLI or standardized Make targets.
- Scope boundary: Orchestrate in-process/local workers first; do not introduce Airflow, Prefect,
Celery, Redis, or Kubernetes.
- Data and artifact paths: `src/arxiv_int/cli.py`, `src/arxiv_int/pipeline/registry.py`, `Makefile`,
and `tests/pipeline/orchestration/`.
- Execution path: Register typed stages and dependencies; resolve parameters; validate required
upstream manifests; add pipeline/stage/status/resume/invalidate commands; keep Make wrappers thin.
- Acceptance gates: DAG, range, skip, invalid dependency, resume, force, and signal-handling tests
pass; CLI help lists defaults and precedence; end-to-end smoke produces the same manifests as
independent stages.
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
- Execution path: Adapt selfsuvis queued logging and timing patterns; add time/count-throttled
progress, heartbeats, psutil/NVML/disk/Postgres metrics, redaction filters, JSONL schema, and
final manifests.
- Acceptance gates: Concurrent-log tests produce intact lines; redaction fixtures remove secrets and
corpus text; stalled worker and ETA states are distinguishable; metric labels have bounded
cardinality.
- Documentation target: `docs/impl/current/pipeline-control.md`



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
and `docs/reference/russian-retrieval.md`.
- Execution path: Build comparable indexes on identical data; measure inflection, identifiers,
abbreviations, OCR noise, homoglyphs, e/yo variants, keyboard layout, transliteration, and
mixed-language cases; use paired bootstrap verdicts.
- Acceptance gates: One profile receives `adopt`, `retain baseline`, or `inconclusive`; final
metrics and costs cite immutable runs; profile changes name required reindex work.
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
- Data and artifact paths: `$NORMALIZED_DIR/embeddings/`, `search.embedding_profile`,
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
- Data and artifact paths: `$NORMALIZED_DIR/nlp/`, `ontology.term`, `configs/nlp/`,
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
- Data and artifact paths: `$NORMALIZED_DIR/mentions/`, `kg.mention`, `configs/nlp/ner/`, and
`$RUNS_DIR/<run-id>/evaluation/ner/`.
- Execution path: Measure Natasha/Slovnet or equivalent CPU baseline; compare GLiNER-style custom
labels on a bounded sample; calibrate thresholds per type; preserve overlapping mentions and
failure reasons.
- Acceptance gates: Per-type precision/recall and span-overlap metrics produce a declared profile;
high-impact low-precision types stay review-only; inference cost and fallback behavior fit the
resource budget.
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
- User-visible outcome: Relations, specifications, equipment, suppliers, dates, quantities, and
claims are queryable with exact source evidence and extraction provenance.
- Scope boundary: Insert `proposed` assertions only; no automatic truth acceptance and no ontology
axiom invention.
- Data and artifact paths: `$NORMALIZED_DIR/facts/`, `kg.fact`, `kg.fact_qualifier`,
`src/arxiv_int/extraction/facts/`, generated output schemas, and prompt packages.
- Execution path: Implement typed rule/table extractors; define JSON-schema LLM envelopes; retrieve
bounded evidence; validate source spans, types, units, model output, and one bounded repair; batch
and checkpoint by content hash.
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
`$NORMALIZED_DIR/fact-findings/`, and `src/arxiv_int/extraction/validation/`.
- Execution path: Add domain/range, typed literal, unit, functional relation, temporal, duplicate,
contradiction, and evidence checks; create immutable decision events and reversible active views.
- Acceptance gates: Synthetic and gold contradictions are found with measured precision; every
active status derives from an audit event; rejected/superseded facts retain evidence; rules are
versioned and replayable.
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
`$NORMALIZED_DIR/linkage/`, and `src/arxiv_int/identity/`.
- Execution path: Adapt the loc-lm-bench Splink 4/DuckDB seam; define blocking and comparison specs;
train/calibrate from reviewer labels; persist the model, thresholds, pair probabilities, and
cluster algorithm.
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
- Data and artifact paths: `$NORMALIZED_DIR/topics/`, `search.topic`, `search.topic_assignment`,
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
`implement-scalable-topic-discovery`.
- User-visible outcome: An operator can find evidence, inspect objects and facts, traverse
relations, and export cited equipment/supplier lists without writing SQL.
- Scope boundary: Read-only query/report boundary with limits; no public multi-user web product and
no hidden acceptance of proposed facts.
- Data and artifact paths: `src/arxiv_int/query/`, `src/arxiv_int/reporting/`,
`$RUNS_DIR/<run-id>/reports/`, and API/query tests.
- Execution path: Implement typed query objects, pagination, filters, review-state controls,
evidence expansion, report definitions, CSV/Parquet/HTML exports, and explain modes; constrain
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
- Dependencies: `build-search-graph-and-report-interfaces`;
`define-compose-profiles-and-operator-wrappers`.
- User-visible outcome: Local dashboards show pipeline progress, topics, entities, facts, conflicts,
and bounded graph views; AGE Viewer supports exploratory Cypher when enabled.
- Scope boundary: Provision read-only local tools; no internet exposure, corpus-bearing telemetry
export, or tool-owned source of truth.
- Data and artifact paths: `docker/grafana/`, `docker/age-viewer/`, Compose profiles, read-only
database role migrations, and screenshot/query smoke fixtures.
- Execution path: Provision PostgreSQL datasource and dashboards as code; create read-only views;
configure AGE Viewer; document loopback URLs and lifecycle; add health and bounded-query smoke
tests.
- Acceptance gates: Fresh profile start needs no manual datasource setup; read-only roles cannot
mutate canonical rows; dashboards load fixture data; graph profile absence degrades cleanly.
- Documentation target: `docs/impl/current/discovery-visualization.md`



### Evaluation and evidence -- `evaluation-evidence`



#### run-representative-scale-pilots

Measure storage amplification, throughput, memory, WAL/temp growth, retrieval quality, resume, and
rebuild on two progressively larger corpus slices.

- Serves: `evaluation-evidence` --
[Performance and scalability assumptions](../design/spec.md#performance-and-scalability-assumptions)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: All required Phase 0-4 tasks for the selected pilot path;
`create-evaluation-fixtures-and-metrics`; `approve-representative-corpus-and-gold`.
- User-visible outcome: A capacity plan predicts normalized, heap, lexical, vector, graph, WAL,
temp, backup, wall-time, and operator-review costs before the full archive runs.
- Scope boundary: Run only approved representative slices; do not authorize the full corpus or
extrapolate without uncertainty and format mix.
- Data and artifact paths: Approved `$ARCHIVE_DIR` slices, `$NORMALIZED_DIR`, `$PGDATA_DIR`,
`$RUNS_DIR/<run-id>/pilot/`, and generated capacity report.
- Execution path: Run 0.1-1% or 50-200 GB pilot, tune bounded parameters, then a larger partition;
inject interruption; measure extraction yield, dedupe, chunks, indexes, updates, reindex, vector
tiers, graph, and recovery.
- Acceptance gates: Both runs remain within declared resource safety margins; estimates include
uncertainty and concurrent-rebuild space; every failure and excluded format is counted; report
ends in authorize-next, resize/reconfigure, retain-subset, or stop.
- Documentation target: `docs/impl/current/evaluation.md`



#### audit-reuse-provenance-and-published-claims

Verify copied/adapted code attribution, artifact lineage, and every number or architectural claim
published in reports and current-state docs.

- Serves: `evaluation-evidence` -- [Reuse map](../design/spec.md#reuse-map)
- Agent status: CLEAR
- Dependencies: `create-evaluation-fixtures-and-metrics`; implementation tasks that adapt source
repositories.
- User-visible outcome: Reuse is legally and technically traceable, and a stale run cannot continue
to support a changed published claim.
- Scope boundary: Audit repository and generated evidence; do not invent missing benchmarks or
license interpretations.
- Data and artifact paths: `NOTICE`, `THIRD_PARTY.md`, dependency lock, source headers,
`ctl.artifact`, run manifests, and docs claim registry.
- Execution path: Record upstream revision/license for adapted code, verify notices, link published
metrics to run fields and content pins, and list invalidations caused by contract/model/profile
changes.
- Acceptance gates: License scanner and manual notice checklist pass; every published number
resolves to one immutable artifact field; orphan or stale claims fail CI.
- Documentation target: `docs/impl/current/evaluation.md`



### Operational recovery -- `operational-recovery`



#### harden-local-security-and-no-egress-mode

Enforce read-only input, loopback services, least-privilege roles, secret redaction, bounded paths,
container mounts, and a network-denied run mode.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: RUN NEEDED
- Dependencies: `define-compose-profiles-and-operator-wrappers`;
`create-canonical-relational-schema`; `implement-local-inference-adapters`.
- User-visible outcome: The local stack can process prepared inputs without unintended network
access or writable access to the archive.
- Scope boundary: Host-local hardening and verification; not a formal third-party penetration test
or multi-user internet deployment.
- Data and artifact paths: Compose security settings, database role migrations, `.env.example`,
`src/arxiv_int/security/`, and security integration fixtures.
- Execution path: Apply non-root/read-only mounts where supported, localhost ports, role separation,
URL/path allowlists, secret filters, image/model pin checks, and network-denied integration
profile.
- Acceptance gates: Prepared smoke succeeds with egress denied; archive write attempts fail; UI role
mutations fail; secrets/corpus snippets do not appear in logs; dependency/image scan findings are
triaged without suppressing gates.
- Documentation target: `docs/impl/current/operations.md`



#### implement-backup-restore-and-rebuild-runbook

Create and exercise backups for contracts/config, normalized artifacts, PostgreSQL, and projection
rebuild metadata.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: RUN NEEDED
- Dependencies: `implement-rebuildable-search-and-graph-projections`;
`harden-local-security-and-no-egress-mode`; `run-representative-scale-pilots` can use the first
pilot for the drill.
- User-visible outcome: A documented command sequence restores canonical state and validates or
rebuilds search and graph projections on a clean target path.
- Scope boundary: Single-host backup/restore and removable-disk workflow; no HA or enterprise
replica claim.
- Data and artifact paths: `scripts/backup/`, `scripts/restore/`, backup manifests outside
`$PGDATA_DIR`, `$RUNS_DIR/<run-id>/recovery/`, and `docs/guide/recovery.md`.
- Execution path: Capture extension/image/model ids, migrations and logical/physical backup,
normalized manifest snapshot, checksums, free-space requirements, restore into a new directory,
run contract/live-store checks, and rebuild disposable projections.
- Acceptance gates: Clean-target restore reproduces canonical counts/checksums and sampled queries;
missing/corrupt backup parts fail before mutation; recovery time/space are recorded; original data
remains untouched.
- Documentation target: `docs/impl/current/operations.md`



#### test-failure-and-capacity-boundaries

Exercise disk pressure, database restart, worker death, corrupt artifacts, model timeout, invalid
index, and stale lease behavior before full-corpus authorization.

- Serves: `operational-recovery` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: RUN NEEDED
- Dependencies: `implement-backup-restore-and-rebuild-runbook`;
`add-progress-logging-and-resource-telemetry`.
- User-visible outcome: Known failures stop safely, preserve evidence, and provide a tested
resume/rebuild action instead of corrupting state.
- Scope boundary: Controlled disposable fixtures and pilot paths only; no destructive testing
against the real archive or sole backup.
- Data and artifact paths: Disposable test volumes under `$NORMALIZED_DIR/test/`,
`$RUNS_DIR/<run-id>/failure-tests/`, and recovery fixtures.
- Execution path: Inject bounded failures at artifact write, COPY, index build, AGE projection,
model call, and shutdown boundaries; verify alerts, state transitions, cleanup plans, and
recovery.
- Acceptance gates: No accepted partial artifact or duplicate canonical row results; retries are
bounded; invalid indexes/projections never become active; capacity refusal occurs before
configured safety margin is consumed.
- Documentation target: `docs/impl/current/operations.md`



## Human-Assisted Tasks



### Corpus foundation -- `corpus-foundation`



#### approve-representative-corpus-and-gold

Select a legally usable, distribution-representative corpus slice and adjudicate the gold
extraction, dedupe, Russian query, entity, fact, ontology, and report samples.

- Serves: `corpus-foundation` -- [Evaluation datasets](../design/spec.md#evaluation-datasets)
- Agent status: BLOCKED BY HUMAN
- Dependencies: Inventory summary from `implement-streaming-inventory`; draft fixture tooling from
`create-evaluation-fixtures-and-metrics`.
- User-visible outcome: Expensive model/store decisions are evaluated on the archive's real formats,
languages, noise, and business questions rather than synthetic convenience data.
- Scope boundary: Human selects and reviews bounded samples and confirms permission to process them;
no full-corpus authorization.
- Data and artifact paths: Private approved archive slice, local review ledgers under
`$RUNS_DIR/<run-id>/review/`, and frozen manifests without copied private text in Git.
- Execution path: Produce stratified candidate manifests and draft labels; human reviews source
spans, duplicate groups, queries, entities, facts, ontology constraints, equipment, and suppliers;
seal tuning/final splits.
- Acceptance gates: Coverage across major bytes/file types/languages and high-value questions is
documented; reviewer decisions and disagreements are recorded; final split remains unopened for
tuning.
- Documentation target: `docs/impl/current/evaluation.md`



### Knowledge extraction -- `knowledge-extraction`



#### approve-fact-review-and-publication-policy

Choose which fact types may be auto-accepted, remain proposed, or always require review, including
how conflicts affect equipment and supplier reports.

- Serves: `knowledge-extraction` --
[Canonical object and fact model](../design/spec.md#canonical-object-and-fact-model)
- Agent status: HUMAN-GATED
- Dependencies: Per-type final metrics from `implement-provenance-bearing-fact-extraction` and
conflict examples from `implement-fact-validation-conflict-and-review-overlays`.
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
- Dependencies: Held-out linkage curves from `implement-probabilistic-entity-resolution`; ontology
review package from `establish-versioned-ontology-assets`.
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



### Discovery and visualization -- `discovery-visualization`



#### accept-operator-discovery-workflows

Validate that a domain operator can complete representative topic, search, object/fact, graph,
equipment, and supplier workflows with understandable evidence and filters.

- Serves: `discovery-visualization` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: HUMAN-GATED
- Dependencies: `build-search-graph-and-report-interfaces`;
`provision-local-dashboards-and-age-viewer`; approved fact and identity policies.
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
approved discovery, fact, identity, and ontology policies.
- User-visible outcome: The multi-terabyte run begins with an explicit disk/time/risk budget and
selected lexical/vector/graph/model profiles, or is intentionally limited.
- Scope boundary: Authorization only; it does not weaken safety margins or imply cloud/HA scope.
- Data and artifact paths: Pilot capacity report, immutable profile ids, backup location,
`$RUNS_DIR/<run-id>/authorization/decision.yaml`.
- Execution path: Review forecast ranges, free space, expected duration, unsupported bytes,
energy/review costs, recovery time, and negative-result alternatives; record authorize-next,
resize/reconfigure, subset-only, or stop.
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
- User-visible outcome: The owner knows what is backed up, what is rebuildable, how long recovery
takes, and which local risks remain accepted.
- Scope boundary: Owner acceptance of the documented single-host posture; not a certification of
high availability, enterprise support, or physical security.
- Data and artifact paths: Recovery report, security checklist, backup inventory, retention policy,
and local acceptance decision.
- Execution path: Observe restore and sampled query parity; review ports, roles, mounts, secrets,
model/image provenance, backup separation, retention, and emergency stop/restart commands; record
residual risks.
- Acceptance gates: Restore evidence and residual-risk list are signed off or rejected; rejected
items return to the owning capability; Community ParadeDB HA limitations remain explicit.
- Documentation target: `docs/impl/current/operations.md`



## Plan maintenance rules

At each task completion transition:

1. Run `make plan-status` before and after the change.
2. Record available behavior, modules, commands, tests, and measured results in the narrowest
  current-state page.
3. Remove the finished task from this forward plan; retain only genuine residual work.
4. Mark a capability `shipped` in the specification only when current-state documentation and its
  evaluation exist. A shipped capability may retain explicitly optional refinements.
5. Run `make lint-spec-plan`, `make lint-doc-links`, and `make ci`.
6. Inspect repository and runtime state; stop processes started by tests unless they are the
  requested persistent service, and retain run evidence under configured data paths.

New capabilities return to the specification first: state the operator problem, behavior, boundary,
evaluation, and valid negative result; register the capability; then add tasks in registry order.
