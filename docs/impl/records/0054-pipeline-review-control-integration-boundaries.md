# Control Integration Boundaries Review

## Task and scope

- Id: `review-control-integration-boundaries`; capability: `pipeline-control`; checkpoint: this task.
- State: accepted; repair 0055, the traced invariants and required CI pass.
- Source: `docs/impl/plan.md`, `pipeline-control`; added by this round after the publication round
  closed. Code revision `e2dcd2f`; working tree otherwise clean at task start.
- Accepted task: the full block added to the plan for this round.

```markdown
#### review-control-integration-boundaries

Review control producers accepted after the publication round before the first corpus stage
consumes them.

- Serves: `pipeline-control` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `repair-source-reconciliation-and-prune-safety`;
[Publication/reuse checkpoint](records/0046-pipeline-review-pipeline-publication-and-reuse-boundaries.md);
[Stage artifact inspection](records/0048-pipeline-add-stage-artifact-inspection.md);
[Incremental reconciliation and stale pruning](records/0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md);
[Package layout and Make](records/0050-govern-refactor-package-layout-and-make.md);
[Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md);
[Prerelease migration consolidation](records/0052-store-refactor-prerelease-migration-consolidation.md);
[Provided-archive control proof](records/0053-pipeline-prove-pipeline-control-on-provided-archive.md).
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked for the first corpus producers; no-refactoring-needed is a valid conclusion.
- Scope boundary: The control producers accepted after the publication round and their routed notes
only; no speculative rewrite, model upgrade or scope expansion, and no repetition of the publication
round's accepted evidence. Adding tests for important stabilized integrity, correctness, and
business-logic cases at these seams is in scope; concluding that existing tests already cover them
is valid. Restoring a numeric coverage floor is not. This verdict permits fixture implementation,
not real-data or CUDA promotion.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/proof artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read the full task snapshots and source changes for the named records; trace
source-scan completeness against withheld removals, last-occurrence versus shared content identity,
silo-scoped rename and path-event overlay agreement, reuse-entry staleness versus prune eligibility,
prune root containment, read-only inspection and evidence resolution, and frozen revision `0001`
coverage; replay representative existing tests; add tests for important integrity, correctness, and
business-logic cases these now-stable interfaces still miss; record concrete findings with evidence,
severity, affected consumers and one disposition each.
- Acceptance gates: Every named producer requirement has an evidence-backed disposition; the traced
invariants hold and `make ci` passes. Important stabilized cases have tests or an evidence-backed
conclusion that existing tests already cover them; a coverage percentage is not a gate. Create a
focused prerequisite repair task for any blocking finding and keep this checkpoint open until it
passes; preserve valid negative results and nonblocking follow-ups in the checkpoint record without
claiming a wider audit.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.
```

- Amendments: none.

## Implementation

This round exists because seven producer records were accepted after
[checkpoint 0046](0046-pipeline-review-pipeline-publication-and-reuse-boundaries.md) closed:
[0047](0047-pipeline-repair-pipeline-publication-and-reuse-integrity.md),
[0048](0048-pipeline-add-stage-artifact-inspection.md),
[0049](0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md),
[0050](0050-govern-refactor-package-layout-and-make.md),
[0051](0051-pipeline-implement-evidence-and-source-location-lookup.md),
[0052](0052-store-refactor-prerelease-migration-consolidation.md) and
[0053](0053-pipeline-prove-pipeline-control-on-provided-archive.md). Each declared
`none identified`, and 0046 could not have covered them. The first consumer of those seams is
`implement-streaming-inventory`, which emits the `arxiv-int.source-manifest.v1` contract that
`reconcile` already consumes, so the review is placed before that task rather than at the end of
the group.

Reviewed by reading each snapshot and its source, then executing the traced invariant directly
against the shipped modules. No production behavior was changed by this record; every repair is
owned by [0055](0055-pipeline-repair-source-reconciliation-and-prune-safety.md). The
[current-state page](../current/pipeline-control.md) is updated when that repair is accepted.

Each invariant below was traced by reading the shipped module and then either executing it directly
against the failing case or, where the invariant already had targeted coverage, replaying that
coverage. A `holds` verdict rests on code plus existing tests and the required CI gates, not on a
new probe for every row.

### Traced invariants

