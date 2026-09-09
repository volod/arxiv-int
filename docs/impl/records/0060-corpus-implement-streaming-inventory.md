# Streaming Inventory

## Task and scope

- Id: `implement-streaming-inventory`; capability: `corpus-foundation`.
- Checkpoint: `review-corpus-and-control-integrity`.
- State: accepted; required CI, fixture acceptance and full configured-archive inventory pass.
- Source: `docs/impl/plan.md`; revision `4fd3e9c`; initially clean working tree.
- Initial count: 66 tasks (56 agent, 10 human).
- Amendments: none.

```markdown
#### implement-streaming-inventory

Build a content-addressed, restartable archive inventory with format, encoding, hash, and quarantine
metadata.

- Serves: `corpus-foundation` -- [Pipeline](../design/spec.md#pipeline)
- Agent status: RUN NEEDED
- Dependencies: [Control integration checkpoint](records/0054-pipeline-review-control-integration-boundaries.md);
[Source reconciliation and prune safety](records/0055-pipeline-repair-source-reconciliation-and-prune-safety.md);
Runtime roots documented in [Portable runtime](current/portable-runtime.md);
[Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md);
[Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md).
[Publication/reuse checkpoint](records/0046-pipeline-review-pipeline-publication-and-reuse-boundaries.md).
- Audit inputs: [AUD-review-control-integration-boundaries-2](records/0054-pipeline-review-control-integration-boundaries.md#audit-handoff).
- User-visible outcome: The operator can inventory one or more multi-terabyte silos without loading
them into RAM and can see per-silo coverage, bytes, duplicates, and unsupported/encrypted inputs.
- Scope boundary: Read files and archive-member metadata only; no text extraction and no
modification of source files.
- Data and artifact paths: Declared source roots from `$ARCHIVE_DIR`, used without modification;
`$RESULTS_DIR/normalized/inventory/`; `$RUNS_DIR/<run-id>/`; `src/arxiv_int/pipeline/inventory/`.
- Execution path: Resolve the declared silo ids and roots; stream directory entries, carry silo id
with root-relative path metadata, detect MIME/encoding, compute strong hashes for content identity
(quick hashes only select candidates), verify file
stability across reads, record completed source-set scope and container/member identities, enforce
archive-bomb limits, shard by stable id, and write atomic Parquet manifests; register
the stage in the existing registry and expose `arxiv-int stage inventory` plus
`make stage STAGE=inventory` in the same change,
then run that command on a bounded authorized archive when available and inspect its artifacts.
Use PyArrow batch writers and contract-derived Pandera checks before sealing partitions;
record completed global occurrence-key checks and reject batches with invalid provenance.
- Acceptance gates: Network-free fixtures cover large/sparse files, links, permission errors,
renamed duplicates, nested archives, encrypted files, interruption, and resume; two silos sharing one
root-relative path stay distinct while identical bytes resolve to one content identity; memory is
bounded independently of file count; fixture stage run and artifact summary are recorded without
private content or machine-specific
paths; provided-archive acceptance is tracked by its separate proof task.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Implementation

`pipeline/inventory/` owns bounded discovery, strong file/member hashes, MIME/encoding probes,
quarantine policy, disk checkpoints, contract validation, partitions and the production adapter.
It reuses `StageRunner`, `source-occurrences` ODCS/Arrow/Pandera assets, shared activation policy,
owned fingerprints, runtime roots, cancellation and the normal stage artifact publisher.
The source-occurrences contract and canonical SQL schema are unchanged. SQLite tables are internal
transactional checkpoint/index state; operational JSONL metadata sidecars carry MIME, encoding,
size, parent identity and quarantine reasons alongside canonical occurrence rows.

The default policy streams 1 MiB reads, bounds samples to 64 KiB, caps directory depth at 64,
uses 16 stable occurrence-id buckets and writes at most 256 rows per Parquet file. ZIP/TAR policy
bounds depth, member count, member bytes, total expansion, compression ratio and ZIP central-directory
allocation. ZIP64/multidisk and unsupported compression/containers are explicit refusals.
One byte-probe policy covers both physical files and members; no text extraction or source write
occurs. `charset-normalizer==3.5.1`, already in the transitive lock, is now a declared lake dependency
for bounded Windows-1251/KOI8-R encoding candidates; `make lock` updates direct ownership only.

Each stable file transaction is resumable. Failed/unstable files retry, observed source-set changes
prevent sealing, and process interruption leaves the current file transaction uncommitted.
The worker also compares its starting metadata to the frozen run snapshot, preventing a source
change between command loading and worker start from using the old run identity.
Global key uniqueness is enforced on disk before publication; generated Pandera checks validate
materialized batches, including the contract partition key, before atomic partition renames.
The checksum index is streamed and the snapshot manifest is sealed last. New publication attempts
never overwrite earlier snapshots. Inspection recognizes the physical `inventory` location as the
`source-occurrences` contract and omits unsealed scratch. Cache reuse rehashes all referenced files.
Archive scratch follows resolved `TMP_DIR`; output and scratch reject protected-root overlap.

Integration required replacing the production command path's eager per-content scheduling before
inventory: source-set scheduling invokes the inventory once and its buckets partition the output.
Fixture DAGs keep their earlier content-shard behavior. The existing production quality adapter
continues refusing unimplemented producers. Preflight/inventory instead execute scope/containment
preconditions; inventory supplies real completed dataset and global-key evidence to the shared
activation boundary. No fixture success is substituted for a production validator.

New production runs declare `inventory-stat-v1`: a counted, order-independent metadata change
detector, with explicit link/error classification and no source-byte read at creation/update.
This is not content identity. Content SHA-256 is computed during inventory. Existing `stat-v1` and
full-content contexts keep their original behavior. The specification now distinguishes these
policies. This necessary command-path integration implements the task's bounded-memory and single
inventory-read requirements; it adds no unrelated capability. The historical legacy-context test
now constructs an actual content snapshot, and the registration assertion now expects inventory to
be shipped. Configuration-drift policy remains unchanged.

Reconciliation reuses the explicit source-entry classification and can adapt a sealed inventory
into its existing source-manifest interface. Links and unobservable sources withhold comparable
removals. That older reconciliation/delta interface still materializes occurrence sets; no
archive-scale reconciliation acceptance is claimed. Current behavior and exact archive limits are
in [Corpus foundation](../current/corpus-foundation.md).

## Acceptance evidence

Evidence root: `$DATA_DIR/inventory/0060/`. Before every direct uv call:
`source scripts/shared/common.sh`, then `arxiv_int_load_env`;
`UV_CACHE_DIR="$DATA_DIR/cache/uv"` selects the writable tool cache.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Prerequisites and selection | `make plan-status`; records 0010, 0042, 0044, 0046, 0054, 0055 and current runtime boundaries | Accepted prerequisites; initial 66 tasks, 56 agent and 10 human |
| Link regression before fix | `link-regression-before.log`; execute the HEAD scanner on a synthetic broken link | Expected assertion failure: the previous scanner reports a comparable source set while omitting the link |
| Frozen-source race | `frozen-race-before.log`; `frozen-race-after.log`; `test_source_change_before_worker_cannot_use_frozen_identity` | Reproduced acceptance of a changed source set before the guard. The regression and seven related source/control checks now pass |
| Inventory acceptance | `uv run --no-sync pytest tests/pipeline/inventory -q`; `inventory-final.log`, `inventory-collection.log` | 31 network-free cases; final CI covers all cases: source/member identities, multiple silos, formats/encodings, sparse files, links, errors, limits, provenance, interruption/resume, cache integrity and source/scratch containment |
| Related integration | `uv run --no-sync pytest tests/pipeline/inventory tests/inspect tests/pipeline/dag tests/pipeline/run tests/pipeline/reconcile -m 'not heavy' --tb=short`; `focused-final.log` | 135 cases passed before the last shared member-policy regression; final CI covers the complete set |
| Bounded source reads | `test_sparse_file_read_memory_is_bounded` | 4/64 MiB sparse files stay below 5 MiB traced Python allocations with less than 1 MiB peak difference |
| Bounded file-count state | `test_file_count_does_not_accumulate_python_inventory` | 100/2,500 files stay below 1 MiB traced checkpoint/walker allocations with less than 512 KiB peak difference |
| Whole-stage host memory | `uv run --no-sync python "$DATA_DIR/inventory/0060/measure-memory.py" 100` and `5000`; `memory-100.json`, `memory-5000.json` | 100/5,000 complete published rows: 126,400/130,176 KiB peak RSS, 0.80/25.15 seconds. Synthetic local measurement, not archive throughput proof |
| Normal operator commands | `uv run --no-sync python "$DATA_DIR/inventory/0060/fixture-command.py"`; `fixture-*.log`, `fixture-summary.json` | Make run-create, forecast, preflight, inventory, refreshed forecast, repeated inventory and inspect pass. Six occurrences, five source entries, 8,388,776 source bytes, one duplicate and two quarantines |
| CUDA host | `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader`; `uv run --no-sync pytest tests/pipeline/forecast/test_cuda.py -ra` | Pass; RTX 4060 Ti, 16,380 MiB, driver 595.84. Forecast test only; inventory has no GPU worker |
| Full archive execution | Local execution logs, manifests and independent artifact checks | Pass: complete physical-file hashing, valid partitions and cache reuse; unsupported inputs and incomplete member coverage remain explicit |
| Dependency ownership | `make lock`; `lock.log` | Pass on host; no package-version churn. Offline attempt lacked cached registry metadata |
| Formatting and required CI | `make format`; `make ci`; `ci.log` | Final host run passes 1,196 tests, 50 heavy deselected, in 203.23 seconds. Prior runs passed 1,195 and 1,186 tests. Sandbox attempt could not resolve build requirements; `ci-sandbox-network.log` retains that failure |
| Dependency-change diagnostics | `make -k quality`; `quality.log` | Completed before the final source guard: 1,195 tests pass, 87% diagnostic coverage, source/wheel builds pass. Only 23 pre-existing MD013 findings fail; all offending lines match HEAD, verified in `markdown-baseline.json`. Final local build is retained separately in `build-final.log` |
| Documentation integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | Pass; zero broken links and zero plan findings. Final count: 65 tasks, 55 agent and 10 human. |

The fixture script creates ordinary operator roots in a temporary directory, runs the unmodified
Make entrypoints and copies only synthetic summaries/logs into tooling evidence before removing
those temporary operator roots. Source bytes and private paths are not committed. Refreshed
forecasts are required when the cache plan changes; initial missing/stale-forecast refusals informed
the final command sequence. Earlier contract validation correctly refused a missing partition key;
the producer now includes the contract-derived bucket column.

## Archive inventory quality conclusion

Full execution on an operator-provided archive passed through the normal Make workflow. Every
physical file was accounted for and strongly hashed. Published partitions passed checksum and
contract validation; metadata agreed with Parquet rows, and inspection found no schema drift.
An unchanged rerun reused the validated snapshot successfully.

Unsupported formats, encryption indicators and incomplete container enumeration remained explicit
quarantine outcomes. Successful physical-file coverage does not imply complete member coverage or
extraction quality. Fixture checks support bounded working memory; the archive run alone does not
establish multi-terabyte performance or GPU fit.

Detailed run identities, measurements and manifests remain in local evidence and configured operator
outputs. They are not prerequisites for another checkout. Use the
[operator workflow](../current/corpus-foundation.md#operator-workflow) to validate a new environment.
The separate complete corpus proof remains open for downstream stages and review prerequisites.

## Audit handoff

Unresolved task-local audit notes: `none identified`.

Incoming `AUD-review-control-integration-boundaries-2` is resolved by explicit link rows, the shared
walker/read policy, and the verified inventory-to-reconciliation adapter. The regression reproduces
the original omission and now verifies that link replacements emit neither removals nor tombstones.

No new blocking concern remains in the reviewed inventory scope. The source-start race is fixed
with a failing regression and final CI coverage. The existing
`review-corpus-and-control-integrity` checkpoint owns the downstream integration and scale review,
including the older materialized reconciliation interface and database activation requirements.
The 23 existing Markdown findings retain that checkpoint's existing diagnostic-debt ownership
from `AUD-review-pipeline-publication-and-reuse-boundaries-2`; no lint rule or gate was weakened.
The standalone archive inventory evidence above does not promote the complete corpus proof,
extraction-quality, model-fit or a human decision.

## Close or resume

Accepted. Final `make ci`, all 31 inventory cases, normal Make fixture execution and the CUDA
forecast test pass. Quality diagnostics ran: the pre-guard coverage run passed 1,195 tests with
87% diagnostic coverage, and only 23 unchanged Markdown line-length findings failed. The final
source and wheel builds include the frozen-source guard. Diagnostic coverage is not an acceptance
gate; its earlier fingerprints are retained separately from the final code fingerprints.

Updated the corpus current-state page, pipeline/runtime/operator guidance and indexes. Resolved the
incoming link-policy audit note, replaced removed-task links with this record, and removed only
`implement-streaming-inventory` from the forward plan. Counts moved from 66 to 65 tasks (56 to
55 agent; 10 human unchanged). Next eligible agent task: `integrate-tiered-text-extraction`.
The inventory stage is available; the overall corpus capability remains planned for extraction,
normalization/chunking, its integration checkpoint and provided-archive proof. That proof remains
open; full standalone inventory now passes, while the downstream corpus stages remain planned.

No human-review handoff applies. No service or model process was started. All task commands exited;
temporary operator roots were removed by their context managers. Tooling evidence and final
source/dependency fingerprints remain under `$DATA_DIR/inventory/0060/`. No commit or push was made.
