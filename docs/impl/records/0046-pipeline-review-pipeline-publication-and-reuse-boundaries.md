# Pipeline Publication and Reuse Boundary Review

## Task and scope

- Id: `review-pipeline-publication-and-reuse-boundaries`; capability: `pipeline-control`.
- State: accepted; required gates pass, with the nonblocking note below.
- Source: `docs/impl/plan.md` at `9639aeb3e429dfdd9b3ab8820336bc496631d6e2`; clean tree.
- Initial count: 71 tasks (61 agent, 10 human); selected task eligible.
- Amendments: the reproduced blocker added a focused prerequisite repair; full revised task below.

```markdown
#### review-pipeline-publication-and-reuse-boundaries

Review fixture orchestration before concrete corpus workers depend on its publication protocol.

- Serves: `pipeline-control` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: [Stage and artifact interface contracts](records/0040-pipeline-refactor-stage-and-artifact-interface-contracts.md);
[Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md);
[Progress logging and resource telemetry](records/0043-pipeline-add-progress-logging-and-resource-telemetry.md);
[Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md);
[Investigation profile and output manifest](records/0045-pipeline-implement-investigation-profile-and-output-manifest.md);
[Inference and evaluation checkpoint](records/0038-eval-found-review-inference-and-evaluation-boundaries.md).
- User-visible outcome:
Concrete adapters inherit a checked run/lease/quality/publication boundary.
- Scope boundary:
Fixture DAG and disposable store integration only; source delta/prune and archive proofs stay in
the later corpus/control checkpoint, avoiding a dependency on workers this checkpoint gates.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace aggregate versus atomic execution, frozen parameters, exact-generation quality, file/database
publication order, concurrent reuse, forced attempts, expired leases, cancellation and reserve loss.
Inject failure around the active-pointer switch; reconcile logs, ledger and visible artifacts.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
Equivalent commands produce equivalent logical manifests; missing/global checks, stale forecasts,
partial or failed stages never activate. Cache hits skip heavy work; interrupted publication
preserves one resumable attempt and the prior complete generation.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: none; this is the bounded checkpoint.
```

## Scope amendment

The checkpoint added repair 0047 as a prerequisite after reproducing the publication/reuse defects.
The original scope stays intact; the repair is now accepted.

```markdown
#### review-pipeline-publication-and-reuse-boundaries

Review fixture orchestration before concrete corpus workers depend on its publication protocol.

- Serves: `pipeline-control` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: [Publication/reuse integrity repair](records/0047-pipeline-repair-pipeline-publication-and-reuse-integrity.md);
[Stage and artifact interface contracts](records/0040-pipeline-refactor-stage-and-artifact-interface-contracts.md);
[Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md);
[Progress logging and resource telemetry](records/0043-pipeline-add-progress-logging-and-resource-telemetry.md);
[Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md);
[Investigation profile and output manifest](records/0045-pipeline-implement-investigation-profile-and-output-manifest.md);
[Inference and evaluation checkpoint](records/0038-eval-found-review-inference-and-evaluation-boundaries.md).
- User-visible outcome:
Concrete adapters inherit a checked run/lease/quality/publication boundary.
- Scope boundary:
Fixture DAG and disposable store integration only; source delta/prune and archive proofs stay in
the later corpus/control checkpoint, avoiding a dependency on workers this checkpoint gates.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace aggregate versus atomic execution, frozen parameters, exact-generation quality, file/database
publication order, concurrent reuse, forced attempts, expired leases, cancellation and reserve loss.
Inject failure around the active-pointer switch; reconcile logs, ledger and visible artifacts.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
Equivalent commands produce equivalent logical manifests; missing/global checks, stale forecasts,
partial or failed stages never activate. Cache hits skip heavy work; interrupted publication
preserves one resumable attempt and the prior complete generation.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: none; this is the bounded checkpoint.
```

## Implementation

Reviewed producer records 0038 and 0040-0045 and their linked current behavior, shared quality
policy, fixture orchestration, forecasts, file publication and disposable SQL ledger. The review
reproduced integrity defects and opened focused repair 0047 before changing production behavior.
No source archive or model workload ran; no Git-bound source artifact is produced.

