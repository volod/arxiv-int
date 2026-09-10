# Bounded Archive Snapshot Hashing

## Task and scope

- Id: `bound-archive-snapshot-hashing`; capability: `pipeline-control`.
- Checkpoint: `review-corpus-and-control-integrity`.
- State: accepted; all required gates passed.
- Source: `docs/impl/plan.md`; revision `f9ef53e`; initially clean working tree.
- Initial plan count: 67 tasks (57 agent, 10 human); selected by `make plan-status`.
- Dependencies reviewed: records 0055 and 0042, including their audit dispositions.
- Amendments: none.

```markdown
#### bound-archive-snapshot-hashing

Stop rehashing whole archive files into memory when a run is created and on every later command.

- Serves: `pipeline-control` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: [Source reconciliation and prune safety](records/0055-pipeline-repair-source-reconciliation-and-prune-safety.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md).
- User-visible outcome: `run create`, `stage`, `status` and `resume` stay usable on a
multi-terabyte archive instead of reading every file whole and rehashing the entire archive on each
command.
- Scope boundary: The run-context source snapshot and its drift check only; no inventory stage, no
new manifest contract, and no change to what counts as configuration drift.
- Data and artifact paths: `src/arxiv_int/pipeline/run/context.py`,
`src/arxiv_int/pipeline/commands.py`, `src/arxiv_int/pipeline/dag/actions.py`; mirrored tests under
`tests/pipeline/run/`.
- Execution path: Hash file bytes in bounded chunks through the shared reader already used by
attempt manifests and the source scan; decide and record whether the per-command drift check needs
full content or cheaper stable metadata, and keep the chosen rule explicit in the run context so a
stale snapshot still refuses. Preserve the existing `StaleUpstreamError` behavior.
- Acceptance gates: Peak memory during a snapshot stays bounded independently of the largest file;
a changed archive still raises `StaleUpstreamError` and an unchanged archive still loads; symlinked
and unreadable entries keep their current treatment. Run the pipeline suites and `make ci`.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Implementation

`pipeline/run/snapshot.py` reuses `pipeline.control.artifacts.hash_file` (1 MiB chunks),
streams aggregate hash input, and preserves the previous ordered path/content digest including
text normalization and trailing newline. `context.py` retains the `snapshot_silos` import seam.
Sorted pathlib traversal still uses memory proportional to path count, but no file-sized buffer.

`commands.create_run_context` and `dag.actions.update_context` bracket content hashing with two
metadata scans; differing scans raise `StaleUpstreamError` before a new context is persisted.
`run/persist.py` stores `source_drift_policy` and `source_metadata_snapshot` with the existing
run context. New runs use `stat-v1`: silo-relative identity, device, inode, size, nanosecond mtime
and ctime, mode, uid and gid. Atime is excluded. `require_frozen_context` compares only metadata
for that policy after the unchanged configuration-drift check. Update refreshes both snapshots;
rebuild preserves both. Identical content keeps its content identity across an explicit update.

Command tracing also found that `dag/dispatch.py` loaded status/resume without the documented
frozen-context guard. Both now use that guard, and stage passes its already-resolved project root
so an unchanged run from an explicit checkout loads against the correct configuration. This stays
within the task's named stage/status/resume drift-check scope; parsing and what counts as
configuration drift are unchanged. Stale-source guidance now recommends `pipeline update` because
resume also refuses changed sources. Two command regressions first reproduced stale status acceptance
and stale resume reaching its worker. Command tests now cover stage/status/resume refusal and
unchanged execution with all source opens prohibited.

Decision: full hashing remains necessary at create/update to preserve source content identity;
per-command full hashing is replaced by stable metadata. This guard detects ordinary edits,
same-size edits with restored mtime, replacements, add/remove/rename and permission changes.
Touching or replacing identical bytes can conservatively refuse. Reliable local filesystem stat
fields and stable sources during execution are assumed; this is neither an atomic filesystem
snapshot nor protection against changes invisible to every selected metadata field. File-open
errors propagate during content hashing; pathlib enumeration behavior and skipped symlinks/empty
directories remain unchanged. Missing silos retain their marker.

Contexts missing both new fields retain `full-content-v1` with chunked full-content checks;
explicit update moves them to `stat-v1`. Unknown policies, missing metadata evidence or metadata
attached to the full-content policy refuse. There is no manifest contract, inventory worker,
dependency, configuration drift, or GPU model change. The relevant specification section and
[current pipeline behavior](../current/pipeline-control.md) describe the selected rule.

## Acceptance evidence

Evidence root: `$DATA_DIR/archive-snapshot/0059-host/`. Commands run from the project root.
Before direct uv calls: `source scripts/shared/common.sh` then `arxiv_int_load_env`.
`UV_CACHE_DIR="$DATA_DIR/cache/uv"` uses a writable tool cache; no project cache policy changed.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Failing regressions first | `uv run --no-sync pytest tests/pipeline/run/test_snapshot.py -q`; `regressions-before.log` | Both whole-file allocation and archive reread assertions fail before the fix |
| Bounded reads and identity | `tests/pipeline/run/test_snapshot.py` | Pass; original normalized digest, ordering, multiple silos and empty/missing inputs preserved |
| Bounded memory | `test_snapshot_memory_is_independent_of_file_size` | Pass; 4/64 MiB synthetic files stay below 4 MiB traced allocations with less than 1 MiB peak difference |
| Host create/load/update measurement | `uv run --no-sync python "$DATA_DIR/archive-snapshot/0059-host/measure.py"`; `measurement.json` | Pass; synthetic 8/512 MiB files use 2,116,367/2,110,544 peak Python bytes; process peak RSS stays 57,396 KiB; five unchanged loads per size open no source files; same-size restored-mtime edit refuses and updated context loads |
| Atomic command integration | `tests/pipeline/run/test_command_drift.py`; `command-regressions-before.log` | Two stale-command regressions failed before dispatch repair; six command cases pass afterward |
| Frozen context and drift | `tests/pipeline/run/test_context_drift.py` | Pass; content/path/permission drift, unchanged reads, config precedence, no-op update, rebuild, legacy checks and invalid policy evidence |
| Race and source treatment | `tests/pipeline/run/test_snapshot.py` | Pass; mutation of an already-hashed file refuses, symlinks remain skipped and injected unreadable-file error propagates |
| Pipeline suites | `uv run --no-sync pytest tests/pipeline -m 'not heavy'`; `pipeline.log` | 215 passed, 1 skipped in sandbox; skipped CUDA test rerun below |
| CUDA host test | `uv run --no-sync pytest tests/pipeline/forecast/test_cuda.py -ra`; `cuda-forecast.log`, `cuda-host.txt` | 1 passed outside sandbox; RTX 4060 Ti, 16,380 MiB, driver 595.84; forecast assumptions only, no model-fit claim |
| Formatting and required CI | `make format`; `UV_CACHE_DIR="$DATA_DIR/cache/uv" make ci`; `ci.log` | Pass outside sandbox; 1,165 passed, 50 heavy deselected in 188.34 seconds; all CI checks pass |
| Optional Markdown diagnostic | `make lint-md`; `markdown-final.log`, `markdown-baseline.json` | 23 existing MD013 violations; every offending line verified unchanged from HEAD; unrelated lines preserved |
| Final documentation integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | Pass; 0 broken links and 0 plan findings; 66 tasks (56 agent, 10 human) |

The initial direct uv command and first CI attempt failed on the sandbox's read-only default uv
cache; the latter is retained in `ci-cache-refusal.log`. Re-running with the writable cache passed
that step. The next sandbox CI run had 18 failures, all local fixture socket creation denied
with `PermissionError`; see `ci-sandbox-socket-refusal.log`. Full CI then passed outside the sandbox;
`ci-before-command-guard.log` retains that intermediate
1,159-test pass. After the command-path repair, final `ci.log` records the complete 1,165-test pass.
The sandbox GPU probe could not reach the driver; the external read-only probe and
forecast test above succeeded. Synthetic source and operator-output directories were removed by
the measurement's temporary-directory context manager; the script, measurements and code SHA-256
fingerprints remain in the evidence root. This task ran no provided-archive scan and establishes
neither multi-terabyte traversal throughput, extraction quality nor CUDA worker fit.

## Audit handoff

Reviewed source digest compatibility, shared reader reuse, metadata field selection, atime,
creation/update consistency, legacy persistence, refusal policy, rebuild behavior, traversal
semantics and allocation evidence. Unresolved task-local notes: `none identified`.
The coverage gap named in
[checkpoint 0054](0054-pipeline-review-control-integration-boundaries.md#audit-handoff)
is addressed by this task. Existing source-link inventory policy remains owned by
[streaming inventory](0060-corpus-implement-streaming-inventory.md). The metadata guard's documented
filesystem/race limits remain an input to
[the corpus/control checkpoint](0063-corpus-review-corpus-and-control-integrity.md).

## Close or resume

Accepted after the regressions, pipeline suite, host measurement, CUDA forecast test and full CI
passed. The satisfied task and its now-empty capability heading were removed from the plan;
the corpus/control checkpoint and earlier coverage-gap note link this accepted record.
Current pipeline behavior, the current-state index, record index, portable-runtime corpus link
and capability registry are updated. `pipeline-control` is shipped for its generic control scope;
concrete corpus stages and their integration/proof remain planned under `corpus-foundation`.

Plan counts moved from 67 to 66 tasks (57 to 56 agent, 10 human unchanged). Next eligible agent:
`implement-streaming-inventory`; it was not started. No human review handoff belongs to this task.
Final `git status` was inspected; only task-scoped code, tests and documentation changed. No commit
or push was made. Test fixture servers finished with CI; no task-owned service remains running.
The measurement removed its temporary source/output tree and retained its evidence under
`$DATA_DIR/archive-snapshot/0059-host/`. The optional Markdown diagnostic still reports the 23
pre-existing line-length findings; none was introduced by this task.
