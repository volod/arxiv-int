# Pipeline Control

Typed stage, source, and artifact references, a generic run ledger, serialized progress
logging with bounded resource telemetry, a fixture-first DAG CLI, a registered preflight
readability worker, a read-only pre-run forecast, profile-declared knowledge-base publication,
read-only stage artifact inspection, incremental source reconciliation, two-phase stale prune,
and read-only citation/source location lookup are available. Concrete corpus stages through `chunk`
are registered, as is `load-lexical`
([lexical retrieval](lexical-retrieval.md)); classification and later investigation stages remain
[planned](../plan.md#archive-classification----archive-classification).

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
[record 0051](../records/0051-pipeline-implement-evidence-and-source-location-lookup.md),
[record 0053](../records/0053-pipeline-prove-pipeline-control-on-provided-archive.md),
[checkpoint 0054](../records/0054-pipeline-review-control-integration-boundaries.md),
[repair 0055](../records/0055-pipeline-repair-source-reconciliation-and-prune-safety.md), and
[record 0056](../records/0056-pipeline-reprove-pipeline-control-after-reconciliation-repair.md), and
[record 0058](../records/0058-pipeline-bind-real-owned-stage-fingerprints.md),
[record 0059](../records/0059-pipeline-bound-archive-snapshot-hashing.md),
[checkpoint 0063](../records/0063-corpus-review-corpus-and-control-integrity.md), and
[repair 0064](../records/0064-corpus-repair-corpus-stage-identity-and-source-offsets.md).

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

Polars document preparation uses this `StageContext` / `StageResult` / `DatasetRef` shape. The
planned evaluation runner will use it once it consumes actual upstream outputs.

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

Stage identities now read actual assets through `pipeline.control.owned.owned_sources()` and
`owned_fingerprints()` before every reuse lookup. `StageSpec` declares the consumed `contracts`
(registry keys; `validators` also imply contracts), additional `code_paths` relative to the
installed `arxiv_int` package, `dependency_packages` (uv package names), and dbt asset paths relative
to the authored dbt project. Existing overlay-or-packaged resource resolution applies. Missing
contracts, generated schemas, catalogs, declared paths or locked dependencies fail before reuse;
there is no placeholder fallback. Moving an unchanged asset tree leaves its identity unchanged.

| Owned field | Source |
| --- | --- |
| `code_fingerprint` | Bytes of the shared module set, the runner source file and declared `code_paths`; the shared set covers control/DAG/run/quality/interfaces plus the contract catalog, generation and SQLAlchemy binding, feature gating, package metadata, stage paths, resource resolution, runtime config/containment and the source-set snapshot walker, because every stage executes them; stage declaration modules are excluded from the shared set because their selected values are hashed separately |
| `dependency_fingerprint` | Installed distribution name/version and selected requirement metadata, Python version, uv lock format and selected package records with transitive dependencies; PyYAML is shared, validators add Pandera/Polars, real dbt models add dbt Core/Postgres |
| `contract_fingerprint` | Selected `FileRegistry` entries plus their referenced ODCS and mapping file bytes |
| `schema_fingerprint` | Selected generated JSON Schema, Parquet, Avro, PostgreSQL (including extension DDL) and Pydantic schemas |
| `tool_fingerprint` | Frozen `StageSpec.tools` mapping of tool names to pinned versions or content digests |
| `model_fingerprint` | Frozen `StageSpec.models` mapping of model names to immutable revisions or content digests |
| `prompt_fingerprint` | Frozen `StageSpec.prompts` mapping of prompt names to content digests or immutable versions |
| `configuration_fingerprint` | Existing frozen run configuration digest, unchanged |
| `validation_catalog_fingerprint` | Selected validators' `generated/quality/<contract>.rules.json` bytes and shared Pandera rule-engine code |
| `dbt_model_fingerprint` | Declared `dbt_models` files plus shared `dbt_project.yml` and macros when models are declared |
| `dbt_input_fingerprint` | Existing `dbt_select`, declared `dbt_inputs`, selected contracts' generated dbt YAML and their consumed table definitions in the combined `generated/dbt/sources.yml` |
| `dbt_rule_fingerprint` | Declared `dbt_rules` files, including model test YAML and singular tests, plus the selected generated source/test definitions |

File identities use sorted relative names and raw-byte SHA-256 through the existing bounded reader.
Each field is SHA-256 over canonical JSON containing stage name, field name and its source values.
An empty declaration means the stage uses no asset of that kind; its digest remains specific to that
stage and field. Fixture stages declare their actual runner, feature and outcome as tool values;
unused model/prompt sets are empty. `with_runner()` preserves all declarations. Old placeholder
identities intentionally miss once; accepted artifacts remain intact.

Stage owners declare the complete asset dependency set, including helper modules, packaged data
assets, upstream dbt models and source/test YAML used by the selected transformation.
`tests/pipeline/dag/test_stage_declarations.py` enforces this: it walks the transitive first-party
import closure of each registered runner and fails when a stage executes a module it does not own,
so an incomplete declaration cannot silently reuse stale artifacts. Declarations stay per-file where
the dependency is narrow, so an inventory-only edit does not recompute chunking. A module reached
only through a runtime string import is outside that closure and still needs a manual declaration.
This binder does not interpret Jinja or implement another dbt selector engine. Declare shared
files only where they are consumed; shared project/macro edits affect every declared dbt
producer. The existing fixture quality adapter
uses synthetic dbt selections without real models. Real producer tasks must bind actual model,
input and rule paths when replacing it. Tool/model/prompt declarations must contain public immutable
identities, never credentials. Hashing these declarations imports no backend or model.

The lock comes from the requested project; disposable resource overlays without a project/lock use
the editable distribution checkout. A wheel deployment supplies its workspace `uv.lock`; a missing
lock in a project fails closed. Selected package records include all locked platform/extra variants
conservatively. Unrelated package pins and documentation edits leave stage identities unchanged.
Additional runtime dependencies belong in `dependency_packages`; changing an owned dependency,
contract, rule, dbt asset or declared tool/model/prompt changes the producer key and propagates through
upstream keys to consumers. `keys_matching_owned_change()` and `stale_closure()` retain their existing
field-selection and consumer-edge behavior. An unchanged rerun validates artifacts with zero workers.

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
`ctl.artifact_pin`. Head is `0002`.
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

New production runs persist `source_drift_policy: inventory-stat-v1`. Creation and update stream
metadata without opening source contents or retaining the path set. The counted, order-independent
source-set fingerprint includes silo id, root-relative path, classification and stable stat fields;
it is a change detector, not content identity. Inventory computes strong content hashes and checks
stability across source reads. File/directory links, unreadable entries and traversal limits are
explicit; changed links therefore invalidate frozen contexts. Atime is excluded. Same-size edits
with restored mtime still change ctime and refuse stale runs. Reliable local filesystem metadata
and stable sources remain assumptions; this is not an atomic filesystem snapshot.

Existing `stat-v1` and `full-content-v1` contexts retain their earlier ordered content/metadata
policies and symlink treatment. Unknown policies or missing metadata evidence refuse load. Rebuild
preserves the frozen policy, and configuration drift checks are unchanged. See
[record 0059](../records/0059-pipeline-bound-archive-snapshot-hashing.md) for the legacy behavior and
[record 0060](../records/0060-corpus-implement-streaming-inventory.md) for the new source-set policy.

Production source-set scheduling invokes inventory once; its stable bucket partitions live inside
the stage. Fixture DAGs retain their content-shard behavior. Preflight and inventory execute real
source-declaration/containment checks, and inventory supplies completed contract and global-key
validation evidence. Unimplemented production boundaries continue to refuse publication.

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

The investigation profile still names unregistered later stages. `make pipeline` therefore fails
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
derived attempts. The [inventory adapter](corpus-foundation.md) loads verified source occurrences
into the existing `arxiv-int.source-manifest.v1` interface when no older delta manifest exists.
Links and unreadable inputs are explicit and prevent comparable removal decisions. This adapter
and the existing delta operations still materialize source occurrences in memory.

A scan hashes readable files per silo in bounded chunks without writing archive bytes, so peak
memory does not scale with file size. Incomplete, unreadable, or
unstable silos cannot emit removal tombstones, and they retract no active row either: the active
view drops a row only when every path supporting it lies in a silo both scans completed.
Diff kinds are add, content-change, path-rename,
and remove. A rename pairs a removal with an addition inside one silo only; a file that moves
between silos is an honest remove plus add, because occurrences and path events are silo-scoped.
Rename and change events carry `previous_silo_id`, and a removal carries `content_remains` when the
same bytes still exist elsewhere.
Path-only renames reuse the content-hash shard and do not invoke workers. Root-stage
reuse identity is the content-hash shard once `document_id` is bound; the forecast cache plan
walks those shards so a no-op rerun is a cache hit. Orchestration writes
`$RUNS_DIR/<run-id>/delta/{manifest,delta,tombstones}.json`. Invalidation writes
`$RUNS_DIR/<run-id>/invalidation/plan.json`. Rebuild writes
`$RUNS_DIR/<run-id>/rebuild/report.json` with payload checksums that strip generation tokens.
`pipeline update` diffs the saved previous manifest against the current scan before the DAG.
`pipeline rebuild` force-runs an isolated generation and records baseline match.

Last-occurrence tombstones retract derived rows whose content hash is gone. Shared remaining
paths, merge/split/review overlays, and content that still exists elsewhere stay; a removal that
is not the last occurrence leaves its content-hash shard live rather than stale, so a still-active
document's attempt never becomes prune-eligible. dbt
`stg_source_tombstones` and `int_active_documents` recompute the set-based active view from
`ctl.source_tombstone`. Typed SQLAlchemy writers live in
`arxiv_int.pipeline.reconcile.postgres` and `tables`; the package initializer does not import
SQLAlchemy. Required quality checks still precede every active-pointer switch.

Prune is two-phase. Dry-run ids land under `$RUNS_DIR/prune-plans/` with a copy under the latest
`$RUNS_DIR/<run-id>/prune/`. Apply rechecks the fingerprint and refuses active generations,
pins, `review/`, `rollback/`, decision or move ledgers, backups, and the sole recovery copy.
Superseded attempt directories become eligible once a live generation exists. Apply checks every
listed directory for protection, root containment and symlinks before removing anything, so a
refusal leaves each tree whole and deletion never follows a link out of `RUNS_DIR`. Apply retains
checksums under `$RUNS_DIR/pruned/` and compact lineage; it never deletes archive sources. The
prune event records measured `bytes_removed` alongside `directories_removed`.

## Integration coverage

Pipeline control is exercised directly through tests under `tests/pipeline/`. They cover cache-hit
replay, resume, add/change/rename/remove reconciliation, source retraction, invalidation, rebuild,
forecast refusal, and protected prune behavior against isolated fixture roots. The earlier bounded
archive-copy scenario in records [0053](../records/0053-pipeline-prove-pipeline-control-on-provided-archive.md)
and [0056](../records/0056-pipeline-reprove-pipeline-control-after-reconciliation-repair.md) was a
milestone experiment over a fixture DAG. Its production scenario and publication modules were
retired by [record 0069](../records/0069-govern-retire-milestone-evaluation-scaffolding.md); they did
not validate the later corpus stages.

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

Each ledger row is bound to the attempt directory it names. A retried stage therefore reports its
accepted attempt with the ledger status and cache decision, and each superseded attempt directory
with its own attempt number and an `unknown` status, because no ledger row claims it. A ledger row
whose tree is unreadable still appears with its recorded fields and a placeholder path.

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
and the 2.5-4.0 amplification envelope live in
`src/arxiv_int/resources/configs/capacity/envelope.json` (schema
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
an incomplete scan that retracts no active row, a non-last-occurrence removal that keeps its shard
live, a move between silos that is not one rename, same-silo rename preference, chunked hashing of
large files,
shared merge/split evidence, rebuild checksum parity, quality-gated activation, dbt source/ref
lineage, and revision `0001` reconcile alignment. Prune tests in `tests/pipeline/prune/` cover
sole-recovery refusal, protected kinds, refusal of a symlinked escape from the runs root, measured
removed bytes, and superseded-attempt deletion that leaves live cache
entries. Fixture coverage does not prove real-archive extraction quality or CUDA worker fit; the
separate corpus archive integration test covers the shipped ordinary corpus closure.

Checkpoint 0046 validates fixture publication and reuse, with live disposable SQL lease/crash checks
and a CUDA-host resource probe. Checkpoint 0054 reviews the producers accepted after 0046 -- inspection,
reconciliation, prune, package layout, evidence lookup and the frozen store revision -- and repair
0055 fixes the reconciliation and prune defects it found. The historical 0053/0056 scenario did not
cover a removal that is not the last occurrence; that behavior stays fixture-covered. Source link policy
is implemented by [streaming inventory](../records/0060-corpus-implement-streaming-inventory.md).
Checkpoint [0063](../records/0063-corpus-review-corpus-and-control-integrity.md) reviews the
integrated corpus and control milestone; repair
[0064](../records/0064-corpus-repair-corpus-stage-identity-and-source-offsets.md) completes the
executed-asset declarations, makes document-text reads and writes byte-exact, and binds each ledger
row to the attempt directory it names. Database activation for corpus artifacts stays with the
retrieval and classification round. The local lock is intentionally coarse; no review here
establishes parallel corpus throughput or power-loss recovery.
