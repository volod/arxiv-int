# Source Reconciliation and Prune Safety Repair

## Task and scope

- Id: `repair-source-reconciliation-and-prune-safety`; capability: `pipeline-control`.
- State: accepted; required regressions, affected suites and `make ci` pass.
- Source: blocking note in
  [checkpoint 0054](0054-pipeline-review-control-integration-boundaries.md#audit-handoff).
  Code revision `e2dcd2f`; dirty scope limited to the modules and tests listed below.
- Accepted task: the full block added to the plan for this repair.

```markdown
#### repair-source-reconciliation-and-prune-safety

Repair source-reconciliation and prune defects that corrupt active derived state before corpus
producers depend on them.

- Serves: `pipeline-control` -- [Resumability](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: [Incremental reconciliation and stale pruning](records/0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md);
[Provided-archive control proof](records/0053-pipeline-prove-pipeline-control-on-provided-archive.md).
- Audit inputs: [AUD-review-control-integration-boundaries-1](records/0054-pipeline-review-control-integration-boundaries.md#audit-handoff).
- User-visible outcome: An unreadable silo, a duplicate-file removal, a cross-silo move and a
symlinked attempt tree leave active derived rows, live reuse entries and out-of-root files intact.
- Scope boundary: Existing `reconcile` and `prune` seams and their honest artifacts only; no
concrete corpus workers, no inventory stage, no new scanner framework and no store adapter.
- Data and artifact paths: `src/arxiv_int/pipeline/reconcile/`, `src/arxiv_int/pipeline/prune/`,
mirrored tests under `tests/pipeline/`; `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Add failing regressions first, then repair: refuse prune deletion that would
follow a directory symlink out of the runs root; withhold active-view retraction for exactly the
silos whose removals were withheld; invalidate a content-hash shard only on a last-occurrence
removal; pair renames within one silo and carry the previous silo id on the delta contract; hash
source files in bounded chunks; record removed bytes rather than a directory count on the prune
event.
- Acceptance gates: An unreadable or partial silo retracts nothing and prunes nothing; removing one
of several identical files keeps its shard live and non-eligible for prune; a cross-silo move never
reports a previous path that did not exist in the reported silo; prune refuses symlinked escapes
and leaves both trees intact; peak scan memory stays bounded independently of file size; prune
events report bytes. Run the reconcile, prune and proof suites plus `make ci`.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-control-integration-boundaries`.
```

- Amendments: none.

## Implementation

Six defects in the accepted reconciliation and prune seams
([record 0049](0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md)) were
repaired. Each behavior change is a defect fix; no public interface gained an alias and no
compatibility shim was added, because nothing is released.

**Prune deletion refuses before it starts** -- `pipeline/prune/apply.py` previously validated only
the top-level target of each listed directory, then walked the tree with `child.is_dir()`, which
follows a directory symlink. A link inside a stale attempt therefore emptied its target outside
`RUNS_DIR` and then raised `NotADirectoryError` on `rmdir`, leaving a half-deleted tree, an
unsaved reuse index and no prune event. `_delete_listed` is replaced by `_checked_targets`, which
validates every listed directory -- protection, root containment and a recursive symlink check --
before a single byte is removed, so a refusal leaves both trees intact. `_remove_tree` now returns
the bytes it removed and is only ever called on a checked tree.

**Withheld removals no longer retract rows** -- `pipeline/reconcile/commands.py` `_active_view`
retracted every row whose content hash was missing from the current scan, so a missing or
unreadable silo retracted rows whose removals `diff_manifests` had deliberately withheld. The
extra retraction pass now applies only to rows every one of whose supporting paths lies in a silo
that both scans completed, using the same rule the diff uses for removals
(`_observable_silos` / `_fully_observed`).

**Only a last-occurrence removal invalidates a shard** -- `DeltaEvent` gained `content_remains`,
set by `diff_manifests` from the current content counts. `reconcile/closure.py` skips those events
in `affected_hashes` and `_invalidation_roots`, so deleting one of several identical files no
longer marks the still-supported document's live reuse entry stale, and therefore no longer makes
it prune-eligible. `tombstones_for` now reads the same flag instead of recomputing the counts, so
the tombstone and the closure cannot disagree.

**Renames stay inside one silo** -- `_pair_renames` keyed candidates by content hash alone and
paired across silos, emitting a `path-rename` whose `previous_path` never existed in the reported
silo and suppressing the removal record for the silo the file left. It now keys by
`(silo_id, content_hash)`, so a move between silos is an honest remove plus add with
`content_remains` true. `DeltaEvent` also carries `previous_silo_id`, and its `__post_init__`
refuses a previous path that names no silo; `reconcile/persist.py` writes both new fields. This
matches `query/evidence/overlay.py`, whose path-event overlay already ignores events from another
silo.

**Bounded source hashing** -- `reconcile/scan.py` `_read_occurrence` called `path.read_bytes()`, so
peak memory scaled with the largest archive object. The chunked reader already used by attempt
manifests is promoted from `pipeline/control/artifacts._hash_file` to a public `hash_file` and
reused here rather than duplicated.

**Honest prune events** -- `_write_event` stored a directory count in `bytes_removed`. The event
now records measured `bytes_removed` and a separate `directories_removed`; the command log and the
`apply_prune_plan` return value keep their existing directory-count meaning.

Limitations: these are fixture and disposable-store seams. Nothing here proves real-archive
extraction quality or CUDA worker fit, and the reconcile scanner remains a stand-in for the
planned inventory walker. See [pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Failing regressions first | `pytest tests/pipeline/reconcile tests/pipeline/prune`; `regressions-before.log` | 7 reproduced failures across diff, closure, scan, active view and prune |
| Prune refuses a symlinked escape | `tests/pipeline/prune/test_prune.py::test_apply_refuses_a_symlinked_escape_from_the_runs_root` | pass; the out-of-root file and the attempt tree both survive |
| Prune event honesty | `tests/pipeline/prune/test_prune.py::test_apply_records_removed_bytes` | pass; measured bytes match the trees deleted |
| Incomplete scan retracts nothing | `tests/pipeline/reconcile/test_update.py::test_incomplete_scan_retracts_no_active_rows` | pass; withheld removals and zero retractions |
| Shared content keeps its shard | `tests/pipeline/reconcile/test_diff.py::test_non_last_occurrence_removal_keeps_the_shard_live` | pass; tombstone not last-occurrence, closure empty |
| Cross-silo move identity | `tests/pipeline/reconcile/test_diff.py::test_a_move_between_silos_is_not_reported_as_one_rename` | pass; remove plus add, tombstone stays with the losing silo |
| Same-silo rename preference | `tests/pipeline/reconcile/test_diff.py::test_rename_prefers_the_pairing_inside_one_silo` | pass; previous silo id equals the reported silo |
| Bounded source hashing | `tests/pipeline/reconcile/test_diff.py::test_scan_hashes_large_files_without_reading_them_whole` | pass; whole-file read refused, digest still correct |
| Affected suites | `pytest tests/pipeline tests/evaluation/proof tests/inspect tests/query -m "not heavy"` | pass; 204 passed |
| Required CI | `make format`; `make ci`; `ci.log` | see the checkpoint record's evidence table |
| Documentation integrity | `make lint-doc-links`; `make lint-spec-plan` | 0 findings |

Evidence above is deterministic and network-free. No provided-archive run was declared inside this
repair's own scope, so the gap was routed to a separate task rather than left implicit:
[record 0056](0056-pipeline-reprove-pipeline-control-after-reconciliation-repair.md) republished the
provided-archive bundle on this repaired code as proof `0056-host`, with every control gate passing
and the archive fingerprint unchanged. Record 0053's `0053-host-2` is superseded as current
evidence and remains the account of the code it proved.

## Audit handoff

Reviewed prune pre-validation versus partial deletion, symlink handling at every tree level,
byte accounting, withheld-removal symmetry between the diff and the active view, tombstone and
closure agreement on last-occurrence content, silo-scoped rename pairing against the path-event
overlay, and chunked hashing reuse rather than a second implementation.

`none identified`.

## Close or resume

Accepted. All listed regressions, the affected suites and `make ci` pass. This resolves the blocking
note in [checkpoint 0054](0054-pipeline-review-control-integration-boundaries.md#audit-handoff),
which closes in the same change. Plan task removed; dependents link this record. Counts moved from
68 to 66 tasks (58 to 56 agent; 10 human unchanged) once both this repair and checkpoint 0054 were
removed. No review-owned service was started or left running.