Reused the stage registry, frozen context, `activation_decision`, artifact checksums, executor,
SQL ledger and forecast collector. The repair is confined to those seams, a local control lock,
retained quality evidence and immutable publication snapshots. There is no dependency or migration
change. Current behavior: [Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

Retained local evidence root: `$DATA_DIR/architecture-review/0046/`. Test fixtures establish the
control protocol only; disposable PostgreSQL exercises actual ledger transactions. The CUDA probe
records the host, not a model workload or memory-fit claim.

| Producer / invariant | Evidence | Result / limit |
| --- | --- | --- |
| 0038 inference/evaluation handoff | Accepted record and existing inference/evaluation tests in CI; quality refs checked at the stage seam | No model or archive promotion; prior audit notes stay resolved |
| 0040 frozen source/artifact identity | `tests/interfaces/`, orchestration drift tests, `test_atomic_stage_cannot_borrow_unrelated_upstream` | Typed refs and transitive frozen identity; no unrelated ancestor selection |
| 0041 complete artifacts and global quality | `tests/pipeline/control/`, `test_finalize_rechecks_artifacts_and_invalidation`, quality-reuse regressions | Missing, malformed, damaged and stale trees refuse; cache cannot bypass missing global checks |
| 0041 leases and attempt identity | `tests/pipeline/control/test_boundary_review.py`; `test_fresh_command_force_preserves_accepted_bytes` | Expired worker refuses; interruption releases; fresh command preserves prior bytes |
| 0041 actual SQL boundary | `tests/integration/postgres/test_pipeline_boundary_review.py`, `test_run_ledger.py`; `host-final.log`, `host-junit.xml` | Disposable pinned PostgreSQL passes concurrent absent-row lease, expiry, payload-rename crash, retry, force and cross-run cache checks |
| 0042 aggregate/atomic/resume | Existing aggregate/atomic outcome and lineage comparisons; `test_resume_reexecutes_partial_stage`; cross-process command regression | Same logical families/outcomes/lineage; partial reruns; duplicate commands invoke each worker once |
| 0042 stage quality | `test_stage_refuses_quality_for_another_generation`; `test_failed_stage_supplied_validation_blocks_publication` | Returned refs are retained and checked, including exact producing generation |
| 0043 logs vs ledger | `test_progress_manifest_agrees_with_halted_stage`; observability suite | Partial/failed outcomes retain truthful terminal state; bounded logging/redaction remain covered |
| 0044 stale forecasts and reserve | Forecast refusal/recheck suite; `test_forced_work_cannot_use_a_cache_hit_forecast` | Stale/missing/underfunded work cannot start; force budgets recomputation |
| 0045 complete and valid-negative output | Publication complete, empty, partial, failed, report-only, unregistered and cancellation tests | Only complete profiles activate; cancel in final worker remains interrupted |
| 0045 active-pointer crash matrix | `test_crash_keeps_a_coherent_pointer_and_resumes_without_work`, all five injection points | Before switch: prior matching snapshot; after switch: new matching snapshot; retry invokes no workers |
| Failing regressions before repair | `regressions-before.log`, `lease-before.log`, `quality-reuse-before.log` | 15 reproduced failures across publication, identity, reuse and quality; subsequent regressions pass |
| Host inventory | `cuda-host.txt`; declared host tests | RTX 4060 Ti, 16380 MiB, driver 595.84; 8 selected host tests pass; no models loaded |
| Required CI | `make ci`; `ci-accepted.log`, `ci-junit.xml` | Pass; 1069 passed, 50 heavy deselected |
| Diagnostic quality | `make -k quality`; `quality.log` | Coverage run passed all 1069 tests, 87% diagnostic coverage; source/wheel build passed. Overall quality exits nonzero for baseline MD013 findings, detailed below |
| Documentation integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | Pass; zero broken links and zero plan-integrity findings; final count 70 |

Earlier failed checks are retained honestly: sandbox NVIDIA access was unavailable; sandbox CI
could not write the existing uv cache; intermediate CI caught complexity/typing and audit-record
formatting, corrected here. A new forecast fixture initially lacked required checkout/config
metadata and was corrected. Putting pytest's base temp inside the checkout broke an existing
root-discovery negative test; the final CI uses pytest's normal external temporary directory.

## Audit handoff

| Note | Finding / owner / disposition |
| --- | --- |
| `AUD-review-pipeline-publication-and-reuse-boundaries-1` | Resolved blocker. [Owner repair 0047](0047-pipeline-repair-pipeline-publication-and-reuse-integrity.md) passed regressions, disposable SQL and required CI; retained failure and recovery evidence above. |
| `AUD-review-pipeline-publication-and-reuse-boundaries-2` | Nonblocking: fixture defaults use placeholder owned fingerprints and a coarse local lock; concrete producers must supply real quality/fingerprint/store boundaries before archive proofs. Repository-wide diagnostic Markdown debt also remains outside these runtime changes. [Owner corpus/control checkpoint](0063-corpus-review-corpus-and-control-integrity.md) reconciled all three: the concrete producers' declarations were completed by repair [0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md), the local lock stays a recorded nonblocking limit with a named owner, and the diagnostic Markdown report is now clean. Disposition: resolved. |

All incoming producer notes were reconciled: 0038 keeps its accepted inference/evaluation
resolutions; 0040's interface identity note remains resolved; 0041/0042/0044/0045 declared no new
notes; 0043's observability note remains resolved and terminal outcome agreement is strengthened.

Refactor verdict: targeted refactor required, implemented by accepted repair 0047. No broader
rewrite, model promotion or dependency change. Final checkpoint verdict: **proceed-with-nonblocking-notes**.

## Close or resume

Accepted. Required regressions, disposable PostgreSQL checks, CUDA host probe and `make ci` pass.
The diagnostic `make -k quality` ran coverage and successfully built source/wheel distributions;
overall quality remains nonzero for eight pre-existing MD013 findings in `plan.md`,
`current/portable-runtime.md` and preserved record 0045. The one new line-length issue was corrected;
`markdown-final.log` retains the remaining baseline findings, with original lines in
`baseline-long-lines.txt`. No lint rule or acceptance gate was weakened; this formatting debt is
explicitly routed with note 2. All changed current-state and record pages pass targeted Markdown lint.

Updated the narrow current-state page, current index and permanent record index. Removed only the
satisfied checkpoint and its accepted repair from remaining work; consumers now link this record.
Plan counts: 71 initially (61 agent, 10 human), 72 while the repair was open, 71 after repair
acceptance, and 70 at checkpoint close (60 agent, 10 human). The next eligible agent task is
`add-stage-artifact-inspection`. `pipeline-control` stays planned for its remaining concrete stages
and archive proof; its fixture publication/reuse boundary is now checked and hardened.

No human review handoff applies. No model service or archive walk was started. The final eight
host checks passed and `containers-after.txt` contains no running containers. No task process or
temporary code scaffold remains. Evidence, test reports and source fingerprints are retained under
`$DATA_DIR/architecture-review/0046/`. No commit or push was made.