| Seam | Invariant | Outcome |
| --- | --- | --- |
| `reconcile/scan.py` completeness | An unreadable or unstable silo marks the scan incomplete and not comparable | holds |
| `reconcile/diff.py` withholding | Incomplete or non-comparable scans emit no `remove` event and no tombstone | holds |
| `reconcile/diff.py` rename identity | A rename stays inside one silo, matching the silo-scoped path-event overlay | fails; note 1 |
| `reconcile/commands.py` active view | Rows survive exactly the removals the delta withheld | fails; note 1 |
| `reconcile/closure.py` staleness | Only a last-occurrence removal invalidates a content-hash shard | fails; note 1 |
| `reconcile/scan.py` memory | Source hashing is bounded independently of file size | fails; note 1 |
| `prune/protect.py` protection | Active, pinned, reviewed, rollback, ledger, backup and sole-recovery trees refuse deletion | holds |
| `prune/apply.py` root containment | Apply never deletes a path outside `RUNS_DIR` | fails; note 1 |
| `prune/apply.py` event honesty | The persisted prune event reports what was removed | fails; note 1 |
| `query/evidence/validate.py` containment | Final and intermediate link escapes resolve to `escaped`, not a hash read | holds |
| `query/evidence/overlay.py` provenance | Path events never rewrite an occurrence's original path and never cross silos | holds |
| `query/evidence/ledger.py` import | Repeated import is idempotent; a conflicting `event_id` is refused and exits non-zero | holds |
| `inspect/artifacts.py` read-only | Summarizing an attempt rechecks checksums and leaves bytes unchanged | holds |
| `contracts` revision `0001` | A single frozen head publishes the control, progress, tombstone, prune and path-event tables | holds |

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Baseline suite before review | `make test` | pass; 1129 passed, 50 deselected (heavy) |
| Prune root containment | `tests/pipeline/prune/test_prune.py::test_apply_refuses_a_symlinked_escape_from_the_runs_root` | fails before repair, passes after |
| Withheld retraction | `tests/pipeline/reconcile/test_update.py::test_incomplete_scan_retracts_no_active_rows` | fails before repair, passes after |
| Shared-content staleness | `tests/pipeline/reconcile/test_diff.py::test_non_last_occurrence_removal_keeps_the_shard_live` | fails before repair, passes after |
| Cross-silo move identity | `tests/pipeline/reconcile/test_diff.py::test_a_move_between_silos_is_not_reported_as_one_rename` | fails before repair, passes after |
| Bounded source hashing | `tests/pipeline/reconcile/test_diff.py::test_scan_hashes_large_files_without_reading_them_whole` | fails before repair, passes after |
| Prune event honesty | `tests/pipeline/prune/test_prune.py::test_apply_records_removed_bytes` | fails before repair, passes after |
| Repair acceptance | [record 0055](0055-pipeline-repair-source-reconciliation-and-prune-safety.md) | pass; all six defects repaired with regressions |
| Affected suites after repair | `pytest tests/pipeline tests/evaluation/proof tests/inspect tests/query -m "not heavy"` | pass; 204 passed |
| Checkpoint coverage of later rounds | `arxiv_int.quality.plan_graph` transitive prerequisite closure per checkpoint | two ordering gaps found and corrected; see the handoff |
| Format and required CI | `make format`; `make ci`; `ci.log` | pass; 1136 passed, 50 deselected (heavy), up from the 1129 baseline |
| Documentation integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 0 broken links, 0 plan-integrity findings |

Evidence in this round is deterministic and network-free. The provided-archive evidence for the
repaired modules was produced separately by
[record 0056](0056-pipeline-reprove-pipeline-control-after-reconciliation-repair.md), whose proof
`0056-host` passes every control gate on the host with the archive unchanged. Neither this round
nor that bundle proves real-archive extraction quality or CUDA worker fit, and this verdict
promotes no real-data or human gate.

## Audit handoff

