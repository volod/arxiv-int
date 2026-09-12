# Corpus and Control Integrity Review

## Task and scope

- Id: `review-corpus-and-control-integrity`; capability: `corpus-foundation`; checkpoint: this task.
- State: accepted; repair
  [0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md), the traced invariants and
  required CI pass.
- Source: `docs/impl/plan.md`, `corpus-foundation`; selected by `make plan-status` as the next agent
  task at 63 open tasks. Code revision `d413383`; working tree clean at task start.
- Accepted task: the full block as it stood in the plan.

```markdown
#### review-corpus-and-control-integrity

Review the integrated milestone before lexical loading, classification and NLP consumers.

- Serves: `corpus-foundation` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: [Normalization, dedupe and chunking](records/0062-corpus-implement-normalization-dedupe-and-chunking.md);
[Owned stage fingerprints](records/0058-pipeline-bind-real-owned-stage-fingerprints.md);
[Bounded archive snapshots](records/0059-pipeline-bound-archive-snapshot-hashing.md);
[Control integration checkpoint](records/0054-pipeline-review-control-integration-boundaries.md);
[Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md);
[Investigation profile and output manifest](records/0045-pipeline-implement-investigation-profile-and-output-manifest.md);
[Progress logging and resource telemetry](records/0043-pipeline-add-progress-logging-and-resource-telemetry.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
[Publication/reuse checkpoint](records/0046-pipeline-review-pipeline-publication-and-reuse-boundaries.md);
[Incremental reconciliation and stale pruning](records/0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md).
- Audit inputs: [AUD-review-pipeline-publication-and-reuse-boundaries-2](records/0046-pipeline-review-pipeline-publication-and-reuse-boundaries.md#audit-handoff);
[AUD-retire-committed-proof-export-1](records/0057-eval-found-retire-committed-proof-export.md#audit-handoff).
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
Use deterministic integration evidence and inspect provided-archive proofs when available;
this verdict permits fixture implementation, not real-data or CUDA promotion.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/proof artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace source immutability,
complete-scan semantics, cell/member coordinates, shard/generation
identity, cache invalidation, atomic publication, forecast/reserve refusal and bounded queues;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.
```

- Amendments: none.

## Implementation

This round is a review. It changed no stage behavior itself. Three blocking findings were routed to
one focused prerequisite repair,
[0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md), which was created,
implemented and accepted before this checkpoint closed. This round contributed the two routed-note
repairs below, four regressions at now-stable seams, and the evidence in the next section.

Routed-note repairs owned by this checkpoint:

- `AUD-retire-committed-proof-export-1`: `tests/inspect/test_summarize.py` and
  `tests/observability/logging/test_redact.py` embedded the operator's own home path as the literal
  the redactor must remove. Both now use a generic `/home/operator/...` literal. The redaction rule
  under test is the generic `/home|Users|var|opt|tmp|mnt|data` path pattern, so the assertions prove
  exactly what they proved before.
- `AUD-review-pipeline-publication-and-reuse-boundaries-2`, diagnostic Markdown debt: the repository
  scan reported 24 `MD013` line-length findings across the specification, six current-state pages,
  the plan and two records. All are now wrapped; the two inside preserved `Accepted task` fenced
  blocks were only re-wrapped, with the whitespace-normalized text asserted identical before writing,
  so no recorded task text changed. `make lint-md` now reports zero findings and no rule was
  weakened.

Tests added at stabilized seams (all reproduced the defect they cover on the pre-repair tree):

- `tests/pipeline/dag/test_stage_declarations.py` computes the transitive first-party import closure
  of each production stage runner and asserts every executed module is an owned asset of that stage,
  plus that the reviewed language profiles are owned by `normalize` alone.
- `tests/pipeline/chunk/test_stage.py::test_source_offsets_address_carriage_returns_in_the_extracted_artifact`
  asserts a document containing carriage returns yields a shifted offset map and that published
  `start_char`/`end_char` select the same text in the extracted artifact.
- `tests/inspect/test_summarize.py::test_superseded_attempt_never_borrows_the_accepted_attempt_identity`
  asserts a retried stage reports each attempt directory with its own attempt number and status.

Current-state page: [corpus foundation](../current/corpus-foundation.md).

## Acceptance evidence

