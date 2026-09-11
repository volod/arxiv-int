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
chunk upserts. Loaded `chunk_id`s go into a transaction-scoped temp table; canonical rows whose ids
are absent from that set are deleted; commit then rebuilds the BM25 covering table. Unchanged ids
are kept by `ON CONFLICT`. An empty snapshot deletes all canonical chunks. Documents are not
deleted. `partial` checksum scope remains for a future declared delta; a complete snapshot that
still disagrees after retraction fails `full` reconcile.

Current state: [lexical retrieval](../current/lexical-retrieval.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Keep-set and SQL shape | `tests/pipeline/load_lexical/test_retract.py` | pass; duplicates collapsed, empty snapshot deletes all, matching store skips DELETE, documents untouched |
| Manifest retracted evidence | `tests/pipeline/load_lexical/test_reconcile.py`, `test_manifest.py` | pass; `retractedChunks` in JSON |
| Disposable ghost span | `tests/integration/lexical/test_live_lexical.py::test_live_lexical_retracts_superseded_chunk_ids` | declared heavy; `make ci` deselects it |
| Provided-archive leftovers | `tests/integration/lexical/test_archive_lexical.py` run `run-30d22e8991244b9ca002c640e12002c4` | pass in 24.46 s; retracted 48; live chunks 70550 one generation; 414 documents (37 unchunked duplicates); `checksumScope=full`; manifest `99a269665a860b8a52f0680f4461da018a23ad36ebf69f0af1a47641e01677a0` |
| Required CI | `make ci` | pass; 1332 passed, 56 deselected |

## Audit handoff

`none identified` after reviewing transaction visibility, empty-snapshot clearing, document
retention, and that facts/mentions FKs will refuse a retract if later stages already cite a
superseded `chunk_id`. A future delta loader must not use this store-wide absent-id delete.

## Close or resume

Required gates pass. Plan tasks unchanged at 58 (48 agent, 10 human). Capability `lexical-retrieval`
remains shipped. [0073](0073-lexical-prove-lexical-retrieval-on-provided-archive.md) audit note 1 is
resolved. Next eligible agent task remains `establish-versioned-udc-derived-scheme`. Updated
[lexical retrieval](../current/lexical-retrieval.md) and the record index. No human review handoff
applies. Next action: none for this task.
