# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-run-ledger-and-atomic-artifacts` /
  `pipeline-control` / `review-pipeline-publication-and-reuse-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `implement-run-ledger-and-atomic-artifacts`; working tree
  includes accepted [0040](0040-pipeline-refactor-stage-and-artifact-interface-contracts.md)
  interface work. Initial count: 76 tasks (66 agent, 10 human); `make plan-status` selected this
  task.
- Amendments: none.

```markdown
#### implement-run-ledger-and-atomic-artifacts

Create run, stage, shard, lease, checkpoint, error, artifact-manifest, and transitive-lineage state
with deterministic reuse keys.

- Serves: `pipeline-control` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: [Canonical relational schema](records/0021-store-create-canonical-relational-schema.md);
fixture artifact contracts from
[Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md).
[Stage and artifact interface contracts](records/0040-pipeline-refactor-stage-and-artifact-interface-contracts.md).
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
```

## Implementation

Generic control lives in `src/arxiv_int/pipeline/control/`. In-memory execution is the public
package surface; `arxiv_int.pipeline.control.postgres` is the bound SQLAlchemy ledger. Frozen DDL
is Alembic `0002` and does not import runtime `tables.py`. Head is `0002`. Catalog comparison
accepts applied `0001` or `0002` so a 0001-era database upgrades instead of blocking setup as
drift. Complete overlays including ledger tables stamp `0002`; complete 0001-era overlays stamp
`0001`.

Reuse keys hash stage identity plus every owned fingerprint field, including validation catalog
and dbt model/input/rule fingerprints. Publication writes sibling temp files and replaces
`manifest.json` last. Cache hits validate the producer attempt and skip the worker. Force retry
uses a new attempt directory. `ctl.resource_lease` exists; inference still writes JSONL and does
not dual-write SQL.

PostgreSQL `Float` columns were authored as `DOUBLE PRECISION` so live inspection matches
`catalog_boundary` expected types.

Current-state page: [Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Illegal transitions rejected | `tests/pipeline/control/test_states.py` | pass; exhaustive illegal pairs plus retry bounds |
| Crash injection; no partial accept | `test_crash_does_not_create_a_reusable_manifest`; `test_crash_after_payload_rename_is_not_accepted` | pass; missing `manifest.json` is not reusable |
| Unchanged rerun skips worker | `test_unchanged_rerun_validates_and_skips_the_worker` | pass; worker invoked once |
| Owned fingerprint stale closure | `test_owned_fingerprint_change_marks_the_closure_stale` | pass; reachable consumers only |
| Force retry new attempt | `test_force_retry_writes_a_new_attempt_without_overwriting` | pass; prior attempt bytes retained |
| Formatting and required CI | `make format`; `DATA_DIR=/tmp/arxiv-int-ledger-0041 make ci` | pass; 943 passed, 45 heavy deselected |
| Disposable schema at head `0002` | `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1 pytest tests/integration/postgres/test_canonical_schema.py` | pass; 8 tests on this CUDA host with image `arxiv-int/postgres:17-0.25.6-age1.7.0` |
| Documentation links and plan integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 75 tasks (65 agent, 10 human); next `implement-stage-dag-cli-and-make-targets` |

Fixtures do not prove real-archive quality or CUDA worker fit. GPU inventory was inspected and not
used as a ledger acceptance gate.

## Audit handoff

Reviewed state-machine completeness, sibling-write order, cache-hit vs producer attempt, 0001/0002
catalog wiring, Float vs DOUBLE PRECISION live types, and optional-stack isolation of
`pipeline.control`.

`none identified`. Inference JSONL vs `ctl.resource_lease` dual-write stays out of this scope.
DAG CLI and publication remain planned.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 76 to 75 tasks
(66 to 65 agent; 10 human unchanged). `pipeline-control` still has DAG CLI, forecast, and
publication work. Next agent work: `implement-stage-dag-cli-and-make-targets`. No review-owned
service remains running. CUDA host inventory was inspected (`nvidia-smi`: NVIDIA GeForce RTX 4060
Ti, 16380 MiB, 14745 MiB free) and was not used as acceptance evidence.
