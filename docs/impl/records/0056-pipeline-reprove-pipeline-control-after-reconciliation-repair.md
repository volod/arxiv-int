# Pipeline-Control Re-Proof After the Reconciliation Repair

## Task and scope

- Id: `reprove-pipeline-control-after-reconciliation-repair`; capability: `pipeline-control`.
- State: accepted; every named control gate passes on the host and the published fingerprint
  reproduces.
- Source: `docs/impl/plan.md`, `pipeline-control`; created to close the stated evidence gap in
  [repair 0055](0055-pipeline-repair-source-reconciliation-and-prune-safety.md), whose repair of the
  delta, retraction and prune seams was verified on fixtures only while
  [record 0053](0053-pipeline-prove-pipeline-control-on-provided-archive.md) remained the last
  real-archive bundle. Code revision `e2dcd2f` plus the accepted 0054/0055 working tree.
- Accepted task: the full block added to the plan for this run.

```markdown
#### reprove-pipeline-control-after-reconciliation-repair

Refresh the provided-archive control proof so the repaired delta, retraction and prune behavior has
current real-archive evidence.

- Serves: `pipeline-control` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: [Source reconciliation and prune safety](records/0055-pipeline-repair-source-reconciliation-and-prune-safety.md);
[Control integration checkpoint](records/0054-pipeline-review-control-integration-boundaries.md);
[Provided-archive control proof](records/0053-pipeline-prove-pipeline-control-on-provided-archive.md).
- User-visible outcome: The operator can see one current proof id whose add, change, rename, remove,
invalidation, rebuild and prune-apply evidence was produced by the repaired code, not by the
superseded bundle.
- Scope boundary: Rerun the existing pipeline-control scenario on a bounded disposable copy and
publish one new bundle; no new gate, no corpus stage, no scenario redesign, and no write to
`ARCHIVE_DIR`. This refreshes control evidence only; it establishes no extraction quality and no
CUDA worker fit.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification;
`$RESULTS_DIR/proof-work/pipeline-control/<proof-id>/`;
`$RESULTS_DIR/proofs/pipeline-control/<proof-id>/`; `$DATA_DIR/pipeline-control/<proof-id>/`.
- Execution path: Run `make proof CAPABILITY=pipeline-control RUN_ID=<proof-id>` on the host, then
`arxiv-int evaluation proof check --proof-dir ...`; capture the host GPU snapshot without loading a
model; compare the published code fingerprint with record 0053's to show the bundle covers the
repaired modules; record the superseded bundle explicitly.
- Acceptance gates: Every named control gate passes; the source fingerprint is unchanged before and
after; the published code fingerprint differs from record 0053's; a removal that is not the last
occurrence leaves its shard live and prune reports measured bytes; the proof check reproduces the
published fingerprint. Declare the Git-bound export list or the no-export result. A failed gate
keeps the task open and the superseded bundle stays the current evidence.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Scope amendment

One acceptance gate as originally written could not be met by this scenario and is corrected here
rather than reported as passed. The published scenario removes a file whose content exists nowhere
else, so it exercises a last-occurrence removal (`last_occurrence: 1`). It has no duplicate-content
file to delete, so the repaired non-last-occurrence rule cannot be exercised on this archive
without redesigning the scenario, which this task's scope boundary excludes. That rule keeps its
fixture regression
(`tests/pipeline/reconcile/test_diff.py::test_non_last_occurrence_removal_keeps_the_shard_live`),
and the gate below is restated to claim only what the run shows.

```markdown
- Acceptance gates: Every named control gate passes; the source fingerprint is unchanged before and
after; the published code fingerprint differs from record 0053's; the last-occurrence removal still
retracts exactly one row and leaves the remaining shards cached; the prune event reports measured
bytes rather than a directory count; the proof check reproduces the published fingerprint. Declare
the Git-bound export list or the no-export result. A removal that is not the last occurrence is out
of this scenario's reach and stays fixture-covered. A failed gate keeps the task open and the
superseded bundle stays the current evidence.
```

## Implementation

No production code changed. The existing scenario
(`src/arxiv_int/evaluation/proof/control_scenario.py`) was rerun unmodified on the host against a
bounded disposable copy of `ARCHIVE_DIR`, so the bundle differs from record 0053's only by the
repaired modules it exercises.

Proof id `0056-host` supersedes `0053-host-2` as the current pipeline-control evidence. Record 0053
stays accepted and unmodified: it remains the correct account of the code it proved. The published
code fingerprint moved from `24f4717092ea817cf50699cb99da746404d9725d2f5823e6340bf724db6dc8ee` to
`06df43f92359`, which is what shows the new bundle covers the repaired reconcile and prune modules
rather than replaying the old ones.

Every scenario count reproduced record 0053's values on the same archive -- 546 source files, zero
no-op workers, add invoked 1 / cached 8, change invoked 1, rename invoked 0, remove
last-occurrence 1, invalidation marked 24, prune removed 96, rebuild parity, sole-recovery blocked,
space refused, resume without alpha replay. The repair therefore fixed the six defects without
changing any behavior the earlier bundle had proved. Current-state page:
[Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Provided-archive proof | `make proof CAPABILITY=pipeline-control RUN_ID=0056-host` | pass; `$RESULTS_DIR/proofs/pipeline-control/0056-host/`; verdict `adopt`; 546 source files sampled |
| Every named control gate | published `gates.json` | pass; all 14 gates `pass` (noop, resume, add, change, rename, remove, code invalidation, space refusal, rebuild parity, sole recovery, prune, archive unmodified, preflight, no-export) |
| Archive left unmodified | `archive_unmodified` gate; `source_before`/`source_after` fingerprints in the scenario report | pass; identical before and after; the copy is at most eight files, 4 MiB each, 16 MiB total |
| Bundle covers the repaired code | published `summary.txt` code fingerprint vs record 0053 | pass; `06df43f92359`, not 0053's `24f4717092ea817c...` |
| Prune reports measured bytes | `$RESULTS_DIR/proof-work/pipeline-control/0056-host/runs/prune-plans/<plan-id>.event.json` | pass; `bytes_removed: 96074` with `directories_removed: 96`; the superseded code would have written `96` into `bytes_removed` |
| Last-occurrence removal | scenario `remove` delta in `export.json` | pass; `last_occurrence: 1`, `retracted: 1`, `active_rows: 8`, remaining eight shards cached, zero workers invoked |
| Proof check reproduces the fingerprint | `arxiv-int evaluation proof check --proof-dir $RESULTS_DIR/proofs/pipeline-control/0056-host` | pass; `37370b381a7496eac232f020375d77b83eba4e54a51a9736bdf5ab7cde243292` |
| Raw vs transformed fingerprints | published `policy.json` | pass; raw `37370b381a7496eac232f020375d77b83eba4e54a51a9736bdf5ab7cde243292`; transformed `77f19032bf8266e9cb91ba26b94d2187032480dd8c9b4a7b560bae7864e09549`; policy `arxiv-int.proof-identity.v1` |
| Git-bound export | published `export.json` | `no-export`; `git_bound: []`; no Git-bound source artifact is produced |
| Identity / leak | `grep -rE "/home/\|/mnt/\|/media/"` over the published bundle | pass; no operator path in any published file |
| CUDA host GPU snapshot | `nvidia-smi`; `$DATA_DIR/pipeline-control/0056-host/nvidia-smi.txt` | pass on host (NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84, CUDA 13.2); no model loaded and no GPU work in this scenario |
| Required CI | `make ci` | pass; 1136 passed, 50 deselected (heavy) |
| Documentation integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 0 findings |

Limits, stated rather than implied. The forecast on this archive was `degraded` / `low` because the
sampled files include multi-gigabyte objects; the control drills still ran and the simulated 0-byte
recheck refused before allocation. Then-usable stages are the registered `preflight` worker plus the
fixture DAG; inventory and later corpus stages are not part of this proof, so it establishes no
extraction quality. The GPU snapshot records the host, not CUDA worker fit, because this scenario
loads no model. A removal that is not the last occurrence stays fixture-covered, per the amendment
above.

## Audit handoff

Reviewed source immutability across the whole run, the bounded copy budget, the published
fingerprint chain, the code-fingerprint change that makes the bundle attributable to the repaired
modules, prune byte accounting on real trees, and path-free publication.

`none identified`.

## Close or resume

Accepted. The provided-archive evidence gap stated in
[repair 0055](0055-pipeline-repair-source-reconciliation-and-prune-safety.md) is closed: proof
`0056-host` is the current pipeline-control bundle and `0053-host-2` is superseded. Plan task
removed; counts moved from 67 back to 66 tasks (56 agent, 10 human unchanged). Next agent work:
`implement-streaming-inventory`. No review-owned service was started or left running; the proof
work tree under `$RESULTS_DIR/proof-work/pipeline-control/0056-host/` is retained as local evidence
and is not Git-bound.
