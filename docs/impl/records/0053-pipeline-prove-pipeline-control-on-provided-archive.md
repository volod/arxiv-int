# Task Record

## Task and scope

- Id / capability / checkpoint: `prove-pipeline-control-on-provided-archive` /
  `pipeline-control` / `review-corpus-and-control-integrity`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `prove-pipeline-control-on-provided-archive`;
  working tree includes accepted [0044](0044-pipeline-implement-evidence-based-pipeline-forecast.md),
  [0036](0036-eval-found-create-evaluation-fixtures-and-metrics.md),
  [0049](0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md),
  [0051](0051-pipeline-implement-evidence-and-source-location-lookup.md), and
  [0052](0052-store-refactor-prerelease-migration-consolidation.md).
  Initial `make plan-status`: 67 tasks (57 agent, 10 human); next eligible agent
  remained `implement-streaming-inventory` because this proof listed the still-open
  `prove-corpus-foundation-on-provided-archive` producer. This record proves then-usable
  pipeline-control stages against a bounded disposable copy of `ARCHIVE_DIR`; it does
  not implement corpus inventory/extract/chunk.
- Amendments: none.

```markdown
#### prove-pipeline-control-on-provided-archive

Exercise idempotency, incremental reconciliation, invalidation, forecasting, rebuild, and prune
planning with the supplied archive and publish the pipeline-control proof bundle.

- Serves: `pipeline-control` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: [Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md);
`prove-corpus-foundation-on-provided-archive`; [Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md);
[Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md).
- User-visible outcome: The supplied archive demonstrates that unchanged inputs skip heavy work,
deltas update only affected artifacts, stale data retracts safely, insufficient space blocks early,
and a clean generation can be rebuilt.
- Scope boundary: Do not modify `ARCHIVE_DIR`; perform add/change/rename/remove and prune-apply
drills only on a bounded disposable proof copy; do not prune the sole proof or recovery generation.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, disposable
`$RESULTS_DIR/proof-work/pipeline-control/<proof-id>/`, and
`$RESULTS_DIR/proofs/pipeline-control/<proof-id>/`.
- Execution path: Forecast and run the corpus closure; rerun unchanged; create controlled source
deltas and a stage-fingerprint bump; inspect minimal closures and active retractions; simulate low
space; rebuild into a fresh generation; compare checksums; dry-run pruning and apply it only to an
extra disposable stale generation.
- Acceptance gates: Proof records zero heavy invocations on the no-op rerun, exact affected/unaffected
shards for each delta, correct tombstones and active rows, targeted code invalidation, non-zero
resource refusal before allocation, clean-rebuild parity, protected-data prune refusal, and no write
to the supplied archive.
Declare the Git-bound export list or no-export result. Committed copies pass the shared identity
obfuscation, format/reference/anchor and leak checks; local originals and local review packets stay
unchanged. Retain separate raw-proof and transformed-export fingerprints.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Implementation

`PreflightStage` is a registered `StageRunner` that refuses unreadable silos and publishes a
path-free `produced` artifact (`archive silos readable`). `production_registry()` binds it
alongside `EvaluateStage`. Aggregate `pipeline run` still calls `preflight_run()` before
forecast; `make stage STAGE=preflight` now has a worker. Inventory and later corpus stages
remain unregistered.

The proof publisher copies at most eight source files (4 MiB each, 16 MiB total) into
`$RESULTS_DIR/proof-work/pipeline-control/<proof-id>/`, isolates `RuntimeConfig` from operator
dotenv roots, and never writes `ARCHIVE_DIR`. Deltas, rebuild, and prune-apply run only on that
copy. The scenario uses then-usable stages: registered preflight plus the fixture DAG
(`alpha` / `beta` / `gamma`). It forecasts, resumes a partial walk without replaying completed
alpha workers, no-op reruns with zero worker invocations, applies add/change/rename/remove,
invalidates `alpha` and bumps its version, simulates a 0-byte free-space recheck, rebuilds with
generation-stripped checksum parity, prunes an extra stale generation, and probes sole-recovery
refusal by invalidating preflight when no live replacement exists. Preflight artifact checksums
are captured before prune deletes superseded attempt trees.

Git-bound export is **no-export** (`git_bound: []`). The published bundle is path-free JSON and
a one-line summary. Fingerprints are code (pipeline plus proof Python) and scenario
`pipeline-control:1`, not the evaluation fixture ledger.

Current-state page: [Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Required control gates on a disposable copy | `tests/evaluation/proof/test_pipeline_control.py` | pass; all named gates `pass`; archive fingerprint unchanged; `export.json` `no-export` and `git_bound: []` |
| Dispatcher and CLI | `test_pipeline_control_dispatcher_and_cli`; `arxiv-int evaluation proof publish/check --capability pipeline-control` | pass |
| Unreadable archive | `test_pipeline_control_refuses_an_unreadable_archive` | pass; `ValueError` `no readable files` |
| Copy budget | `test_copy_bounded_skips_files_over_budget` | pass; files over the per-file/total cap are not copied; source bytes unchanged |
| Registered preflight worker | `tests/pipeline/publish/test_preflight_stage.py`; `tests/pipeline/dag/test_cli.py` | pass; `preflight` not in missing investigation runners; inventory still missing |
| Unvalidated capabilities still refuse | `tests/evaluation/proof/test_evaluate_proof.py::test_proof_publish_rejects_unvalidated_and_stale` | pass; `corpus-foundation` still `unvalidated` |
| Provided-archive proof | `make proof CAPABILITY=pipeline-control RUN_ID=0053-host-2` | pass; `$RESULTS_DIR/proofs/pipeline-control/0053-host-2/`; 546 source files sampled; `archive_unmodified=true`; noop workers 0; add invoked 1 / cached 8; change invoked 1; rename invoked 0; remove last-occurrence 1; invalidation marked 24; rebuild match; sole-recovery blocked; prune removed 96; space refused; resume_ok |
| Proof check | `arxiv-int evaluation proof check --proof-dir $RESULTS_DIR/proofs/pipeline-control/0053-host-2` | pass; fingerprint `915ce8f94d55b79d1fece6f6c03d589afe46b5fe34de67a63247337a23d624a0` |
| Identity / leak | published `summary.txt`, `proof-manifest.json`, `export.json`, `gates.json`, `policy.json` | pass; no `/home/` or `/mnt/` in the Git-bound tree; Git-bound export list is empty |
| Raw vs transformed fingerprints | `$RESULTS_DIR/proofs/pipeline-control/0053-host-2/policy.json` | pass; raw `915ce8f94d55b79d1fece6f6c03d589afe46b5fe34de67a63247337a23d624a0`; transformed `77f19032bf8266e9cb91ba26b94d2187032480dd8c9b4a7b560bae7864e09549`; code `24f4717092ea817cf50699cb99da746404d9725d2f5823e6340bf724db6dc8ee`; fixtures `52fd23d0b250c473e87fcf2815ab3fc8d1f91dc51c9004f22189104a8902477c` |
| CUDA host GPU snapshot | `nvidia-smi`; `$DATA_DIR/pipeline-control/0053-host-2/nvidia-smi.txt` | pass on host (NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84, CUDA 13.2) |
| Format and required CI | `make format`; `make ci` | pass; 1127 passed, 2 skipped, 50 deselected (heavy); `make lint-doc-links` and `make lint-spec-plan` 0 findings |

The first host publication `0053-host` is stale after the `resume_ok` field rename. `0053-host-2`
is the accepted bundle. Forecast on this archive was `degraded` / `low` because sampled files
include multi-gigabyte objects; the control drills still ran, and the simulated 0-byte recheck
refused before allocation. Fixtures do not prove real-archive extraction quality or CUDA
worker fit. Corpus inventory/extract remain planned.

## Audit handoff

Reviewed bounded copy vs source immutability, checksum capture before prune, sole-recovery when
preflight is the remaining live root, content-hash shard closures for add/change/rename/remove,
and path-free proof publication.

`none identified`.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 67 to 66 tasks
(57 to 56 agent; 10 human unchanged). `pipeline-control` still has later corpus stages and
`review-corpus-and-control-integrity`. Next agent work: `implement-streaming-inventory`.
No review-owned service remains running.