Evidence root: `$DATA_DIR/architecture-review/0063/`. Fixture silo:
`$DATA_DIR/normalize/0062/archive` (17 files). The pre-repair diagnosis run is
`run-9e4fddc56bc548cd9e735c90d2aeca7d`; the post-repair replay is
`run-4d031f305616407fa296ec587a44cc7e`.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Prerequisites and selection | `make plan-status` | Pass; `review-corpus-and-control-integrity` selected at 63 open tasks (53 agent, 10 human) |
| Baseline before any edit | `make ci` | Pass; 1258 tests, 50 deselected |
| Source immutability | `sha256sum` over the fixture silo versus `.data/normalize/0062/source-after.json` | Pass; all 17 files byte-identical after a full `preflight..chunk` run, two reruns and a forced recompute |
| Complete-scan semantics | `pipeline/inventory/reconcile.py` traced against `reconcile/diff.py` and `_active_view`; `pytest tests/pipeline/reconcile -q` | Pass; an unobservable silo withholds removals and tombstones, and rows whose supporting silos were not fully rescanned are retained |
| Cell/member coordinates | `pipeline/inventory/archives.py` `_member` and `extraction` span sidecars; published chunk metadata | Pass; member addresses carry the header ordinal and JSON-quoted name, and span sidecars retain page/sheet/row/column/cell anchors |
| Shard/generation identity | `reconcile/scan.py` `source_shard_ids`; `inventory/stage.py` roots | Pass; production runs bind one `default` shard and one `scan_id=<generation>` root, and reuse keys carry the shard id |
| Cache invalidation | `make forecast`; `make stage` for `inventory..chunk`, unchanged and after a reviewed language-profile edit | Blocking defect found and repaired by [0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md); after the repair the unchanged rerun is a full cache hit and a profile edit recomputes `normalize`, `dedupe`, `chunk` only |
| Atomic publication | `pipeline/inventory/publish.py`, `lake/artifacts.py` `validate_snapshot_manifest`; `make inspect` | Pass; partitions and manifests land through temporary-then-replace with `fsync`, the checksum index seals last, and every referenced artifact is rehashed before reuse |
| Forecast and reserve refusal | `make forecast RUN_ID=...`; `forecast/recheck.py`; the retained `0056-host` control proof gates | Pass; devices report `peak + reserve`, the stage boundary refuses below reserve, and a stale cache plan refuses the stage |
| Bounded queues | `observability/logging/__init__.py`; `pytest tests/observability -q` | Pass; enqueue never blocks, drops are counted, and the stop sentinel cannot hang shutdown |
| Chunk source offsets on published artifacts | scripted check over `run-4d031f305616407fa296ec587a44cc7e`: 91 chunks read byte-exact against the extracted text | Pass; 14 documents, 91 chunks, unique chunk ids, zero out-of-bounds offsets, and 91 of 91 source-offset-faithful chunks, including one chunk whose canonical and original offsets genuinely differ. The one chunk that is not a verbatim slice is the table chunk whose repeated header is recorded in `repeated_prefix_chars` |
| Retained provided-archive control proof | `$RESULTS_DIR/proofs/pipeline-control/0056-host/gates.json` | Pass; all 14 gates `pass`, including `archive_unmodified`, `space_refusal`, `code_invalidation` and `noop_zero_workers`. Control-plane evidence only; no corpus proof exists yet |
| Operator workflow after the repair | `make run-create`; `make forecast`; `make stage STAGE=preflight..chunk`; `make inspect` on `run-4d031f305616407fa296ec587a44cc7e` | Pass; every stage `succeeded`/`produced` with a valid tree and no schema drift; `preflight` and `inventory` reused the earlier run because the repair did not touch their declared assets, and `extract` onward recomputed, which is the repaired closure |
| Unchanged rerun after the repair | `make forecast` then the same stages | Pass; `inventory`, `extract`, `normalize`, `dedupe` and `chunk` all `cache_hit=true` |
| Markdown diagnostic debt | `make lint-md` | Pass; 0 findings, down from 24 |
| Documentation gates | `make lint-doc-links`; `make lint-spec-plan` | Pass; 0 broken links, 0 spec-plan findings |
| Required repository gate | `make ci` | Pass; 1268 tests, 50 deselected; format, lint, mypy, complexity, shell, doc-link, spec-plan, contract, evolution, migration, ontology, schema and evaluation-fixture gates all held |

Fixture and control-plane evidence only. Nothing here establishes provided-archive corpus quality,
extraction accuracy, CUDA throughput or multi-terabyte behaviour; those remain with
[the corpus proof](0068-corpus-prove-corpus-foundation-on-provided-archive.md).

## Audit handoff

