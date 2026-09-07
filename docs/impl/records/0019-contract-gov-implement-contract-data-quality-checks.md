# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-contract-data-quality-checks` /
  `contract-governance` / `review-foundation-and-store-boundaries`
- State: accepted
- Source: `docs/impl/plan.md#implement-contract-data-quality-checks`. Working tree also contains
  accepted store-image and migration work that this task does not absorb.
- Initial count: 83 tasks (72 agent, 11 human); next agent task
  `implement-contract-data-quality-checks`.
- Accepted task:

```markdown
#### implement-contract-data-quality-checks

Make contract conformance executable on dataset contents with bounded, descriptive validation
results shared by all producers.

- Serves: `contract-governance` -- [Data quality](../design/spec.md#data-transformations-and-quality)
- Agent status: CLEAR
- Audit inputs: [AUD-data-engineering-tooling-3](records/0015-govern-review-data-engineering-tooling.md#audit-handoff).
- Dependencies: [Contract schema and migration tooling](records/0017-contract-gov-refactor-contract-schema-and-migration-tooling.md).
- User-visible outcome: Invalid batches and missing required checks have inspectable reasons and
cannot be represented as publishable validated output.
- Scope boundary: Implement reusable Pandera/Polars checks, generated dbt source/test YAML, and typed
results; reuse domain/SHACL rules. Producer tasks attach their semantics, pipeline tasks enforce
activation, and `implement-dbt-transformation-foundation` executes whole-relation dbt checks.
- Data and artifact paths: `src/arxiv_int/data_quality/`, shared contract generation,
`contracts/generated/{quality,dbt}/`, `tests/data_quality/`, feature/dependency/Make files,
`$DATA_DIR/data-quality/<run-id>/`, and `$RUNS_DIR/<run-id>/quality/` for published evidence.
- Execution path: Generate strict schema/type/nullability/value/key checks from the same normalized
ODCS fields; map supported rules to Pandera and dbt with stable ids. Validate materialized bounded
Polars batches via PyArrow IO; distinguish batch versus whole-snapshot rules and delegate global
keys/relationships to declared dbt or disk-backed checks. Emit rule/input/tool fingerprints,
scope/count/severity/status and redacted failure references through typed results. Keep data-quality
dependencies optional and avoid importing them into CLI/core paths that do not need them.
- Acceptance gates: Fixtures cover valid/invalid types, nulls, decimal/unit cases, unknown rules,
missing checks, duplicate keys split across batches, broken relationships, empty and insufficient
data, and bounded failure samples. LazyFrame schema-only validation cannot count as data validation;
unexecuted global checks cannot pass. Generation is stable and retains descriptions; outputs are
secret-free and memory is bounded by declared batch/spill limits. `make ci` and `make quality` pass;
fixture validation makes no held-out model or real-archive quality claim.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Shared contract-derived quality catalogs compile from the same `NormalizedTable` fields as
SQLAlchemy. Batch rules run through Pandera/Polars on eager frames; per-kind handlers live in
`batch_kinds.py` so dispatch stays in `batch_eval.py`. Snapshot uniqueness and relationships are
declared as dbt YAML and executed by a disk-backed Polars adapter. Typed
`DatasetValidationResult` values are publishable only after required data checks executed and
passed. LazyFrame schema-only validation, missing related datasets, skipped snapshot checks, and
unattached semantic rules stay `not-run` or failed and cannot look publishable. Number columns skip
Pandera Decimal schema construction and use a dedicated Polars decimal/type path. Unit tests under
`tests/stores/` cover 0018 probe helpers that the optional Docker probe gate does not run; they do
not absorb store-image scope.

Optional extras: `data-quality` (`pandera[polars]==0.28.0`) and Polars in `lake`. CLI/core paths
that do not validate data do not import them. Generation version `2.1.0` writes
`contracts/generated/{quality,dbt}/` into the existing pipeline. Operator entry:
`arxiv-int data-quality check` / `make data-quality`. Current state:
[contracts](../current/contracts.md).

Limitations: this adapter generates dbt YAML and runs disk-backed snapshot checks; it does not
execute dbt Core. Producers attach ontology/SHACL outcomes. Fixture validation makes no held-out
model or real-archive quality claim.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Valid/invalid types, nulls, decimal/unit, accepted values, bounded redacted samples | `tests/data_quality/test_batch_checks.py` | pass; fixtures only |
| Unknown quality engine/rule fail closed; descriptions retained | `tests/data_quality/test_rules.py` | pass |
| Duplicate keys split across batches; broken/missing relationships; unexecuted globals cannot pass | `tests/data_quality/test_snapshot.py` | pass; batch unique can pass while global unique fails |
| Empty and insufficient rows | `tests/data_quality/test_empty.py` | pass; min_rows undershoot is fail/not publishable |
| LazyFrame schema-only cannot count as data validation | `tests/data_quality/test_lazyframe.py` | pass; `publishable=False` |
| Missing semantic/SHACL attachments cannot pass | `tests/data_quality/test_semantic.py` | pass; adapters reuse ontology validators |
| Stable generation; secret-free IO; spill parquet under DATA_DIR | `tests/data_quality/test_generate.py`, `test_io.py`, `test_commands.py` | pass |
| Committed quality/dbt artifacts and golden fingerprints | `arxiv-int contracts generate` (192 files); `tests/contracts/test_generate_pipeline.py` | pass |
| `make ci` | `make ci` | pass; 596 passed, 1 skipped |
| `make quality` | `make quality` | pass; 596 passed, 1 skipped; coverage 90.22%; wheels built |
| Held-out model / real-archive quality | none | not-run; fixtures only |

Artifacts: `contracts/generated/quality/*.rules.json`, `contracts/generated/dbt/*.yml`,
`dbt/sources.yml`, `tests/contracts/golden/artifact-fingerprints.json`. Tool evidence lands under
`$DATA_DIR/data-quality/<run-id>/` and is not retained.

## Audit handoff

`none identified` for the reviewed scope: rule compilation, Pandera batch adapters, disk-backed
snapshot uniqueness/relationships, generated dbt YAML, typed publication gating, optional extras,
and CLI/Make entrypoints. Whole-relation dbt execution is recorded in
[0024](0024-store-implement-dbt-transformation-foundation.md).

## Close or resume

Every declared fixture gate passed. Current contracts, developer tooling, project foundation,
development guide, README, the record index, and `AUD-data-engineering-tooling-3` link this record.
The task block was removed from the plan; dependents
([Canonical relational schema](0021-store-create-canonical-relational-schema.md),
[dbt transformation foundation](0024-store-implement-dbt-transformation-foundation.md),
`create-evaluation-fixtures-and-metrics`) point at this record. `contract-governance` is shipped
in the capability registry; live migration and dbt execution remain with canonical-store.

Counts: before 83 tasks (72 agent, 11 human); after 82 tasks (71 agent, 11 human). Next agent
task after 0019: [Canonical relational schema](0021-store-create-canonical-relational-schema.md).

Capabilities: contract-governance gains executable dataset checks with inspectable non-publishable
outcomes. No dbt run, live store, held-out model, or real-archive quality is claimed. No commit or
push was made.
