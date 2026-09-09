# Normalization, Dedupe and Chunking

## Task and scope

- Id: `implement-normalization-dedupe-and-chunking`; capability: `corpus-foundation`.
- Checkpoint: `review-corpus-and-control-integrity`.
- State: accepted; deterministic and bounded CUDA-host fixture evidence passed.
- Source: `docs/impl/plan.md`; code revision `b2331c9`; initially clean working tree.
- Initial count: 64 tasks (54 agent, 10 human).
- Amendments: none.

```markdown
#### implement-normalization-dedupe-and-chunking

Normalize extracted text, group exact/near duplicates and editions, and emit source-aligned chunks
without destructive corpus edits.

- Serves: `corpus-foundation` -- [Normalized data lake](../design/spec.md#normalized-data-lake)
- Agent status: RUN NEEDED
- Dependencies: [Tiered text extraction](records/0061-corpus-integrate-tiered-text-extraction.md).
- User-visible outcome: Each unique document has searchable, table/structure-aware chunks and
reversible duplicate/edition overlays.
- Scope boundary: Normalize and propose duplicate groups; do not merge entities or delete
source/extracted records.
- Data and artifact paths: `$RESULTS_DIR/normalized/documents/`, `spans/`, `chunks/`, duplicate overlays,
`src/arxiv_int/pipeline/normalize/`, and `src/arxiv_int/pipeline/chunk/`.
- Execution path: Preserve original text; create NFC/casefold/search views; map
original-to-normalized offsets; detect language; run exact, normalized, MinHash/lexical, and
edition grouping; implement bounded structure/table/sentence chunkers with source breadcrumbs;
register the normal stage commands and run them against a bounded authorized archive when available.
Express tabular normalization and grouping with typed Polars expressions and PyArrow batches;
keep text/span algorithms in focused Python functions. Run generated Pandera checks, cross-partition
identity checks and bounded-memory tests before publishing.
- Acceptance gates: Golden offsets and table headers survive chunking; unchanged input yields stable
ids; dedupe precision is measured on labels; no suppression occurs without an overlay; out-of-core
memory and shard-resume tests pass; the declared fixture commands produce inspectable artifacts
whose redacted results are recorded in current-state documentation.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Implementation

`src/arxiv_int/pipeline/normalize/` derives NFC canonical, casefold, and search views with reversible
original-to-normalized offset maps and offline language profiles under
`src/arxiv_int/resources/language/profiles.json`. Extracted records are never rewritten.
`src/arxiv_int/pipeline/dedupe/` proposes exact, normalized, MinHash/lexical, and edition groups as
reversible overlays. Classic k-permutation MinHash (algorithm version 2) replaced a one-permutation
sketch that under-estimated near-duplicate and edition Jaccard. Members can be suppressed only when
an overlay names a representative. `src/arxiv_int/pipeline/chunk/` splits canonical text into
heading, table, and sentence blocks, repeats table headers in every row group, and skips suppressed
duplicates. Shared `src/arxiv_int/pipeline/lake/` publishes contract Parquet, sidecars, and
checksum manifests; streaming Polars primary-key uniqueness runs across `part-*.parquet` files
before seal. Interrupted publication aborts unpublished scratch.

ODCS contracts `normalized-documents` and `duplicate-groups` plus Alembic `0002` add
`corpus.normalized_documents` and `corpus.duplicate_groups`. Store head is `0002`. Generated Pandera
checks and owned-stage fingerprints bind reuse. The DAG registers `normalize` -> `dedupe` ->
`chunk`. A completed extract or normalize snapshot that published documents is `produced` even when
some inputs are quarantined, so later corpus stages can consume the snapshot. Incomplete scans
remain `partial` and still halt.

LangGraph and LangChain splitters were not added. They do not preserve original-to-normalized
character offsets required by the gates, and the chunkers here are deterministic
structure/table/sentence functions. CUDA is present on this host and is reserved for later
`embed`/`facts` lanes; these stages are CPU.

## Acceptance evidence

Evidence root: `$DATA_DIR/normalize/0062/`.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Prerequisites and selection | `make plan-status`; record 0061 | Pass; task selected with 64 open tasks |
| Golden offsets and table headers | `pytest tests/pipeline/chunk/test_chunkers.py tests/pipeline/chunk/test_stage.py -q` | Pass; markdown table headers repeat per row group and canonical offsets map back to source text |
| Stable ids on unchanged input | `test_unchanged_input_yields_stable_chunk_ids` | Pass; two independent fixture chains emit identical chunk ids |
| Dedupe precision on labels | `pytest tests/pipeline/dedupe/test_stage.py -q` | Pass; labeled prose/copy and long/near pairs are grouped; editions are grouped without suppression |
| No suppression without overlay | `test_no_suppression_occurs_without_an_overlay` | Pass; every suppressed member belongs to a group that still has a representative |
| Out-of-core memory and resume | `pytest tests/pipeline/normalize/test_resume.py -q` | Pass; sketch peak stays under 8 MiB across 24 vs 96 documents; KeyboardInterrupt leaves no sealed snapshot |
| Cross-partition identity | `SnapshotValidator.check_identities` before lake seal | Pass; duplicate primary keys across `part-*.parquet` refuse publication |
| Fixture Make commands | `make stage STAGE=normalize\|dedupe\|chunk RUN_ID=run-6372982831da4d1cb462e62b75650da8` | Pass; 14 normalized documents (1 empty-text quarantine), 4 duplicate groups / 9 memberships / 3 suppressed, 91 chunks (1 table, 90 text) over 10 representatives |
| Unchanged rerun | same stages after `make forecast FROM=preflight TO=chunk` | Pass; normalize, dedupe, and chunk reported `cache_hit=true` and invoked no heavy work |
| Source integrity | `$DATA_DIR/normalize/0062/source-before.json` vs `source-after.json` | Pass; 17 fixture SHA-256 values unchanged |
| Required repository gate | `make ci` | Pass; 1256 tests, 2 skipped; complexity, contracts, and spec-plan gates held |

## Audit handoff

Unresolved task-local audit notes: `none identified`.

Self-review repaired three producer defects before acceptance: MinHash one-permutation sketches
missed labeled near-duplicates and editions; lake publication lacked cross-partition identity
checks; and extract/normalize outcomes of `partial` for expected quarantines halted the DAG so
`chunk` could never run. The fixture Make run proves the repaired outcomes. Short extracted
snippets can still receive an `und` or compact-profile language code; that is a heuristic on
bounded samples, not a Russian-quality claim.

LangGraph was considered for chunking optimization and rejected because offset-preserving
structure/table/sentence chunkers are already deterministic and cheaper than a graph runtime.
This run is not a CUDA throughput or multi-terabyte quality claim. Live catalog comparison still
treats 0002 lake tables as additive overlays on the 0001 store snapshot; that remains with store
consumers.

The provided-archive corpus proof and `review-corpus-and-control-integrity` remain open. This
record does not start either.

## Close or resume

Accepted. The next consumer is the milestone review `review-corpus-and-control-integrity`;
`prove-corpus-foundation-on-provided-archive` remains blocked on that checkpoint.

Updated corpus current-state, pipeline/runtime/operator guidance and indexes, replaced downstream
raw task dependencies with this accepted record, and removed only
`implement-normalization-dedupe-and-chunking` from the forward plan. Counts moved from 64 to 63
tasks (54 to 53 agent; 10 human unchanged). The next eligible agent task is
`review-corpus-and-control-integrity`.

No human-review handoff applies. No service or model process was started. All task commands
exited; immutable product artifacts remain under the configured results root and tool evidence
under `$DATA_DIR/normalize/0062/`. No commit or push was made.