Coverage: the ten producer records named as dependencies, their modules under
`src/arxiv_int/pipeline/{inventory,normalize,dedupe,chunk,reconcile,prune,forecast,control,dag,run}/`,
`src/arxiv_int/extraction/`, `src/arxiv_int/inspect/` and `src/arxiv_int/observability/logging/`, the
two routed notes, and the retained `0056-host` control proof. Coverage limit: the round traced the
executed first-party closure of each stage runner statically; a module reached only through a runtime
string import would not appear in it. The Postgres control and reconciliation backends were read but
not exercised, because no corpus stage activates a database.

Incoming notes and their dispositions:

| Source round | Note and disposition |
| --- | --- |
| Publication and reuse round, placeholder owned fingerprints | `AUD-review-pipeline-publication-and-reuse-boundaries-2`. Resolved. The concrete producers do supply real contract, validator, tool and dependency identities, but their code and data declarations were incomplete; note 1 below reproduces it and [0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md) repairs it. |
| Publication and reuse round, coarse local lock | `AUD-review-pipeline-publication-and-reuse-boundaries-2`. Reconciled and carried forward as note 5 below. |
| Publication and reuse round, diagnostic Markdown debt | `AUD-review-pipeline-publication-and-reuse-boundaries-2`. Resolved; `make lint-md` reports zero findings. |
| Retired proof export, hardcoded operator path in two tests | `AUD-retire-committed-proof-export-1`. Resolved; both literals are generic and both assertions still fail when path redaction is removed. |
| [0059](0059-pipeline-bound-archive-snapshot-hashing.md) metadata-guard filesystem/race limits | Reconciled and carried forward as note 6 below. |
| [0060](0060-corpus-implement-streaming-inventory.md) materialized reconciliation interface | Reconciled and carried forward as note 4 below. |
| [0060](0060-corpus-implement-streaming-inventory.md) database activation requirements | Reconciled and carried forward as note 7 below. |

Blocking findings, all repaired by
[0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md):

| Finding | Evidence, invariant and consumers |
| --- | --- |
| `AUD-review-corpus-and-control-integrity-1` | Blocking, resolved. Every production stage's owned assets omitted first-party code it executes, so an edit to an executed module left the reuse key unchanged and the next run reused stale artifacts. Sharpest case: editing the reviewed `resources/language/profiles.json` left `owned_fingerprints("normalize")` byte-identical while `normalizer_id` changed, so a cached normalized snapshot kept the previous language labels with no signal. Invariant: a changed executed asset must invalidate its owning shard and consumer closure. Consumers: `prove-corpus-foundation-on-provided-archive`, lexical loading, classification and Russian NLP. Repaired and regressed by [0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md). |
| `AUD-review-corpus-and-control-integrity-2` | Blocking, resolved. `NormalizeStage._read` applied universal newlines to the extracted text, so a document containing `\r\n` was normalized from a shorter view than the published artifact, `canonical_view` recorded an identity offset map instead of its `\r\n` runs, and `chunk` published `start_char`/`end_char` shifted by the count of preceding carriage returns. Measured on the fixture chain: offsets `12-81` and `48-105` selected text two characters early. Invariant: published source offsets address the extracted artifact a consumer reads. Consumers: evidence and source-location lookup, lexical snippets, classification, Russian NLP, and the corpus proof's span checks. Repaired and regressed by [0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md). |
| `AUD-review-corpus-and-control-integrity-3` | Blocking, resolved. `inspect` keyed ledger rows by stage name and applied the accepted row to every attempt directory the manifests walk returned, so after a retry a superseded `attempt-1` directory was reported with the accepted attempt's number, status and cache decision. Invariant: an inspection field describes the artifact it names. Consumers: `prove-corpus-foundation-on-provided-archive`, whose accounting gate reads `make inspect`, and every operator inspecting a retried run. Repaired and regressed by [0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md). |

Nonblocking notes, one owner each:

