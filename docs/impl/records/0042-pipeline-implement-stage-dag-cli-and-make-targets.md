# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-stage-dag-cli-and-make-targets` /
  `pipeline-control` / `review-pipeline-publication-and-reuse-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `implement-stage-dag-cli-and-make-targets`; working tree
  includes accepted [0041](0041-pipeline-implement-run-ledger-and-atomic-artifacts.md)
  ledger work. Initial count: 75 tasks (65 agent, 10 human); `make plan-status` selected this
  task.
- Amendments: none.

```markdown
#### implement-stage-dag-cli-and-make-targets

Complete the dependency-aware stage registry, independent stage command, end-to-end and incremental
runners, resume, status, invalidate, rebuild, and stale-prune planning interfaces.

- Serves: `pipeline-control` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: [Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md).
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
```

## Implementation

Typed fixture-first DAG orchestration lives in `src/arxiv_int/pipeline/` and walks stages through
the 0041 `ShardExecutor`. There is no second scheduler and no Airflow, Prefect, Celery, Redis, or
Kubernetes. Setup's `PROFILE_STAGES` / `STAGE_FEATURES` remain the feature/service requirement
seam. `production_registry()` declares production dependencies and binds only `EvaluateStage`;
other investigation stages stay unregistered and fail explicitly.

`allocate_run_id()` emits `run-<hex>` and never inherits Make's developer `RUN_ID=local` fallback.
`arxiv-int run create` freezes secret-free configuration under `$RUNS_DIR/<run-id>/run-context.json`.
Later stage/status/resume calls reuse that context and refuse configuration drift or a changed
archive snapshot. `--to X` is ancestors(X)+X; `--from X` is X plus descendants with assumed
upstream. Invalidate marks both the reuse index and the ledger stale so a later walk cannot
cache-hit. Update clones the frozen profile into a new generation that sees the current snapshot;
rebuild allocates a new generation with `force=True`. Prune dry-run lists stale derived attempts;
apply needs `--apply --plan PLAN_ID` and refuses to delete the sole recovery copy. Declared
Pandera validators and dbt selections run at producer boundaries through `QualityBoundary`;
failed or not-run checks halt downstream work.

Argument parsing stays in `pipeline/cli.py` so base `--help` does not import YAML or orchestration
handlers. Make wrappers load `.env` and stay thin; `pipeline` / `run-create` do not pass
`--run-id` or `--profile` defaults.

Current-state page: [Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| DAG, range, skip, invalid dependency | `tests/pipeline/orchestration/test_dag.py` | pass; `--from`/`--to` closures, cycles, unknown stages |
| Skip / cache-hit on unchanged rerun | `test_aggregate_run_produces_lineage_and_skips_on_rerun` | pass; worker invoked once |
| Failure halt | `test_failure_halts_downstream_gamma` | pass; optional omega not invoked |
| Aggregate vs atomic equivalence | `test_aggregate_and_atomic_produce_equivalent_outcomes`; `test_aggregate_and_atomic_refuse_the_same_missing_upstream` | pass; same lineage/outcomes and `StaleUpstreamError` |
| Unregistered required stages | `test_unregistered_required_stages_fail_before_work`; `test_pipeline_run_refuses_unregistered_investigation_stages` | pass; investigation `make pipeline` / CLI exits 1 |
| Resume after cancel | `test_resume_after_cancel_continues_remaining_stages` | pass |
| Force new attempt | `test_force_writes_a_new_attempt_without_overwriting` | pass; prior attempt retained |
| Update, invalidate, rebuild, prune dry-run | `tests/pipeline/orchestration/test_actions.py` | pass; apply needs a plan id |
| Quality not-run/fail and dbt not-run | `test_failed_and_not_run_quality_halt_downstream`; `test_failed_dbt_selection_halts_downstream` | pass |
| Signal handling | `test_signal_handler_cancels_the_token` | pass |
| Unique run ids | `test_allocate_run_id_is_unique_and_not_local` | pass; prefix `run-`, never `local` |
| CLI help, defaults, precedence | `test_cli_help_lists_defaults_and_precedence` | pass |
| Make/CLI defaults agree | `tests/pipeline/orchestration/test_make.py` | pass; no hardcoded `--run-id`/`--profile` on `pipeline`/`run-create`; `stage`/`resume` refuse `local` |
| Optional-import isolation | `tests/pipeline/orchestration/test_optional_imports.py`; `tests/runtime/setup/test_optional_imports.py` | pass; parser build does not import YAML |
| Directory-to-report on concrete stages | deferred until corpus runners exist | not-run; investigation profile refuses unregistered stages instead |
| Formatting and required CI | `make format`; `DATA_DIR=/tmp/arxiv-int-dag-0042 make ci` | pass; 982 passed, 48 heavy deselected |
| Documentation links and plan integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 74 tasks (64 agent, 10 human); next `add-progress-logging-and-resource-telemetry` |

Fixtures do not prove real-archive extraction quality or CUDA worker fit. GPU inventory was
inspected and not used as a DAG acceptance gate.

## Audit handoff

Reviewed registry acyclicity, `--from`/`--to` closures, freeze/drift, invalidate vs ledger
cache-hit, aggregate vs atomic equivalence, quality halt, unique run ids vs Make `local`,
parser-build isolation from YAML, and production unregistered-stage refusal.

`none identified`. Forecast, `run finalize`, and knowledge-base publication remain planned.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 75 to 74 tasks
(65 to 64 agent; 10 human unchanged). `pipeline-control` still has progress logging, forecast,
and publication work. Next agent work: `add-progress-logging-and-resource-telemetry`. No
review-owned service remains running. CUDA host inventory was inspected (`nvidia-smi`: NVIDIA
GeForce RTX 4060 Ti, 16380 MiB, 14709 MiB free, driver 595.84) and was not used as acceptance
evidence.
