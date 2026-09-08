# Task Record

## Task and scope

- Id / capability / checkpoint: `refactor-prerelease-migration-consolidation` /
  `canonical-store` / `review-corpus-and-control-integrity`
- State: accepted
- Source: ad hoc operator request (2026-09-08); no public release or deployed database.
  Code revision is the working tree that previously carried overlay revisions `0002`-`0005`.
  Initial `make plan-status`: 67 tasks (57 agent, 10 human); next agent remained
  `implement-streaming-inventory`.
- Amendments: none.

```markdown
#### refactor-prerelease-migration-consolidation

Collapse pre-release Alembic history into one initial store revision that matches the current
model, so operators are not asked to read development-era ALTER/overlay steps.

- Serves: `canonical-store` -- [Evolution and migrations](../design/spec.md#evolution-and-migrations)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md);
[Incremental reconciliation](records/0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md);
[Progress logging](records/0043-pipeline-add-progress-logging-and-resource-telemetry.md);
[Run ledger](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
[Canonical relational schema](records/0021-store-create-canonical-relational-schema.md).
- User-visible outcome: Empty databases apply a single irreversible `0001` that creates the current
canonical, control, staging, and projection schema. Later additive revisions appear only after a
release, as differences from that baseline.
- Scope boundary: Re-author frozen `0001_initial_store.py` as CREATE-time current DDL; delete
`0002`-`0005`; do not keep overlay ALTER TABLE or partial-era stamp targets. Do not change product
contracts, runtime table modules, or operator commands except revision identity and adoption of a
complete current catalog. Do not invent a previous-release upgrade path.
- Data and artifact paths: `src/arxiv_int/migrations/versions/`, `revision_manifest.json`,
`head_state.json`, store apply/adopt/inspect modules, mirrored tests, and current-state store,
contract, pipeline-control, and inference pages.
- Execution path: Merge overlay table/index/grant definitions into `0001` schema_metadata so HASH
parents, staging clones, and foreign keys are created with the initial tables; set head to `0001`;
refuse incomplete catalogs on adopt; align tests with one head.
- Acceptance gates: `make db-check` reports head `0001` with no pending operations; network-free
tests cover complete-catalog stamp, partial-catalog refusal, irreversible teardown, and runtime
table alignment against frozen `0001`; `make ci` passes. Live disposable schema apply is not-run
unless `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1`.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Implementation

`src/arxiv_int/migrations/versions/0001_initial_store.py` is now the only Alembic revision and
the current store model. Overlay files `0002_pipeline_run_ledger.py`,
`0003_stage_progress.py`, `0004_source_tombstone_and_prune.py`, and
`0005_document_path_event_table.py` are removed. Path-event HASH parents and staging clones are
created with the other contract tables (no post-create `ALTER TABLE` for those foreign keys).
Run-ledger, stage-progress, and reconcile tables are created in the same `upgrade()` as indexes
and grants.

`HEAD_REVISION` and `INITIAL_REVISION` are both `0001`. Live adoption stamps `0001` only when the
complete current overlay is present; partial catalogs are refused. Catalog comparison loads one
frozen `schema_metadata()`. Runtime SQLAlchemy modules in `pipeline.control`,
`observability.sinks`, and `pipeline.reconcile` are unchanged except comments; alignment tests
read subsets of the initial revision.

Current-state pages: [Canonical store](../current/canonical-store.md);
[Contracts](../current/contracts.md); [Pipeline control](../current/pipeline-control.md);
[Local inference](../current/local-inference.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Head `0001`, no pending operations | `make db-check` (via `make ci`) | pass; `migration check passed at head 0001; live evidence: not-run` |
| Offline SQL is one revision | `tests/contracts/migrations/test_offline_sql.py` | pass; creates `document_path_event`, `ctl.run`, progress and tombstone tables; no path-event `ALTER TABLE`; no `0002` stamp |
| Complete overlay stamps `0001` | `tests/stores/postgres/test_canonical_schema_apply.py::test_adopt_stamps_complete_overlay` | pass |
| Missing ledger refuses stamp | `tests/stores/postgres/test_ledger_adopt_stamp.py` | pass |
| Path-event columns/FKs match contract | `tests/stores/postgres/test_path_event_revision.py` | pass; `HEAD_REVISION == INITIAL_REVISION == "0001"` |
| Runtime ledger/progress/reconcile alignment | `tests/pipeline/control/test_revision_alignment.py`; `tests/observability/test_obs_revision_alignment.py`; `tests/pipeline/reconcile/test_revision_alignment.py` | pass |
| Graph/checksum gate | `tests/contracts/migrations/test_graph_and_check.py` | pass; product head `0001` |
| Format, lint, types, complexity, doc links, spec-plan | `make ci` | pass |
| Contracts, ontology, inference schemas, identity policy, fixtures | `make ci` | pass; 21 contracts |
| Deterministic tests | `make ci` / `make test` (`-m "not heavy"`) | pass; 1121 passed, 2 skipped, 50 deselected (heavy) |
| Live disposable schema | `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1` | not-run |
| Plan counts | `make plan-status` | 67 tasks (57 agent, 10 human); next agent `implement-streaming-inventory` |

Fixtures and offline SQL do not prove a live PostgreSQL apply. Coverage from `make quality` is
diagnostic (about 86%) and is not a gate. `make quality` then failed `lint-md` on existing
MD013 line-length findings in spec/current/plan pages; those were not introduced as product
behavior and were not treated as blocking this refactor.

## Audit handoff

Reviewed frozen `0001` CREATE-time coverage versus deleted overlays, single-head checksum/graph
gates, adoption of only a complete current catalog, and irreversible teardown. No previous-release
upgrade path exists because there is no release.

`none identified`.

## Close or resume

Accepted. This request was not a plan task, so plan counts stay 67 tasks (57 agent, 10 human).
`canonical-store` schema history is now one initial revision; later additive revisions remain the
post-release mechanism. Next agent work: `implement-streaming-inventory`. This record does not
start that task. No review-owned service remains running.
