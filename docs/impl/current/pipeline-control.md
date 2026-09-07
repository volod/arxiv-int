# Pipeline Control

Typed stage, source, and artifact references are available, and generic run/stage/shard control
exists. DAG CLI, forecast, and publication assembly remain
[planned](../plan.md#pipeline-control----pipeline-control).

See [record 0040](../records/0040-pipeline-refactor-stage-and-artifact-interface-contracts.md) and
[record 0041](../records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md).

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

Inventory still lists every group that a stage may activate. Downstream DAG work decides whether
a missing conditional group becomes `not-selected` or a hard refusal.

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
`validate_attempt` accepts the tree; the worker is not invoked. Force retry allocates
`next_attempt` and a new directory. Publication writes sibling `.name.tmp` files, renames payloads,
then `os.replace` of `manifest.json` last. A missing or mismatched manifest is not accepted.
Crash injection after payload rename leaves an unusable tree; recovery produces a new attempt.

Layout: `$RUNS_DIR/<run-id>/manifests/<stage>/<shard>/attempt-<n>/`.

Activation requires at least one global quality check and successful validation/transform refs for
the exact generation. Warnings without blocking findings quarantine the shard.

Alembic revision `0002` is frozen DDL for `ctl.run`, `stage_run`, `shard_run`, `reuse_lease`,
`checkpoint`, `shard_error`, `artifact_manifest`, `artifact_lineage`, and `resource_lease`. Head is
`0002`. `ctl.resource_lease` exists for later SQL writers; inference still appends JSONL. `0002`
downgrade drops ledger tables only; `0001` teardown remains refused.

## Tests and limits

`tests/interfaces/` covers protocol conformance, duplicate paths across silos, cell/member
anchors, distinct generations, honest partial/empty/failed/not-selected outcomes, and the rule
that interface modules do not import optional heavy stacks. Feature-catalog tests cover
conditional GPU/UI groups. `tests/pipeline/control/` covers illegal transitions, crash injection,
cache hits, owned-fingerprint stale closure, force retry, and in-memory isolation from SQLAlchemy.
Fixtures do not prove real-archive extraction quality, CUDA fit, or DAG CLI behavior. Forecast and
publication activation remain planned.
