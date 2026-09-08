# Pipeline Publication and Reuse Integrity Repair

## Task and scope

- Id: `repair-pipeline-publication-and-reuse-integrity`; capability: `pipeline-control`.
- State: accepted; required regression, disposable-store and CI gates pass.
- Source: blocking note in [checkpoint 0046](0046-pipeline-review-pipeline-publication-and-reuse-boundaries.md).
- Amendments: none; focused repair authorized by the implementation request.

```markdown
#### repair-pipeline-publication-and-reuse-integrity

Repair publication and reuse gaps identified by the pipeline checkpoint before releasing workers.

- Serves: `pipeline-control` -- [Resumability](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: [Publication producer](records/0045-pipeline-implement-investigation-profile-and-output-manifest.md).
- User-visible outcome: Frozen fixture runs reject unrelated upstream/quality evidence, preserve
accepted attempts across fresh commands, and expose one coherent complete generation after crashes.
- Scope boundary: Existing fixture orchestration and disposable control-store boundary only;
no concrete corpus workers, source reconciliation, model promotion or production DB activation adapter.
- Data and artifact paths: `src/arxiv_int/pipeline/`, mirrored tests, disposable PostgreSQL tests;
`$DATA_DIR/architecture-review/0046/`.
- Execution path: Add failing regressions for generation/quality/artifact validation, run-bound
upstream lookup, concurrent reuse, fresh-executor force, expired lease and cancellation cleanup,
and every active-pointer crash point. Repair these seams using shared quality and lease policy;
retain immutable generation catalog snapshots selected by one active pointer.
- Acceptance gates: Regressions pass, complete/empty remain publishable, missing/stale/partial
outputs refuse activation, duplicate requests skip work, force preserves old bytes, expired holders
cannot publish, interruption resumes without replacing prior complete output. Run deterministic
pipeline tests, declared disposable PostgreSQL integration and `make ci`.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.
```

## Scope amendment

The audit input is an observation owned by this repair, not an acceptance dependency on the open
checkpoint. Force includes forecast allocation and terminal logs must reconcile with ledger results.
This makes the original boundary review concrete; it adds no corpus capability.

```markdown
#### repair-pipeline-publication-and-reuse-integrity

Repair publication and reuse gaps identified by the pipeline checkpoint before releasing workers.

- Serves: `pipeline-control` -- [Resumability](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: [Publication producer](records/0045-pipeline-implement-investigation-profile-and-output-manifest.md).
- Audit inputs: [AUD-review-pipeline-publication-and-reuse-boundaries-1](records/0046-pipeline-review-pipeline-publication-and-reuse-boundaries.md#audit-handoff).
- User-visible outcome: Frozen fixture runs reject unrelated upstream/quality evidence, preserve
accepted attempts across fresh commands, and expose one coherent complete generation after crashes.
- Scope boundary: Existing fixture orchestration and disposable control-store boundary only;
no concrete corpus workers, source reconciliation, model promotion or production DB activation adapter.
- Data and artifact paths: `src/arxiv_int/pipeline/`, mirrored tests, disposable PostgreSQL tests;
`$DATA_DIR/architecture-review/0046/`.
- Execution path: Add failing regressions for generation/quality/artifact validation, run-bound
upstream lookup, concurrent reuse, fresh-executor force, expired lease and cancellation cleanup,
and every active-pointer crash point. Repair these seams using shared quality and lease policy;
retain immutable generation catalog snapshots selected by one active pointer.
- Acceptance gates: Regressions pass, complete/empty remain publishable, missing/stale/partial
outputs refuse activation, duplicate requests skip work, force preserves old bytes, expired holders
cannot publish, interruption resumes without replacing prior complete output. Run deterministic
pipeline tests, declared disposable PostgreSQL integration and `make ci`.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.
```

## Implementation

Reused `activation_decision`, typed quality refs, artifact checksums, `ShardExecutor`, PostgreSQL
ledger operations, forecast collection and stage sessions. No dependency or migration change.

- Retain generation-bound `quality.json`; validate returned contract/generation identity and reject
  missing global checks on execution and cache hits. Production defaults fail closed.
- Resolve atomic upstream keys transitively from frozen parameters. Reject incomplete caches;
  resume partial stages and allocate exclusive attempt directories across fresh executors.
- Serialize local commands and index updates across processes. Lock absent SQL lease rows by reuse
  key; refuse expired renewal and publication, release interrupted workers, retain classified errors.
- Verify artifact/index/quality state at finalization. Write matching generation snapshots before
  switching one active pointer; preserve old snapshots and scope orphan cleanup to publication.
- Budget force as uncached through forecast, CLI and Make. Preserve cancellation at the last stage
  and truthful terminal observability outcomes.

Current behavior and compatibility: [Pipeline control](../current/pipeline-control.md).
Accepted old attempts without retained quality evidence become cache misses and require rerunning.
Catalog readers must follow the active pointer's catalog path. No production corpus/DB activation
adapter, model fit, archive acceptance or power-loss durability is claimed.

## Acceptance evidence

Evidence root: `$DATA_DIR/architecture-review/0046/`; full invariant matrix in
[checkpoint 0046](0046-pipeline-review-pipeline-publication-and-reuse-boundaries.md#acceptance-evidence).

| Gate | Exact test / command | Result and limit |
| --- | --- | --- |
| Publication and quality regressions | `tests/pipeline/publish/test_boundary_review.py`; `tests/pipeline/orchestration/test_quality_reuse_review.py` | Pass after reproduced failures; immutable snapshot/catalog, exact generation, stale/corrupt artifacts, partial resume, cancellation and logs |
| Lease and cache regressions | `tests/pipeline/control/test_boundary_review.py`; `tests/pipeline/orchestration/test_concurrent_commands.py` | Pass; expiry, interrupt cleanup, no missing-global bypass, separate-process workers execute once |
| Force allocation | `tests/pipeline/forecast/test_boundary_review.py` | Pass; cached forecast cannot authorize forced recomputation |
| Disposable SQL and CUDA host | Declared `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1` run; `host-tests.log` | 8 passed including live host probe; no real-archive or model-fit claim |
| Required checks | `make format`; `make ci` | Pass; 1069 passed, 50 heavy deselected; `ci-accepted.log` |
| Diagnostic checks | `make -k quality` | Coverage 87% (diagnostic), 1069 passed; distributions built. Overall quality nonzero only for pre-existing Markdown line-length debt recorded in 0046 |

## Audit handoff

Resolved `AUD-review-pipeline-publication-and-reuse-boundaries-1`; evidence in the linked
checkpoint matrix. `none identified` as new notes in this focused repair.

## Close or resume

Accepted. Required regressions, declared disposable PostgreSQL checks and `make ci` pass.
Removed only this repair from the plan and linked the accepted record from checkpoint 0046.
Counts: 72 including this added prerequisite, then 71 after its acceptance (61 agent, 10 human).
Checkpoint 0046 subsequently accepted the integrated repair with its documented nonblocking note.
No capability
status is promoted by this repair; no commit or push was made.
