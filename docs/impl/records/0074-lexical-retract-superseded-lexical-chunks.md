# Lexical Load Snapshot Retraction

## Task and scope

- Id / capability / checkpoint: `retract-superseded-lexical-chunks` / `lexical-retrieval` /
  `review-investigation-and-report-integrity`
- State: accepted; required gates pass.
- Source: user-directed repair of
  [AUD-prove-lexical-retrieval-on-provided-archive-1](0073-lexical-prove-lexical-retrieval-on-provided-archive.md#audit-handoff).
  `lexical-retrieval` is shipped. `make plan-status` reported 58 tasks (48 agent, 10 human); this
  repair was not the next eligible agent task.
- Accepted task:

```markdown
#### retract-superseded-lexical-chunks

Retract canonical chunks that a complete `load-lexical` snapshot no longer contains, in the same
transaction as the upsert, so a re-chunked document cannot leave searchable ghost spans.

- Serves: `lexical-retrieval` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: [Lexical retrieval provided-archive integration](0073-lexical-prove-lexical-retrieval-on-provided-archive.md).
- User-visible outcome: A full lexical load leaves `corpus.chunks` equal to the snapshot it loaded;
search and citations no longer mix superseded spans from an earlier generation of the same document.
- Scope boundary: Retract only `corpus.chunks` for the complete snapshot `load-lexical` already
reads. Do not delete documents, archive files, or projection history. Do not add a leftover-count
heuristic or a delta loader.
- Data and artifact paths: canonical `corpus.chunks`, `$RUNS_DIR/<run-id>/search/lexical.json`
reconciliation evidence.
- Execution path: After upserting the snapshot in one transaction, delete canonical rows whose
`chunk_id` is absent from that snapshot; commit; then build and activate the covering index from the
retracted store. Unchanged ids stay via upsert. An empty snapshot clears the table.
- Acceptance gates: A document with old and new chunk ids keeps only the loaded ids; documents
without chunks stay; reconcile is `full` when counts match; a failure before commit leaves the
previous generation visible. Deterministic tests and `make ci` pass.
- Documentation target: `docs/impl/current/lexical-retrieval.md`
- Review checkpoint: `review-investigation-and-report-integrity`.
```

- Amendments: none.

## Implementation

`arxiv_int.pipeline.load_lexical.retract` runs in the same `engine.begin()` as the document and
chunk upserts. Loaded `chunk_id`s go into a transaction-scoped temp table; one `DELETE` removes
canonical rows whose ids are absent from that set and reports its row count; commit then rebuilds
the BM25 covering table. Unchanged ids are kept by `ON CONFLICT`. An empty snapshot deletes all
canonical chunks. Documents are not deleted. Every load is complete, so reconciliation requires
`full` scope and checksum equality: a canonical chunk count that differs from the loaded count
reports `partial` and is refused.

Audit repair (2026-09-11): the first implementation left `Reconciliation.ok` accepting `partial`
scope without a checksum check, so a store still wider than the snapshot (duplicate ids or a
concurrent writer) would publish, and this record's claim that such a store fails `full` reconcile
was false. `ok` now requires `full` scope. The retract dropped its separate `count(*)` pass for the
`DELETE` row count, SQL-shape unit tests were replaced by keep-set and insert-batching checks, and
the live test now covers failure before commit, a document left without chunks, and `full`
reconcile of the rebuilt projection. The first record listed that live test but did not run it.

Current state: [lexical retrieval](../current/lexical-retrieval.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Keep set | `tests/pipeline/load_lexical/test_retract.py` | pass; blanks and duplicates collapsed, keep set spans every insert batch, empty snapshot deletes all, documents untouched |
| Reconcile scope | `tests/pipeline/load_lexical/test_reconcile.py` | pass; `full` when the store equals the snapshot; a wider store reports `partial` and is refused (regression for the audit repair) |
| Manifest retracted evidence | `tests/pipeline/load_lexical/test_reconcile.py`, `test_manifest.py` | pass; `retractedChunks` in JSON |
| Ghost span, rollback, chunkless document | `ARXIV_INT_RUN_LEXICAL=1 pytest -m heavy tests/integration/lexical/test_live_lexical.py` | pass, 2 tests, after the audit repair; a failure before commit keeps `chunk-old`; the retract keeps only `chunk-1` and both documents; the rebuilt projection reconciles at `full`. Declared heavy; `make ci` deselects it |
| Provided-archive leftovers | `tests/integration/lexical/test_archive_lexical.py` run `run-30d22e8991244b9ca002c640e12002c4` | pass before the audit repair, in 24.46 s; retracted 48; live chunks 70550 one generation; 414 documents (37 unchunked duplicates); `checksumScope=full` with checksum match, so it also meets the stricter rule; not rerun after the repair; manifest `99a269665a860b8a52f0680f4461da018a23ad36ebf69f0af1a47641e01677a0` |
| Required CI | `make ci` | pass after the audit repair; 1333 passed, 56 deselected |

## Audit handoff

| Note | Observation |
| --- | --- |
| `AUD-retract-superseded-lexical-chunks-1` | Resolved in this record. `Reconciliation.ok` passed `partial` scope without a checksum, which let a store wider than the snapshot publish. `ok` now requires `full` scope. `load-lexical` code paths feed its reuse key, so attempts published before the repair are not reused. Owner: [review-investigation-and-report-integrity](../plan.md#review-investigation-and-report-integrity). Disposition: resolved; evidence in [acceptance evidence](#acceptance-evidence). |
| `AUD-retract-superseded-lexical-chunks-2` | Nonblocking observation. The publication lock is per run (`$RUNS_DIR/<run-id>/search/`), so two concurrent `load-lexical` runs with different snapshots are not serialized across load, build and verify, and the later retract removes the earlier run's rows. With `full` scope required, the run whose store no longer equals its snapshot fails reconciliation instead of publishing. This is reasoned from the transaction order, not exercised. Owner: [review-investigation-and-report-integrity](../plan.md#review-investigation-and-report-integrity). Disposition: resolved by [0075](0075-lexical-serialize-concurrent-lexical-loads.md), which holds a store-wide advisory lock across load, build and verify. |

Also reviewed: transaction visibility, empty-snapshot clearing and document retention. `kg.facts` and
`kg.mentions` reference `corpus.chunks` without cascade, so they refuse a retract once they cite a
superseded `chunk_id`; the load then rolls back. A future delta loader must not use this store-wide
absent-id delete.

## Close or resume

Required gates pass after the audit repair. Plan tasks unchanged at 58 (48 agent, 10 human);
`AUD-retract-superseded-lexical-chunks-2` is resolved by
[0075](0075-lexical-serialize-concurrent-lexical-loads.md). Capability `lexical-retrieval`
remains shipped. [0073](0073-lexical-prove-lexical-retrieval-on-provided-archive.md) audit note 1 is
resolved. Next eligible agent task remains `establish-versioned-udc-derived-scheme`. Updated
[lexical retrieval](../current/lexical-retrieval.md) and the record index. No human review handoff
applies. Next action: none for this task.
