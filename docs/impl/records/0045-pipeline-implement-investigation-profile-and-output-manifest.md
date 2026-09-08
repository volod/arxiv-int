# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-investigation-profile-and-output-manifest` /
  `pipeline-control` / `review-pipeline-publication-and-reuse-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `implement-investigation-profile-and-output-manifest`; working
  tree includes accepted [0044](0044-pipeline-implement-evidence-based-pipeline-forecast.md)
  forecast. Initial count: 72 tasks (62 agent, 10 human); `make plan-status` selected this task.
- Amendments: none.

```markdown
#### implement-investigation-profile-and-output-manifest

Publish an explicit requested profile and coherent knowledge-base generation with honest completion states.

- Serves: `pipeline-control` -- [End-to-end run and output contract](../design/spec.md#end-to-end-run-and-output-contract)
- Agent status: CLEAR
- Dependencies: [Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md); [Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md).
- User-visible outcome: The default investigation command names every required output and report
entry point; a
lexical-only request is visibly a smaller profile.
- Scope boundary: Implement profile selection, contract validation, publication, and exit semantics
using fixture
runners; do not claim concrete extraction or full-pipeline acceptance from mocks.
- Data and artifact paths: `configs/pipeline/`, `src/arxiv_int/pipeline/`, output-manifest contracts,
`$RUNS_DIR/<run-id>/knowledge-base.json`, and orchestration fixtures.
- Execution path: Declare required versus conditional stages and output families; seal
artifact/snapshot ids,
counts/checksums, coverage and report path; validate then switch one active generation pointer;
write diagnostic reports for partial/failed runs and reconcile orphan staging after crashes.
Connect concrete profile declarations to setup's shared requirement seam. Assemble bare
`make pipeline` / `arxiv-int pipeline run` from the same create, preflight, forecast, stage and
finalize handlers as the documented atomic chain. Expose `make run-finalize RUN_ID=...` and
`arxiv-int run finalize RUN_ID`; report rendering alone cannot activate a generation. Return the run
id, logical status, manifest/report paths and exact status/resume commands; enforce missing-provider,
quality, resource and authorization gates before dependent work. Update the operator workflow with
the actual profile order and availability while concrete stages remain pending.
- Acceptance gates: Fixtures cover complete, valid-empty, partial, failed, blocked, interrupted,
and not-selected
states, specified exit codes, stale dependency refusal, and crash recovery across file/database
publication; a partial run cannot replace the last complete generation. No-argument Make and CLI
runs read `.env` in fresh shells; the explicit atomic chain yields equivalent logical artifacts,
lineage, quality and final states. Missing setup/required stages refuse execution, optional disabled
branches stay explicit, and interruption preserves one resumable generation.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.
```

## Implementation

`src/arxiv_int/pipeline/publish/` owns profile selection, knowledge-base assembly
(`arxiv-int.knowledge-base.v1`), diagnostic reports, and pointer activation. Committed overlays
are `configs/pipeline/investigation.json` and `lexical.json` (`arxiv-int.pipeline.profile.v1`).
Setup `PROFILE_STAGES` remains the requirement seam; `check_profile_alignment()` and
`check_schema_drift()` refuse drift. `FIXTURE_PROFILE` is Python-only. Anomalies currently map to
`evaluate`. Lexical omits topics/identities/ontology/facts/domain/vectors/graph.

Aggregate `pipeline run` / `update` / `rebuild` call archive-readability `preflight_run`, then
forecast, `run_dag`, then `finalize_run`. Atomic `stage` does not auto-finalize.
`arxiv-int run finalize RUN_ID` and `make run-finalize RUN_ID=...` require a created run id.
`write_report()` never calls `activate_generation()`. Activation writes
`$RUNS_DIR/<run-id>/knowledge-base.json`, then `$RUNS_DIR/active-catalog.json` (catalog/DB
stand-in), then `$RUNS_DIR/active-generation.json`. Only `succeeded` activates. Empty required
families are valid complete. Partial/failed/interrupted runs write diagnostics and cannot
replace the last complete pointer. Crash injectors cover after-manifest through
after-generation-replace; orphan `.tmp` files are reconciled on the next finalize.

Exits: succeeded 0, partial 2, failed 1, blocked/preflight 3, interrupted 130. A production
investigation run still refuses unregistered corpus stages after forecast (exit 1). Merged
`status.json` keeps prior stages so `stage` then `run finalize` sees the full chain.
`InterruptedPipelineError` maps SIGINT to 130. `PreflightRefusedError` covers unreadable silos.

Current-state page: [Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Setup/profile alignment | `tests/pipeline/publish/test_profiles.py::test_investigation_and_lexical_match_setup_profile_stages` | pass |
| Lexical is a smaller profile | `test_lexical_profile_is_visibly_smaller` | pass |
| Schema/profile drift | `test_committed_pipeline_assets_match_python_defaults` | pass |
| Complete activate exit 0 | `tests/pipeline/publish/test_publish.py::test_complete_fixture_run_activates_and_exits_zero` | pass; `active-generation.json` switches; optional `omega` is `not-selected` |
| Valid empty still succeeds | `test_valid_empty_required_family_still_succeeds` | pass; exit 0 |
| Partial cannot replace complete | `test_partial_run_cannot_replace_complete_generation` | pass; exit 2; prior pointer kept |
| Failed diagnostic, no activate | `test_failed_run_writes_diagnostic_without_activation` | pass; exit 1 |
| Unreadable archive preflight | `test_unreadable_archive_is_blocked_preflight` | pass; `PreflightRefusedError` exit 3 |
| Interrupted 130 then resume | `test_interrupted_run_is_resumable_and_does_not_activate` | pass; resume then activate |
| Stale upstream | `test_stale_dependency_still_refuses_before_finalize` | pass |
| Crash after-manifest | `test_crash_after_manifest_keeps_prior_complete_generation` | pass; prior complete pointer kept |
| Crash after-catalog-write | `test_crash_after_catalog_write_reconciles_orphans` | pass; orphan `.tmp` cleaned |
| Report cannot activate | `test_report_rendering_cannot_activate_a_generation` | pass |
| Aggregate vs atomic | `test_aggregate_and_atomic_finalize_to_the_same_logical_state` | pass |
| CLI and Make finalize | `tests/pipeline/publish/test_cli.py` | pass; created run id required |
| Optional imports | `test_publish_modules_do_not_import_heavy_stacks` | pass |
| CUDA host snapshot | `nvidia-smi`; `tests/pipeline/forecast/test_cuda.py::test_live_nvidia_snapshot_is_recorded_when_a_device_is_present` | pass on host (NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84); `make ci` included the live probe |
| Formatting and required CI | `make format`; `DATA_DIR=/tmp/arxiv-int-publish-0045 make ci` | pass; 1044 passed, 48 heavy deselected |
| Documentation links and plan integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 71 tasks (61 agent, 10 human); next `review-pipeline-publication-and-reuse-boundaries` |

Fixtures do not prove real-archive extraction quality or CUDA worker fit. Publication used the
fixture protocol, not a production corpus walk.

## Audit handoff

Reviewed profile/setup alignment, activation-only-on-complete, report-cannot-activate, file
versus catalog pointer crash recovery, merged status for atomic finalize, and CUDA-host GPU
snapshot without model load.

`none identified`.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 72 to 71 tasks
(62 to 61 agent; 10 human unchanged). `pipeline-control` still has the publication/reuse
checkpoint and later corpus work. Next agent work:
`review-pipeline-publication-and-reuse-boundaries`. No review-owned service remains running.
