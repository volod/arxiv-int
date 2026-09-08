# Pipeline Control

Typed stage, source, and artifact references, a generic run ledger, serialized progress
logging with bounded resource telemetry, a fixture-first DAG CLI, a registered preflight
readability worker, a read-only pre-run forecast, profile-declared knowledge-base publication,
read-only stage artifact inspection, incremental source reconciliation, two-phase stale prune,
read-only citation/source location lookup, and a provided-archive pipeline-control proof are
available. Concrete corpus
stages remain
[planned](../plan.md#pipeline-control----pipeline-control).

See [record 0040](../records/0040-pipeline-refactor-stage-and-artifact-interface-contracts.md),
[record 0041](../records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md),
[record 0042](../records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md),
[record 0043](../records/0043-pipeline-add-progress-logging-and-resource-telemetry.md),
[record 0044](../records/0044-pipeline-implement-evidence-based-pipeline-forecast.md), and
[record 0045](../records/0045-pipeline-implement-investigation-profile-and-output-manifest.md),
[checkpoint 0046](../records/0046-pipeline-review-pipeline-publication-and-reuse-boundaries.md),
[repair 0047](../records/0047-pipeline-repair-pipeline-publication-and-reuse-integrity.md),
[record 0048](../records/0048-pipeline-add-stage-artifact-inspection.md),
[record 0049](../records/0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md),
[record 0051](../records/0051-pipeline-implement-evidence-and-source-location-lookup.md), and
[record 0053](../records/0053-pipeline-prove-pipeline-control-on-provided-archive.md).

## Stage, source, and artifact seams

`src/arxiv_int/interfaces/` holds Protocol definitions and frozen value types with no optional
import. Adapters can be declared and faked before a backend stack is installed. Domain stages,
orchestration, and Pandera/dbt execution stay outside these modules.

| Type | Role |
| --- | --- |
| `SiloRoot` | Named archive root; a run may declare several silos |
| `SourceOccurrence` | Physical identity `(silo_id, relative_path, scan_id)` from the source-occurrence contract |
| `SourceAnchor` | Page/character, sheet/cell, bounding-box, and container/member coordinates |
| `DatasetRef` | Dataset, contract version, partition, and `generation_id` |
| `ValidationResultRef` | Quality-run pointer without importing Pandera |
| `TransformationRunRef` | dbt-run pointer without importing dbt |
| `StageContext` | Stage name, run id, generation id, silos, results root, and options |
| `StageResult` | Honest outcome plus output, validation, and transformation refs |
| `StageRunner` | One restartable stage over those values |
| `DocumentExtractor` | One backend from a readable path and occurrence to `ExtractedDocument` |
| `ArtifactStore` | Locate and publish one generation-bearing `DatasetRef` |

`StageOutcome` is `produced`, `partial`, `empty`, `failed`, or `not-selected`. Empty is the valid
negative when a shard has nothing to emit. Partial and failed results must not look complete.
`not-selected` records why an optional branch did not run. Cache-hit bookkeeping belongs to the
run ledger below, not this outcome set.

Occurrence identity does not collapse duplicate relative paths across silos or shared content
hashes. Member occurrences keep `container_path` and `member_path`; cell anchors keep sheet, range,
and optional row/column/bbox. Relative paths are silo-relative POSIX paths; absolute, parent, and
empty segments are refused. `StageContext.source_path()` joins a silo root without reading the
file.

`DatasetRef.logical_partition()` compares dataset, contract version, and partition without
generation. Distinct generations of one partition are different refs and must locate to different
paths. Partition and option maps are frozen after construction. A failed or not-run validation
cannot be `publishable`; only a transformation run with status `ok` can be `activatable`.

`EvaluateStage` and Polars document preparation use this `StageContext` / `StageResult` /
`DatasetRef` shape.

## Conditional feature requirements

`STAGE_FEATURES` maps each pipeline stage to a `StageFeatureSet` of required and conditional
groups. GPU is conditional on `embed` and `facts`; UI is conditional on `report`. Setup profile
requirements collect required groups only, so an investigation setup does not demand GPU or UI
when those branches are not selected. `make features` and `make features STAGE=embed` label
conditional groups.

Inventory still lists every group that a stage may activate. A missing required runner is
`UnregisteredStageError`. Optional stages (`embed`, `load-vector`, `graph`) stay `not-selected`
when the selected profile does not include them.

## Compatibility

These constructor and outcome changes are intentional. Existing in-tree callers were updated;
there is no silent alias for the previous fields.

| Previous | Current |
| --- | --- |
| `StageContext.archive_dir` | `silos: tuple[SiloRoot, ...]`; one archive is one named silo |
| `run_id` as the only generation token | required `generation_id`; it may equal `run_id` on a first generation |
| `StageOutcome` `completed` / `skipped` | `produced`; `skipped` is not an artifact outcome |
| `DatasetRef` without generation | required `generation_id` |
| `DocumentExtractor.extract(source)` | `extract(source, occurrence)`; anchors are typed, not metadata strings |
| GPU/UI listed as required stage extras | conditional on `embed`/`facts` and `report` |

`ExtractedDocument.metadata` remains for backend extras that are not occurrence identity or
coordinates. Inference and embedding protocols are unchanged.

## Run ledger and atomic artifacts

`src/arxiv_int/pipeline/control/` implements generic control mechanics. Domain stages still own
their workers. `arxiv_int.pipeline.control` (the package initializer) does not import SQLAlchemy;
bound Postgres access is `arxiv_int.pipeline.control.postgres`.

Reuse identity is `ReuseIdentity`: stage, version, shard id, parameters, input hashes, upstream
reuse keys, and every owned fingerprint in `OWNED_FINGERPRINT_FIELDS` (code, dependency, contract,
schema, tool, model, prompt, configuration, validation catalog, and dbt model, input, and rule).
`reuse_key()` is SHA-256 over that identity. A changed owned fingerprint selects matching shards,
then `stale_closure()` walks consumer edges.

Statuses for run, stage, and shard are `pending`, `running`, `succeeded`, `failed`, `quarantined`,
`superseded`, `stale`, and `pruned`. Leases move `acquired` to `released`, `expired`, or `failed`.
Manifests move `staging` to `accepted` or `rejected`. Illegal transitions raise
`IllegalTransitionError`. Transient retry codes are `timeout`, `lease-expired`, `connection`,
`busy`, and `interrupted`; permanent codes are `validation`, `quality`, `illegal-input`,
`checksum`, and `activation`. Default max transient attempts is 3.

`ShardExecutor.execute` reuses a succeeded or quarantined producer attempt when
`validate_attempt` accepts the tree; the worker is not invoked. A held reuse lease records a
`busy` failure without duplicating the worker. Blocking quality results fail the attempt before
the worker runs. Force retry and failed cache validation reserve a new attempt directory
exclusively, including when a fresh command has no in-memory attempt history.
Publication writes sibling `.name.tmp` files, renames payloads, then `os.replace` of
`manifest.json` last. A missing, mismatched, or extra-file tree is not accepted. Crash injection
after payload rename leaves an unusable tree; recovery produces a new attempt. Invalidation that
wins the race against a running shard leaves it `stale` instead of accepting it.

Layout: `$RUNS_DIR/<run-id>/manifests/<stage>/<shard>/attempt-<n>/`.

Activation requires at least one global quality check and successful validation/transform refs for
the exact producing generation. Stage publication retains checks and references in `quality.json`,
covered by the attempt manifest. Cache hits validate this evidence without repeating heavy work;
cross-run reuse retains the producer generation. Missing or malformed stage/quality evidence and
partial outcomes are cache misses. Partial stages are retried by resume. Warnings without blocking
findings quarantine the shard. Fixture checks are available only on the fixture profile by default;
production checks remain explicit not-run until concrete adapters supply them.

Local orchestration, invalidation and finalization share a reentrant filesystem lock under
`RUNS_DIR`; commands reload the reuse index while holding it. This deliberately serializes the
fixture control path across processes. Assumed upstream stages must match the frozen run's full
transitive identity, rather than whichever stage ran most recently. PostgreSQL lease acquisition
locks the reuse key even before a lease row exists. Expired holders cannot renew or publish;
worker interruption releases the lease and records a failed attempt.

Postgres `add_shard` assigns the next attempt under a transaction-scoped advisory lock. In-memory
and SQL ledgers share the same transition rules.

Alembic revision `0001` is frozen DDL for contract tables, HASH partitions including
`corpus.document_path_event`, staging clones, projection metadata, `ctl.run`, `stage_run`,
`shard_run`, `reuse_lease`, `checkpoint`, `shard_error`, `artifact_manifest`, `artifact_lineage`,
`resource_lease`, `ctl.stage_progress`, `ctl.source_tombstone`, `ctl.prune_event`, and
`ctl.artifact_pin`. Head is `0001`.
`ctl.resource_lease` exists for later
SQL writers; inference still appends JSONL. `0001` teardown remains refused. Complete current
overlays stamp `0001`. Partial catalogs are refused.

## DAG registry and operator commands

`src/arxiv_int/pipeline/` owns the typed registry, `--from`/`--to` planner, frozen run context, and
in-process orchestrator. There is no Airflow, Prefect, Celery, Redis, or Kubernetes scheduler.
Setup's `PROFILE_STAGES` / `STAGE_FEATURES` remain the feature/service requirement seam.

A run id is allocated as `run-<hex>` and never inherits Make's developer `RUN_ID=local` fallback.
`arxiv-int run create` and `make run-create` freeze secret-free configuration under
`$RUNS_DIR/<run-id>/run-context.json`. Later `stage`, `status`, and `resume` calls reuse that
context and refuse configuration drift or a changed archive snapshot. `pipeline update` clones the
frozen profile into a new generation that sees the current snapshot; `pipeline rebuild` allocates a
new generation and skips cache reuse.

| Command | Role |
| --- | --- |
| `arxiv-int run create` / `make run-create` | Unique run id; freeze `.env` profile and roots |
| `arxiv-int pipeline forecast` / `make forecast RUN_ID=...` | Read-only time, storage, and free-space decision |
| `arxiv-int stage STAGE --run-id RUN_ID` / `make stage STAGE=... RUN_ID=...` | One stage; required upstream manifests must already validate |
| `arxiv-int pipeline run` / `make pipeline` | Create a run, preflight, forecast, execute the DAG, then finalize |
| `arxiv-int pipeline update` / `make update` | New generation for archive deltas; unchanged reuse keys cache-hit |
| `arxiv-int pipeline rebuild` / `make rebuild` | Fresh generation without cache reuse |
| `arxiv-int pipeline invalidate STAGE --run-id RUN_ID` / `make invalidate` | Logical stale closure; no deletes |
| `arxiv-int run status RUN_ID` / `make run-status RUN_ID=...` | Per-stage ledger status plus latest progress snapshot |
| `arxiv-int inspect RUN_ID\|DATASET\|latest` / `make inspect RUN_ID=...` | Read-only row/byte, partition, quality, and failure summary |
| `arxiv-int archive locate DOCUMENT_ID` / `make archive-locate DOCUMENT_ID=...` | Read-only citation to original and current source locations |
| `arxiv-int archive import-ledger PATH` | Idempotent import of a portable path-event ledger |
| `arxiv-int run artifacts RUN_ID` | Alias of inspect for one frozen run |
| `arxiv-int run resume RUN_ID` / `make resume RUN_ID=...` | Continue after halt or SIGINT |
| `arxiv-int run finalize RUN_ID` / `make run-finalize RUN_ID=...` | Seal `knowledge-base.json`; activate only a complete profile |
| `arxiv-int artifacts prune --stale` / `make prune` | Dry-run stale derived attempts; `--apply --plan PLAN_ID` is separate |

CLI values override process environment, then `.env`, then documented defaults. Make does not pass
hardcoded `--profile investigation` or `--run-id local` on `pipeline` / `run-create`. `STAGE` and
`RUN_ID` for atomic commands must be the created run id.

The investigation profile still names unregistered corpus stages. `make pipeline` therefore fails
explicitly until those runners ship. Fixture DAGs in `tests/pipeline/dag/` cover range,
skip, invalid dependency, aggregate versus atomic equivalence, failure halt, resume, force,
invalidate, update, rebuild, prune dry-run, quality not-run/fail, and signal cancel. Declared
Pandera validators and dbt selections run at producer boundaries through `QualityBoundary`; failed
or not-run checks halt downstream work. The directory-to-report gate waits on concrete stages.

`stage STAGE=preflight` is a registered readability worker. It does not load models or write
archive bytes. Aggregate commands still run the same archive-readability handler before forecast.

## Incremental reconciliation and stale pruning

`src/arxiv_int/pipeline/reconcile/` diffs complete comparable source manifests and retracts stale
active views. `src/arxiv_int/pipeline/prune/` plans and applies physical deletion of unreferenced
derived attempts. Inventory remains
[planned](../plan.md#implement-streaming-inventory); the reconciler consumes the same
`arxiv-int.source-manifest.v1` contract that inventory will later emit.

A scan hashes readable files per silo without writing archive bytes. Incomplete, unreadable, or
unstable silos cannot emit removal tombstones. Diff kinds are add, content-change, path-rename,
and remove. Path-only renames reuse the content-hash shard and do not invoke workers. Root-stage
reuse identity is the content-hash shard once `document_id` is bound; the forecast cache plan
walks those shards so a no-op rerun is a cache hit. Orchestration writes
`$RUNS_DIR/<run-id>/delta/{manifest,delta,tombstones}.json`. Invalidation writes
`$RUNS_DIR/<run-id>/invalidation/plan.json`. Rebuild writes
`$RUNS_DIR/<run-id>/rebuild/report.json` with payload checksums that strip generation tokens.
`pipeline update` diffs the saved previous manifest against the current scan before the DAG.
`pipeline rebuild` force-runs an isolated generation and records baseline match.

Last-occurrence tombstones retract derived rows whose content hash is gone. Shared remaining
paths, merge/split/review overlays, and content that still exists elsewhere stay. dbt
`stg_source_tombstones` and `int_active_documents` recompute the set-based active view from
`ctl.source_tombstone`. Typed SQLAlchemy writers live in
`arxiv_int.pipeline.reconcile.postgres` and `tables`; the package initializer does not import
SQLAlchemy. Required quality checks still precede every active-pointer switch.

Prune is two-phase. Dry-run ids land under `$RUNS_DIR/prune-plans/` with a copy under the latest
`$RUNS_DIR/<run-id>/prune/`. Apply rechecks the fingerprint and refuses active generations,
pins, `review/`, `rollback/`, decision or move ledgers, backups, and the sole recovery copy.
Superseded attempt directories become eligible once a live generation exists. Apply retains
checksums under `$RUNS_DIR/pruned/` and compact lineage; it never deletes archive sources.

## Provided-archive control proof

`make proof CAPABILITY=pipeline-control RUN_ID=...` copies a bounded file set from `ARCHIVE_DIR`
into `$RESULTS_DIR/proof-work/pipeline-control/<proof-id>/` and publishes
`$RESULTS_DIR/proofs/pipeline-control/<proof-id>/`. The copy is at most eight files, 4 MiB each,
and 16 MiB total. Add/change/rename/remove, fingerprint bump, rebuild, and prune-apply run only
on that copy. The supplied archive is not written. Then-usable stages are registered `preflight`
plus the fixture DAG; inventory and later corpus stages are not part of this proof.

The bundle is Git `no-export` (`git_bound: []`) with separate raw-proof and transformed-export
fingerprints. Required gates are zero workers on a no-op rerun, exact affected/unaffected shards
for each delta, tombstones and active rows, targeted code invalidation, simulated free-space
refusal before allocation, rebuild checksum parity, sole-recovery prune refusal, and an
unmodified source snapshot. Host proof `0053-host-2` is recorded in
[record 0053](../records/0053-pipeline-prove-pipeline-control-on-provided-archive.md).

## Stage artifact inspection

`src/arxiv_int/inspect/` summarizes what a normal stage already published. It does not rerun
workers, execute Pandera or dbt, write attempt trees, or treat a summary as proof acceptance.
`arxiv-int inspect RUN_ID` and `make inspect RUN_ID=...` require a created run id, not Make's
developer `local` fallback. `arxiv-int inspect latest` uses the newest `run-*` context.
`arxiv-int inspect DATASET` reads `$RESULTS_DIR/normalized/<dataset>/` and matching run outputs.
`--json` writes schema `arxiv-int.inspect.v1` to stdout; `--limit N` bounds partitions, quality
rows, lineage, and anchors. Explicit `--runs-dir` (and optional `--results-dir`) inspect a
published tree without requiring `ARCHIVE_DIR` or `PGDATA_DIR`. Unflagged operator inspect still
loads runtime configuration for those roots.

Each stage line reports status, honest outcome, attempt, cache-hit, bytes, retained row counts,
checksum validity, contract conformance, quarantines, and failures. Directories are
`$RUNS_DIR`-relative POSIX paths. Quality comes from attempt `quality.json` plus published
`$RUNS_DIR/<run-id>/quality/result.json`. Sanitized dbt lineage comes from quality
transformations or published `run_results.json`, never from a live transform. Empty, partial,
quarantined, failed, and schema-drifted trees still produce a stable summary. Inspection
rechecks checksums in place and leaves bytes unchanged.

## Evidence and source location lookup

`src/arxiv_int/query/evidence/` resolves content, fact, and report citations to physical sources
without a placement executor, live model/graph services, or archive writes. It reads a sealed
evidence catalog (`arxiv-int.evidence-catalog.v1`) of document rows, source occurrences, optional
citations, and path events. Document and occurrence objects are rows of the registered `documents`
and `source-occurrences` contracts. Path-event rows and portable ledger files
(`arxiv-int.path-event-ledger.v1`) are rows of `document-path-events`, the ODCS source of truth for
`corpus.document_path_event`. Alembic revision `0001` publishes that table. Portable codecs parse
those rows through the shared ODCS normalizer; they do not keep a parallel field list. Occurrences
join documents by `content_hash`; path events keep `document_id`. Unknown keys and missing required
contract fields are refused on import.

`arxiv-int archive locate DOCUMENT_ID` and `make archive-locate DOCUMENT_ID=...` are read-only.
`--kind fact|report` resolves those citation ids. `--json` writes schema
`arxiv-int.evidence-resolution.v1` to stdout. Explicit `--catalog` and `--ledger` skip operator
`ARCHIVE_DIR` / `PGDATA_DIR`. `--silo SILO_ID=ROOT` is the only filesystem access: it checks
silo-root containment and current hashes. Locations stay silo-relative POSIX paths. Duplicate
silos remain distinct occurrences. Nested members hash the container file, not a virtual member
path. Original occurrence rows are never rewritten; rename and copy events overlay current paths.
Missing, changed, and escaped-link files are explicit statuses. `arxiv-int archive import-ledger`
merges events by `event_id` and refuses conflicting payloads without rewriting a matching store.

## Pre-run forecast and resource refusal

`src/arxiv_int/pipeline/forecast/` predicts requested work, duration ranges, output and peak
storage, and free-space safety without loading models or writing production artifacts. Aggregate
`pipeline run` / `update` / `rebuild` call the same estimator and refusal handler as the atomic
command. `make forecast RUN_ID=...` requires a created run id and writes
`$RUNS_DIR/<run-id>/forecast/decision.json`. Standalone `arxiv-int pipeline forecast` allocates a
`forecast-<hex>` id, does not write `run-context.json`, and is not a production generation.

Inventory prefers a delta manifest, then an inventory manifest, then bounded directory metadata
sampling (no file contents). Cache hits come from the reuse index. Comparable telemetry, when
present, comes from prior `logs/observability-manifest.json` and `progress.jsonl`. Coefficients
and the 2.5-4.0 amplification envelope live in `src/arxiv_int/resources/configs/capacity/envelope.json` (schema
`arxiv-int.capacity.envelope.v1`). The decision schema is `arxiv-int.forecast.v1`.

Filesystem roots are inspected and grouped by device id so a shared disk is budgeted once. Cost
families map to one root each: normalized/artifacts to `RESULTS_DIR`; logs/staging/rollback to
`RUNS_DIR`; heap/indexes/vectors/graph/rebuild to `PGDATA_DIR`; WAL to `PG_WAL_DIR` or
`PGDATA_DIR`; temp to `TMP_DIR`. Backups stay zero unless the envelope sets a backup fraction.
The hard reserve is 1 GiB or 5% of the upper-bound peak, whichever is larger, and is not
bypassed. Archive organization is excluded (`excluded=archive-organization`).

Decisions are `ready`, `degraded`, `blocked`, or `unknown`. Zero-history, truncated sample, or
missing telemetry yields `degraded` with `low` confidence and conservative ranges, never an
invented point duration. A missing GPU for a `gpu_required` stage is `degraded`, not blocked. An
`unknown` large-stage estimate (input at least 50 GiB and no comparable telemetry) rolls up to
`blocked` and asks for a bounded pilot. Inaccessible output paths or upper-bound peak plus
reserve shortfalls exit 3 (`ForecastRefusedError`) before heavy work. Rotational database or
scratch devices widen the time range and lower confidence.

The orchestrator requires a covering forecast whose config fingerprint, source snapshot,
envelope, plan coverage, and per-stage cache-hit flags match the current run. Live free bytes
are rechecked, not fingerprinted. Before each stage, `space_guard` re-reads free space and
blocks the next allocation when a device falls below peak plus reserve; the stage worker is not
invoked. A stale or missing forecast raises `StaleForecastError` (also exit 3). Forced runs budget every
worker as uncached. Before an atomic forced stage, use
`make forecast RUN_ID=... FORCE=1` or `arxiv-int pipeline forecast --run-id RUN_ID --force`.
A forecast that assumed cache hits cannot authorize forced recomputation.

## Investigation profiles and knowledge-base publication

`src/arxiv_int/pipeline/publish/` seals one generation from the requested profile. Committed
overlays live in `src/arxiv_int/resources/configs/pipeline/investigation.json` and `lexical.json` (schema
`arxiv-int.pipeline.profile.v1`). The knowledge-base document is `arxiv-int.knowledge-base.v1`.
Setup's `PROFILE_STAGES` / `OPTIONAL_STAGES` remain the requirement seam; Python defaults and
committed JSON must not drift (`check_profile_alignment()` / `check_schema_drift()`). The
fixture profile (`alpha` / `beta` / `gamma`, optional `omega`) is Python-only.

Investigation required families are inventory, documents (`chunk`), classification, lexical,
topics, identities, ontology, facts, domain, evaluation, anomalies, and report. Optional
families are vectors (`load-vector`) and graph. Anomalies currently map to `evaluate` until an
anomalies stage exists. Lexical omits topics, identities, ontology, facts, domain, vectors, and
graph, so it is a visibly smaller profile.

Aggregate `pipeline run` / `update` / `rebuild` call the same create, archive-readability
preflight, forecast, stage, and finalize handlers as the atomic chain. Atomic `stage` does not
auto-finalize. `arxiv-int run finalize RUN_ID` and `make run-finalize RUN_ID=...` require a
created run id. Unreadable archive silos raise `PreflightRefusedError` (exit 3) before forecast.

Finalization rechecks the current reuse index, complete artifact trees, quality evidence and
required stage selection. A stale, missing or damaged artifact cannot become active just because
`status.json` still says it succeeded. Empty required families remain valid complete outputs.

A succeeded profile writes `$RUNS_DIR/<run-id>/knowledge-base.json` and retains a matching manifest
and catalog under `$RUNS_DIR/<run-id>/publications/<fingerprint>/`. One atomic replacement of
`$RUNS_DIR/active-generation.json` selects both snapshot paths. Readers follow its `manifest` and
`catalog` fields; the former root-level `active-catalog.json` is no longer an authority. Catalogs
remain a fixture stand-in for database publication. The disposable SQL ledger is tested separately;
this does not claim a production database activation adapter.

Partial, failed, blocked and interrupted runs write diagnostics without replacing the last complete
pointer. `write_report()` cannot activate a generation. Logical exits are succeeded 0, partial 2,
failed 1, blocked 3 and interrupted 130; activation refusal returns failure. A missing `status.json`
returns the DAG fallback exit. All five publication crash points are checked: `after-manifest`,
`after-catalog-write`, `after-catalog-replace`, `after-generation-write` and
`after-generation-replace`. Before the active-pointer replacement, readers retain the prior matching
snapshot; afterward they see the new matching snapshot. Finalize retries reuse the same completed
attempts. Cleanup removes only publication-owned temp files under the control lock, preserving worker
staging. A default investigation run still refuses unregistered corpus stages.

## Progress logging and resource telemetry

`src/arxiv_int/observability/` serializes operator logs and throttled progress for every
orchestrated stage. Concurrent records pass through one bounded `queue.Queue`; newest records
drop when the queue is full, and shutdown inserts a sentinel even under saturation. A redacting
filter strips secrets, prompts, absolute paths, and long quoted corpus text. Metric labels are
only `stage`, `event`, `worker_state`, `device`, and `failure_class`.

Each stage writes under `$RUNS_DIR/<run-id>/logs/`: `console.log`, `events.jsonl`,
`progress.jsonl`, `latest.json`, and `observability-manifest.json`. Console lines include UTC
timestamp, run/stage/shard token, processed/remaining, bytes, throughput, ETA, errors, worker
state, and CPU/RAM/disk/GPU pressure. Terminal observability manifests retain the actual stage
outcome; partial and failed results mark progress failed. Worker states are `running`, `slow`
(fresh heartbeat, large ETA), `stalled` (heartbeat timeout), `completed`, and `failed`. Heartbeats
are time-throttled on a background pump so long stages keep reporting without a worker callback.
`LOG_FORMAT` and `PROGRESS_INTERVAL_SEC` come from frozen secret-free run configuration (defaults
`console+jsonl` and `30`).

Host samples reuse inference `nvidia-smi` plus `/proc` CPU/RAM and `shutil.disk_usage`. Optional
psutil is used when installed; it is not a base dependency. Postgres size/WAL is an injectable
callback. The same bounded fields are appended as `pipeline.resource` telemetry JSONL.
`PostgresProgressStore` inserts `ctl.stage_progress` and can touch `ctl.stage_run.updated_at`
when a caller supplies an engine. Grafana `pipeline-progress.json` and `resource-pressure.json`
query that table through datasource `arxiv-int-postgres`. Topic/entity/fact dashboards remain
planned with discovery visualization.

## Tests and limits

`tests/interfaces/` covers protocol conformance, duplicate paths across silos, cell/member
anchors, distinct generations, honest partial/empty/failed/not-selected outcomes, and the rule
that interface modules do not import optional heavy stacks. Feature-catalog tests cover
conditional GPU/UI groups. `tests/pipeline/control/` covers illegal transitions, crash injection,
cache hits, corrupt-cache rerun, concurrent leases, quality skip, owned-fingerprint stale closure,
invalidation during produce, force retry, and in-memory isolation from SQLAlchemy. Live ledger
behavior is in `tests/integration/postgres/test_run_ledger.py`. Fixture DAG tests live in
`tests/pipeline/dag/`. Observability tests in `tests/observability/` cover intact
concurrent log lines, queue overload/shutdown, redaction, stalled versus slow ETA, bounded
metric labels, and revision `0001` ledger/progress alignment. Forecast tests in
`tests/pipeline/forecast/` cover
zero-history ranges, replay, device dedup, cache hits, inaccessible/shortfall refusal, stale
config, missing/uncovered forecasts, simulated free-space loss without partial manifests,
inventory/delta versus sample, schema drift, CLI standalone versus `--run-id`, Make dry-run, and
optional-import isolation. Publication tests in `tests/pipeline/publish/` cover setup/profile
alignment, lexical subset, schema drift, complete activate, valid-empty succeed, partial cannot
replace complete, failed diagnostic without activation, unreadable preflight, interrupted 130
plus resume then activate, stale upstream, crash after-manifest, crash after-catalog-write plus
orphan reconcile, report cannot activate, aggregate versus atomic logical equivalence, CLI/Make
finalize, and optional-import isolation. Inspection tests in `tests/inspect/` cover empty,
partial, quarantined, schema-drifted, and failed summaries, checksum stability, secret/path
redaction, latest and lake lookup, bounded anchors, evaluate-stage artifacts, CLI/Make wrappers,
and optional-import isolation. Evidence lookup tests in `tests/query/evidence/` cover duplicate
silos, sheet/cell and nested-member anchors, path-only renames, missing/changed files, escaping
links, ambiguous citations, copy extras, repeated ledger import, contract-column refusal, CLI/Make
wrappers, and
optional-import isolation. Reconciliation tests in `tests/pipeline/reconcile/` cover no-op
updates, additions, path-only renames, change/remove retraction, partial-scan withholding,
shared merge/split evidence, rebuild checksum parity, quality-gated activation, dbt source/ref
lineage, and revision `0001` reconcile alignment. Prune tests in `tests/pipeline/prune/` cover
sole-recovery refusal, protected kinds, and superseded-attempt deletion that leaves live cache
entries. Pipeline-control proof tests in `tests/evaluation/proof/test_pipeline_control.py` cover
the named gates, dispatcher/CLI publish and check, unreadable archives, copy budgets, and
path-free no-export bundles. Fixtures do not prove real-archive extraction quality or
CUDA worker fit.

Checkpoint 0046 validates fixture publication and reuse, with live disposable SQL lease/crash checks
and a CUDA-host resource probe. Record 0053 publishes the provided-archive control proof for
then-usable stages. Concrete producer fingerprints, validators, database activation and remaining
corpus stages stay with the
[corpus/control checkpoint](../plan.md#review-corpus-and-control-integrity). The local lock is
intentionally coarse; the review does not establish parallel corpus throughput or power-loss recovery.