| Note | Finding, next check and owner |
| --- | --- |
| `AUD-review-corpus-and-control-integrity-4` | `reconcile/commands.py` `prepare_update` still calls `scan_silos`, which re-walks and re-hashes every silo and holds one `SourceOccurrence` per file in memory, duplicating the inventory stage's bounded streaming work. `Orchestrator` already restricts the same call to the fixture profile, but `make update` does not. No correctness defect: the delta must precede the DAG walk, so a fresh scan is required there. Next check: measure `make update` peak memory and wall time against a silo of realistic file count and decide whether the delta must stream to disk. Owner: [test-failure-and-capacity-boundaries](../plan.md#test-failure-and-capacity-boundaries). Disposition: open, nonblocking. |
| `AUD-review-corpus-and-control-integrity-5` | `run/locking.py` holds one process-wide `RLock` across the whole guarded body, so two threads publishing to different roots in one process would serialize completely. No correctness defect today: the pipeline contains no threading or multiprocessing, and cross-process exclusion is a real `flock` per root. Next check: before any concurrent worker or distributed control ledger, narrow the thread lock to the `_HELD` bookkeeping. Owner: [test-failure-and-capacity-boundaries](../plan.md#test-failure-and-capacity-boundaries). Disposition: open, nonblocking. |
| `AUD-review-corpus-and-control-integrity-6` | The inventory metadata guard brackets each read with device, inode, mode, size, mtime and ctime checks and re-verifies the pathname through a second descriptor, and the source-set snapshot is compared before and after the scan. A change that is created and reverted entirely between two observations remains undetectable, as [0059](0059-pipeline-bound-archive-snapshot-hashing.md) documented. Next check: confirm the provided-archive proof runs against a quiescent, read-only archive and records that condition. Owner: [prove-corpus-foundation-on-provided-archive](0068-corpus-prove-corpus-foundation-on-provided-archive.md). Disposition: resolved by record 0068; source hashes and metadata matched, with the transient-change limit retained. |
| `AUD-review-corpus-and-control-integrity-7` | Corpus stages publish to the lake only; no corpus stage activates a database, and `reconcile/postgres.py` plus the Postgres control ledger were read but not exercised in this round. Next check: trace corpus artifact identities into the canonical store and its activation gate when the first store consumer loads them. Owner: [checkpoint 0080](0080-archive-cls-review-retrieval-and-classification-boundaries.md). Disposition: resolved by checkpoint 0080; the corpus chain reaches the store as checksum-validated manifest pointers plus per-row generation, chunker and contract identities, and activation is gated on build quality, the active pointer and, after repair 0081, the engine profile that built it. |
| `AUD-review-corpus-and-control-integrity-8` | `dedupe/group.py` assembles duplicate groups by union-find over lexical edges, so similarity is transitive without a component-size bound. At the `0.90` threshold this needs many hops to chain unrelated documents, and the overlay stays reversible and deletes nothing, but each chained component suppresses all but one member from chunking. Next check: measure duplicate component sizes and the suppressed-member share on the provided archive, and decide whether a component bound or verification pass is required. Owner: [prove-corpus-foundation-on-provided-archive](0068-corpus-prove-corpus-foundation-on-provided-archive.md). Disposition: resolved by record 0068; component sizes and suppression share measured, with no bound change justified. |
| `AUD-review-corpus-and-control-integrity-9` | `extract` fingerprints Docling by its CLI version string, not by the layout and table model assets prefetched under `$MODEL_CACHE_DIR/docling/`; `spec.models` is empty for the stage. A model refresh under an unchanged version would not invalidate extraction. Next check: on the provided-archive run, record the Docling asset digests alongside the tool versions and decide whether they belong in `model_fingerprint`. Owner: [prove-corpus-foundation-on-provided-archive](0068-corpus-prove-corpus-foundation-on-provided-archive.md). Disposition: resolved by record 0068; actual model content now binds extraction reuse and is regressed. |

Refactor verdict: refactor needed, bounded to the owned-asset declarations, the
document-text IO seams and the inspection attempt binding, and implemented by accepted repair
[0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md). No broader rewrite, model
promotion, contract change or dependency change is warranted; inventory walking and hashing, archive
member policy, extraction routing, normalization text rules, grouping, chunking, forecasting,
publication atomicity and bounded logging need no change.

Checkpoint verdict: **proceed-with-nonblocking-notes** for lexical loading, classification, Russian
NLP and the provided-archive corpus proof, now that repair 0064 has passed.

## Close or resume

All acceptance gates pass; no gate remains unrun. Next action: none for this checkpoint. The next
eligible agent task is
[prove-corpus-foundation-on-provided-archive](0068-corpus-prove-corpus-foundation-on-provided-archive.md)
(`RUN NEEDED`), which this verdict releases.

Updates: [corpus foundation](../current/corpus-foundation.md) and
[pipeline control](../current/pipeline-control.md) record the completed declarations, the byte-exact
document-text seams and the honest attempt reporting; the [record index](README.md) lists 0063 and
0064; `docs/impl/plan.md` no longer carries this checkpoint, and every task that named
`review-corpus-and-control-integrity` now links this record.

Plan counts: 63 tasks before (53 agent, 10 human; `CLEAR=19`, `HUMAN-GATED=10`, `RUN NEEDED=34`);
62 after (52 agent, 10 human). Capability change: none added. The corpus stages' existing reuse,
source-offset and inspection promises now hold, and the milestone is released to its named consumers.
