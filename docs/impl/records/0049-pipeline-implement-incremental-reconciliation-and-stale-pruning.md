# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-incremental-reconciliation-and-stale-pruning` /
  `pipeline-control` / `review-corpus-and-control-integrity`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `implement-incremental-reconciliation-and-stale-pruning`;
  working tree includes accepted [0041](0041-pipeline-implement-run-ledger-and-atomic-artifacts.md),
  [0042](0042-pipeline-implement-stage-dag-cli-and-make-targets.md),
  [0025](0025-store-implement-rebuildable-search-and-graph-projections.md), and
  [0048](0048-pipeline-add-stage-artifact-inspection.md). Initial count: 69 tasks
  (59 agent, 10 human). `make plan-status` reports `implement-streaming-inventory` as the
  next eligible agent task because this task listed that producer as a dependency.
  This record implements the reconciler against complete comparable source-manifest
  fixtures so inventory can later emit the same schema; it does not implement inventory.
- Amendments: none.

```markdown
#### implement-incremental-reconciliation-and-stale-pruning

Reconcile archive and implementation deltas through artifact lineage, retract stale active data,
and provide safe partial update, full rebuild, and physical-prune paths.

- Serves: `pipeline-control` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: [Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md);
[0025](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
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
```

## Implementation

Root-stage reuse identity is now the content-hash shard after `bind_shard`, not the whole
`source_snapshot`. A complete comparable scan is persisted under
`$RUNS_DIR/<run-id>/delta/manifest.json` so later updates diff against saved state.

| Module | Role |
| --- | --- |
| `pipeline/reconcile/scan.py` | Per-silo file hashes; incomplete/unreadable silos cannot tombstone |
| `diff.py` / `closure.py` | add/content-change/path-rename/remove; path-rename skips workers |
| `views.py` / `activate.py` | Last-occurrence retraction; shared/merge/split/review retained |
| `commands.py` | `prepare_update` / `record_rebuild` (checksums strip `generationId`) |
| `pipeline/prune/` | Two-phase dry-run/apply; protected kinds; superseded dirs |
| `migrations/versions/0004_source_tombstone_and_prune.py` | Frozen `ctl.source_tombstone`, `prune_event`, `artifact_pin` |
| `stg_source_tombstones` / `int_active_documents` | Set-based active view excluding last-occurrence hashes |

`arxiv_int.pipeline.reconcile` does not import SQLAlchemy; bound writers are
`reconcile.postgres` / `tables`. Forecast `cache_plan` walks the same shards as the
orchestrator so a no-op rerun is a cache hit. Prune apply deletes by directory so live
reuse keys are not dropped when a superseded attempt shares the key.

Current-state page: [Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| No-op update skips workers | `tests/pipeline/reconcile/test_update.py::test_noop_update_invokes_no_heavy_workers` | pass; `alpha` calls stay 1 |
| Additions touch only new shards | `test_additions_touch_only_new_shards` | pass; `alpha` calls 2 |
| Path-only rename skips analysis | `test_path_only_rename_avoids_content_analysis` | pass; no worker on second walk |
| Change/remove retract dependents | `test_change_and_remove_retract_dependent_outputs`; `test_diff.py::test_last_occurrence_retracts_only_unshared_rows` | pass |
| Partial/unreadable scans | `test_diff.py::test_partial_or_unreadable_scans_withhold_removal_tombstones` | pass; no removal tombstones |
| Shared merge/split evidence | `test_diff.py::test_merge_split_and_review_keep_shared_evidence` | pass |
| Rebuild matches baseline | `test_rebuild_matches_a_clean_baseline` | pass; checksums ignore generation tokens |
| Quality blocks pointer switch | `test_quality_failure_blocks_pointer_switch` | pass; `ActivationRefusedError` |
| dbt source/ref vs artifact edges | `test_dbt_source_ref_lineage_covers_artifact_edges` | pass |
| Owned-fingerprint descendants | existing `tests/pipeline/control/` stale-closure tests | pass |
| Prune protections | `tests/pipeline/prune/test_prune.py` | pass; sole-recovery, active/pin/review/rollback/ledger/backup; superseded deleted, live index kept |
| Frozen revision `0004` | `tests/pipeline/reconcile/test_revision_alignment.py`; `make db-check` | pass; head `0004`; SHA-256 `2e9997722371608fd7c7a7ae375a103540c9b6e82f7e5e94097978c114286b4f` |
| Optional imports | `tests/pipeline/reconcile/test_optional_imports.py` | pass; in-memory reconcile/prune omit sqlalchemy |
| CUDA host GPU snapshot | `nvidia-smi`; `$DATA_DIR/pipeline-reconcile/0049/nvidia-smi.txt` | pass on host (NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84, CUDA 13.2) |
| Disposable schema at head `0004` | `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1 pytest tests/integration/postgres/test_canonical_schema.py tests/integration/postgres/test_run_ledger.py tests/integration/postgres/test_catalog_boundaries.py` | pass; 16 tests on this CUDA host with image `arxiv-int/postgres:17-0.25.6-age1.7.0` |
| Formatting and required CI | `make format`; `make ci` | pass; 1100 passed, 50 heavy deselected |
| Documentation links and plan integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 68 tasks (58 agent, 10 human); next `implement-streaming-inventory` |

Fixtures do not prove real-archive extraction quality or CUDA worker fit. Streaming inventory
remains planned; live dbt materialization of `int_active_documents` was not-run
(`ARXIV_INT_RUN_DBT` unset).

## Audit handoff

Reviewed complete-scan tombstone withholding, last-occurrence versus shared evidence, rebuild
checksum comparison without generation tokens, prune directory identity versus reuse-key
collision, overlay stamp `0004`, and forecast cache-plan shard alignment.

`none identified`.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 69 to 68 tasks
(59 to 58 agent; 10 human unchanged). `pipeline-control` still has evidence lookup, provided-archive
proof, and the corpus/control checkpoint. Next agent work: `implement-streaming-inventory`.
No review-owned service remains running.
