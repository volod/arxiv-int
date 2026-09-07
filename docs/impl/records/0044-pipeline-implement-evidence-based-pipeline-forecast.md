# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-evidence-based-pipeline-forecast` /
  `pipeline-control` / `review-pipeline-publication-and-reuse-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `implement-evidence-based-pipeline-forecast`; working tree
  includes accepted [0043](0043-pipeline-add-progress-logging-and-resource-telemetry.md)
  progress logging. Initial count: 73 tasks (63 agent, 10 human); `make plan-status` selected
  this task.
- Amendments: none.

```markdown
#### implement-evidence-based-pipeline-forecast

Implement a read-only command that predicts requested work, duration, output/peak storage, and
free-space safety before a pipeline run.

- Serves: `pipeline-control` --
[Pre-run forecast and resource refusal](../design/spec.md#pre-run-forecast-and-resource-refusal)
- Agent status: CLEAR
- Dependencies: [Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
[Progress logging and resource telemetry](records/0043-pipeline-add-progress-logging-and-resource-telemetry.md);
runtime storage evidence documented in
[Portable runtime](current/portable-runtime.md).
- User-visible outcome: Before starting, an operator sees stage-by-stage cache hits, changed work,
time and data-size ranges, peak scratch/rebuild needs, accessible disk free space, confidence, and a
clear ready/degraded/blocked decision.
- Scope boundary: Perform inventory, sampling, manifest, telemetry, and filesystem checks only; do
not load heavy models, materialize production artifacts, invent precise estimates, or bypass hard
space reserves.
- Data and artifact paths: `src/arxiv_int/pipeline/forecast/`, `configs/capacity/`, forecast JSON
Schema/contracts, prior run manifests/telemetry, and `$RUNS_DIR/<forecast-id>/forecast/`.
- Execution path: Implement estimators against fixture manifests before concrete stages; use
bounded directory
metadata sampling when no inventory exists, then consume inventory/delta and cache manifests when
available. Resolve comparable runs and bounded format samples;
estimate lower/upper output, time, WAL, temp, staging, rebuild, rollback, backup, and
selected pipeline output costs; the organizer estimates placement independently; deduplicate
filesystem devices across the archive, results, and
database roots; read accessible free bytes; emit evidence/coefficient provenance and a fingerprinted
console/JSON decision; add stage-boundary free-space rechecks. Expose `make forecast RUN_ID=...`
and the equivalent CLI option to use the created run's frozen inputs and retain its forecast under
that run. The aggregate command calls the same estimator and refusal handler; standalone forecasts
remain available without creating a production generation.
- Acceptance gates: Zero-history fixtures yield conservative low-confidence ranges; estimates replay
from captured evidence; shared devices are counted once; inaccessible paths and upper-bound peak plus
reserve shortfalls exit non-zero before heavy work; stale forecasts are rejected; simulated free-space
loss checkpoints before allocation without accepting partial output. Atomic and aggregate forecast
decisions agree for the same captured inputs; changed configuration cannot reuse a stale forecast.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.
```

## Implementation

`src/arxiv_int/pipeline/forecast/` owns the read-only estimator, JSON decision
(`arxiv-int.forecast.v1`), and stage-boundary free-space recheck. Aggregate `pipeline run` /
`update` / `rebuild` and atomic `pipeline forecast` share `build_forecast()`. Declared coefficients
live in `configs/capacity/envelope.json` (`arxiv-int.capacity.envelope.v1`); missing checkout files
fall back to the same Python defaults so fake checkouts still work. Drift is checked by
`check_schema_drift()`.

Inventory prefers delta, then inventory manifests, then bounded metadata sampling (no file
contents). Cache hits come from the reuse index. Comparable telemetry, when present, comes from
prior observability manifests. Host GPU/RAM assumptions reuse inference `nvidia-smi` and do not
load models. Filesystem roots are grouped by device id; category costs assign to one root then
sum per device. Archive organization is excluded. Freshness hashes config, source snapshot,
envelope, plan coverage, and per-stage cache hits; live free bytes are rechecked, not
fingerprinted. `ForecastRefusedError` and `StaleForecastError` use exit 3. A missing GPU for a
`gpu_required` stage is `degraded`. An `unknown` estimate on a large archive (at least 50 GiB,
no comparable telemetry) rolls up to `blocked`.

Standalone forecasts allocate `forecast-<hex>` without `run-context.json`. Bound forecasts use
the created run id. `run_dag` binds a covering forecast and installs `space_guard` before each
stage. Hard reserves are not bypassed.

Current-state page: [Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Zero-history conservative ranges | `tests/pipeline/forecast/test_engine.py::test_zero_history_sample_is_conservative_and_low_confidence` | pass; `degraded` / `low`; 2.5-4.0 envelope; no point duration |
| Replay from captured evidence | `test_estimates_replay_from_captured_evidence` | pass; identical inputs yield identical fingerprint and ranges |
| Shared devices counted once | `test_shared_devices_are_budgeted_once` | pass; one budget per device id |
| Atomic and aggregate agree | `test_atomic_and_aggregate_agree_on_captured_inputs` | pass; same `build_forecast()` document |
| Inaccessible paths | `tests/pipeline/forecast/test_refusal.py::test_inaccessible_paths_block` | pass; overall `blocked` |
| Peak plus reserve shortfall | `test_upper_bound_plus_reserve_shortfall_blocks` | pass; exit path is `ForecastRefusedError` (3) |
| Stale configuration | `test_changed_configuration_cannot_reuse_stale_forecast` | pass; `StaleForecastError` |
| Missing or uncovered forecast | `test_missing_forecast_is_rejected`; `test_uncovered_stage_is_rejected` | pass |
| Simulated free-space loss | `tests/pipeline/forecast/test_recheck.py::test_simulated_free_space_loss_halts_before_allocation` | pass; worker not invoked; no partial manifest |
| Inventory/delta vs sample | `tests/pipeline/forecast/test_sample.py` | pass; manifests preferred; sampling does not read contents |
| Schema drift | `test_capacity_schema_and_envelope_match_the_checkout` | pass |
| CLI standalone vs `--run-id` | `tests/pipeline/forecast/test_cli.py` | pass; standalone is `forecast-<hex>` / `production=false`; bound writes under the run |
| Make dry-run | `test_make_help_lists_forecast` | pass; requires created run id |
| Optional imports | `test_forecast_modules_do_not_import_heavy_stacks` | pass |
| CUDA host snapshot | `nvidia-smi`; `tests/pipeline/forecast/test_cuda.py::test_live_nvidia_snapshot_is_recorded_when_a_device_is_present` | pass on host (NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84); `make ci` skipped the live probe in the sandbox |
| Live standalone forecast | `arxiv-int pipeline forecast --archive-dir` on a one-file sample | pass; `decision=degraded` `confidence=low` `inventory=sample`; rotational `PGDATA_DIR` device `degraded`; exit 0; excluded `archive-organization` |
| Formatting and required CI | `make format`; `DATA_DIR=/tmp/arxiv-int-forecast-0044 make ci` | pass; 1024 passed, 2 skipped (live NVIDIA under sandbox), 48 heavy deselected |
| Documentation links and plan integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 72 tasks (62 agent, 10 human); next `implement-investigation-profile-and-output-manifest` |

Fixtures do not prove real-archive extraction quality. CUDA inventory was sampled for host
assumptions and was not used as a DAG worker-fit gate. The live forecast did not load models.

## Audit handoff

Reviewed estimator ranges, device dedup, freshness versus live free-space recheck, orchestrator
`space_guard` halt-before-allocation, and CUDA-host GPU snapshot without model load.

`none identified`.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 73 to 72 tasks
(63 to 62 agent; 10 human unchanged). `pipeline-control` still has publication assembly work.
Next agent work: `implement-investigation-profile-and-output-manifest`. No review-owned service
remains running.