Coverage: the seven producer records accepted after the publication round, their source modules
under `src/arxiv_int/pipeline/reconcile/`, `src/arxiv_int/pipeline/prune/`,
`src/arxiv_int/query/evidence/`, `src/arxiv_int/inspect/`, and frozen revision `0001`. Coverage
limit, recorded after the fact: this round traced bounded hashing in the reconcile scanner but did
not sweep every other archive reader, and `snapshot_silos` in `pipeline/run/context.py` carries the
same whole-file read. It belongs to the earlier run-context producers rather than to the records
reviewed here, and is resolved by
[bounded archive snapshots](0059-pipeline-bound-archive-snapshot-hashing.md). Incoming
notes: none were routed to this round; `AUD-review-pipeline-publication-and-reuse-boundaries-2`
stays with the [corpus/control checkpoint](../plan.md#review-corpus-and-control-integrity) because
it explicitly waits on concrete corpus producers, which do not exist yet.

| Note | Finding / owner / disposition |
| --- | --- |
| `AUD-review-control-integration-boundaries-1` | Resolved blocker. Five reconcile/prune defects corrupt active derived state, plus one dishonest prune-event field. (a) `prune/apply.py` `_remove_tree` follows a directory symlink out of `RUNS_DIR`, deletes the target's files and then aborts on `rmdir`, leaving a half-deleted tree and no prune event; the `refusing to delete path outside RUNS_DIR` guard only inspects the top-level target. (b) `reconcile/commands.py` `_active_view` retracts every row whose content hash is absent from an incomplete scan, so a missing or unreadable silo retracts rows whose removals the delta deliberately withheld. (c) `reconcile/closure.py` `_invalidation_roots` invalidates a content-hash shard for any `remove`, so deleting one of several identical files marks a still-supported document's live reuse entry stale and therefore prune-eligible. (d) `reconcile/diff.py` `_pair_renames` pairs removals and additions across silos, emitting a `path-rename` whose `previous_path` never existed in the reported silo and suppressing the removal record; the silo-scoped path-event overlay cannot represent it. (e) `reconcile/scan.py` `_read_occurrence` calls `path.read_bytes()`, so peak memory scales with the largest archive object. (f) `prune/apply.py` `_write_event` stores a directory count in `bytes_removed`. Affected consumers: `implement-streaming-inventory`, `prove-corpus-foundation-on-provided-archive` and every operator running `artifacts prune --apply`. [Owner repair 0055](0055-pipeline-repair-source-reconciliation-and-prune-safety.md). |
| `AUD-review-control-integration-boundaries-2` | Nonblocking. `reconcile/scan.py` `_iter_files` skips every symlinked source file while still reporting the silo `complete`, so an archive whose files were replaced by links scans clean and its prior occurrences become last-occurrence removals. Reconcile's scanner is a stand-in for the real inventory walker, which owns link, quarantine and unsupported-input policy. Next check: the inventory stage must classify links explicitly rather than omit them, and reconcile must consume that classification. [Resolved by inventory 0060](0060-corpus-implement-streaming-inventory.md): explicit link classifications and verified reconciliation input withhold removals and tombstones in the passing regression. |

### Audit of the later checkpoints

This round and the plan's eight other open checkpoints were checked against the
specification's enumerated placements and against the transitive prerequisite closure of each
round, so that no checkpoint can run before a producer it claims to review. Two ordering gaps
were found and corrected in the plan:
`provision-local-dashboards-and-age-viewer` named `review-investigation-and-report-integrity` as its
round without being one of its prerequisites, and `implement-published-evidence-freshness-checks`
named `review-production-readiness-and-recovery` the same way. Both are now explicit dependencies,
so neither round can close before the work it reviews exists.

Three patterns were checked and found correct rather than defective. A `prove-*-on-provided-archive`
task names its round without being a prerequisite of it, which is right: the checkpoint releases the
proof, and the workflow forbids a checkpoint depending on the consumer it must release. Human
`approve-*` and `accept-*` tasks do the same, keeping proof and human gates separate. The optional
`add-cited-local-question-answering` refinement is correctly ordered after required work rather than
before its round. One observation carries no defect: `review-semantic-branch-integrity` has no
dependent task, because semantic retrieval is a terminal branch; its round releases operator use of
that branch rather than another planned task, and the workflow explicitly allows naming the blocked
operation instead of inventing a successor.

Note 1 is closed: repair 0055 reproduced all six defects as failing regressions, repaired them, and
passed the affected suites and required CI.

Refactor verdict: targeted refactor needed, bounded to the reconcile and prune seams and owned by
repair 0055. No broader rewrite, model promotion or dependency change is warranted; inspection,
evidence lookup, package layout and revision `0001` need no change. Checkpoint verdict:
**proceed-with-nonblocking-notes** for the first corpus producers, now that repair 0055 has passed.

## Close or resume

Accepted. Repair 0055, the affected suites, `make ci`, `make lint-doc-links` and `make lint-spec-plan`
pass. Both plan tasks are removed and dependents link these records; `implement-streaming-inventory`
now depends on this accepted round and carries note 2. Counts moved from 66 to 68 tasks while both
tasks were open, then back to 66 (56 agent, 10 human unchanged) on acceptance. No capability changed
status: `pipeline-control` keeps its planned corpus stages and the
[corpus/control checkpoint](../plan.md#review-corpus-and-control-integrity), whose own
`AUD-review-pipeline-publication-and-reuse-boundaries-2` still waits on concrete corpus producers.
Next agent work: `implement-streaming-inventory`. This verdict permits fixture implementation only;
it promotes no real-data, CUDA or human gate. No review-owned service was started or left running.
