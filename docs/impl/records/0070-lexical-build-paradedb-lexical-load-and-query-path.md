# ParadeDB Lexical Load and Query Path

## Task and scope

- Id / capability / checkpoint: `build-paradedb-lexical-load-and-query-path` / `lexical-retrieval` /
  `review-retrieval-and-classification-boundaries`
- State: accepted
- Source: `docs/impl/plan.md`, section
  "Lexical retrieval -- `lexical-retrieval`", at code revision `0fba636` with a clean worktree.
- Accepted task:

```markdown
#### build-paradedb-lexical-load-and-query-path

Bulk-load selected document/chunk projection rows and implement lexical search, filters, snippets,
facets, and identifier lookup.

- Serves: `lexical-retrieval` --
[Search and vector projections](../design/spec.md#search-and-vector-projections)
- Agent status: RUN NEEDED
- Dependencies: [0025](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md).
[Corpus and control integrity checkpoint](records/0063-corpus-review-corpus-and-control-integrity.md).
- User-visible outcome: The full normalized corpus or chosen partition is searchable with
evidence-bearing results and stable filter behavior.
- Scope boundary: Establish the lexical path and lifecycle; semantic fusion is separate.
- Data and artifact paths: `search.*` tables/indexes, `src/arxiv_int/retrieval/lexical.py`,
`$RUNS_DIR/<run-id>/search/`, and retrieval fixtures.
- Execution path: Binary-COPY staging rows; create one covering ParadeDB index per partition/table
design; index Russian text plus literal ids and required filter fields; expose typed query and
explain/diagnostic modes.
Reuse dbt-tested projection inputs and Pandera batch validation; use psycopg binary COPY and
bound SQLAlchemy queries. Keep ParadeDB index/search syntax in named engine assets and Alembic
operations, separate from business transformations.
- Acceptance gates: Load counts/checksums reconcile; result citations resolve to source spans;
concurrent index build/rebuild remains observable; query and index failures have actionable
diagnostics.
- Documentation target: `docs/impl/current/lexical-retrieval.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.
```

- Amendments: none.

## Implementation

Current state: [lexical retrieval](../current/lexical-retrieval.md).

New `arxiv_int.pipeline.load_lexical` package (`artifacts`, `source`, `loader`, `reconcile`,
`publish`, `stage`, `reuse`, `boundary`) registers the `load-lexical` runner after `chunk`. It
validates the chunk snapshot manifest the DAG passes as an upstream pointer, then follows that
manifest's checksum-bound pointers to the normalization and extraction snapshots, so no artifact is
read before it is rehashed. Widening the stage's DAG dependency beyond `chunk` was rejected in favour
of that existing manifest chain. Extraction rows carry `language: None`, so the load applies the
per-document language normalization detected rather than editing the accepted dbt model
`proj_lexical_rows.sql`; undetected documents stay null instead of being coerced to `und`.

Batches of 2000 rows are Pandera-validated through the shared `SnapshotValidator`, binary-COPYed into
`staging.*`, upserted into `corpus.documents`/`corpus.chunks` with a bound SQLAlchemy
`ON CONFLICT DO UPDATE`, and truncated between batches. Two defects in the shared loader were fixed:
`load_contract()` no longer truncates staging in a `finally` block, which previously masked the real
failure behind `InFailedSqlTransaction`; and `copy_binary()` now reads declared staging column type
OIDs and calls `Copy.set_types()`, because binary COPY applies no cast rule and previously failed with
`ProtocolViolation: insufficient data left in message`. A staging table missing a declared column is
now refused by name. `load_canonical_batch()` shares the fix.

The projection build reuses the accepted lifecycle (`build_projections`) for the lexical kind only, so
dbt builds `derived.proj_lexical_rows__g_<version>`, the versioned covering table and its single BM25
index are created, validated, and the active pointer switches under one publication lock below
`$RUNS_DIR/<run-id>/search/`.

`stores/projections/adapters/lexical.py` now declares the tokenizer profile as a hashed JSON asset:
Russian stemmer plus Russian stopwords for `body`/`title`, a whitespace tokenizer with lowercasing
disabled for `identifiers`, and fast keyword fields for `language`/`document_id`. A keyword tokenizer
on `identifiers` was tried first and broke literal lookup. `adapters/lexical_search.py` is the single
named engine asset holding every ParadeDB operator; user text, field names, filter values, limits and
snippet tags are bound parameters and only whitelisted identifiers are composed.
`retrieval/lexical.py` exposes the typed request, ranked search, literal lookup and explain;
`retrieval/projection.py` resolves the active target, index sizes and in-flight BM25 builds;
`retrieval/citations.py` resolves hits back to `corpus.chunks` spans. `retrieval/cli.py` plus
`retrieval/commands.py` add `arxiv-int search lexical` and `make search-lexical`, with exit 2 for no
active projection and exit 1 for refused fields, unparsable queries or driver errors.

`stores/postgres/selection.py` centralizes store-URL selection (explicit override, else the
configured service). Extending the same fallback to `store projections-build|status|cleanup` was
implemented and then reverted: their `not-run` without an explicit URL is an accepted boundary with
tests, so changing it needs the specification and plan first (AUD-build-paradedb-lexical-1).

Wiring: `dag/stages.py` declares the stage's contracts, validators, dependency packages and the
first-party modules it executes (store, dbt, runtime and projection adapters, required by
`test_stage_owns_every_first_party_module_it_executes`); `dag/execute.py` adds the
`lexical-projection` upstream pointer, passes `runs_dir`, and registers the reuse validator;
`dag/orchestrate.py` binds `LoadLexicalQuality`; `setup/requirements.py` marks the stage implemented;
`features/stages.py` gives it the `data-quality`/`lake`/`store`/`transform` groups.

Limitations: semantic and hybrid fusion, tokenizer calibration and the archive-wide relevance proof
remain separate plan tasks. `identifiers` currently carries the chunk id from the accepted dbt model,
so literal lookup resolves chunk and document ids, not yet extracted part numbers. No Alembic
revision was needed; the projection tables are created by the lifecycle, not by owned migrations.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Load counts and checksums reconcile | `$RUNS_DIR/run-lexical-live-0002/search/lexical.json` from corpus generation `run-77943af6b23e4fb995907fe4c7f072bc` | pass; 414 documents and 70550 chunks loaded, 70550 projection rows, 0 unindexed, `checksumScope=full` with `checksumMatch=true` |
| Result citations resolve to source spans | `make search-lexical QUERY="двигатель" LANGUAGE=rus CITATIONS=1 JSON=1` | pass; 98 matches, 10 hits, every citation resolved, `unresolved=[]` |
| Concurrent index build/rebuild observable | second load while polling `arxiv-int search lexical ... --explain` | pass; `index build pid=11115 state=active wait=IO:WalInitSync` reported while queries continued to serve the previous active version |
| Rebuild, switch and retire a version | `ctl.projection_active` and `ctl.projections` after the second load | pass; `lexical:run_lexical_live_0001` dropped, `lexical:run_lexical_live_0002` active |
| Query and index failures have actionable diagnostics | `arxiv-int search lexical x --field nosuch`; `--facet body`; `body:[[[`; identifier miss | pass; names allowed fields, unfacetable columns, the engine parse message, or exit 1 on unresolved identifier |
| Russian analysis, filters, snippets, facets | `make search-lexical QUERY="беспилотный летательный аппарат" FACET=language JSON=1` | pass; 608 matches, stemmed capitalized forms highlighted, facet `rus=601, eng=6, empty=1` |
| Deterministic unit tests | `make ci` | pass; 1290 passed, 52 deselected |
| Declared live integration test | `ARXIV_INT_RUN_LEXICAL=1 pytest tests/integration/lexical -m heavy` | pass; 1 passed on disposable `arxiv-int/postgres:17-0.25.6-age1.7.0` |
| Static gates | `make format`, `make lint`, `make typecheck`, `make lint-md`, `make lint-doc-links`, `make lint-spec-plan` | pass; 481 source files typechecked, 0 findings |
| Full-archive relevance quality | not attempted | not-run; structural provided-archive load/query is [0073](0073-lexical-prove-lexical-retrieval-on-provided-archive.md); judged archive-wide gold remains a production promotion gate |

The operator store was empty of project data, so the stale pre-0065 Alembic stamp was repaired with
the user's authorization by dropping the eight owned schemas plus `public.alembic_version` and
re-applying `upgrade head`; `make setup-schema` then reported `setup: ready` at revision `0001`.
Artifacts stay under configured roots: `$RUNS_DIR/<run-id>/search/lexical.json` and the projection
result under `$DATA_DIR/projections/<run-id>/`. Nothing source-derived was committed.

## Audit handoff

| Note | Observation |
| --- | --- |
| `AUD-build-paradedb-lexical-1` | Nonblocking. `arxiv-int store projections-build`, `projections-status` and `projections-cleanup` refuse with `not-run` unless `ARXIV_INT_MIGRATION_DATABASE_URL` is set, so the documented Make targets cannot inspect or clean the configured service that the pipeline itself loads. Evidence: `stores/projections/commands.py` uses `resolve_database_url()` while `stores/postgres/selection.py` resolves the service fallback; the fallback was implemented, broke `tests/stores/projections/test_projection_units.py::test_cli_projection_status_not_run` and two sibling tests, and was reverted. Impact: operators must export a URL for lifecycle commands. Next check: decide whether the selection fallback is specified behavior for those commands. Owner: [review-retrieval-and-classification-boundaries](../plan.md#review-retrieval-and-classification-boundaries). Disposition: open. |
| `AUD-build-paradedb-lexical-2` | Nonblocking. Editing any module in `_SHARED_CODE` (for example `pipeline/dag/execute.py`) changes every stage's `code_fingerprint`, so implementing one late stage invalidated the whole cached corpus chain and forced a 46-minute re-extraction on an unchanged archive. Evidence: `pipeline/control/owned.py` `_SHARED_CODE` includes `pipeline/dag` with only `stages.py` exempt; the first `make pipeline TO=load-lexical` recomputed `extract`. Impact: cost, not correctness. Next check: whether the executor seam can be narrowed the way `stages.py` already is. Owner: [review-retrieval-and-classification-boundaries](../plan.md#review-retrieval-and-classification-boundaries). Disposition: open. |

## Close or resume

All required gates passed; relevance quality remains explicitly not-run and owned by later tasks.
Plan tasks: 61 before, 60 after; agent tasks awaiting a run drop from 33 to 32. The `lexical-retrieval`
capability gains a load and query path; `calibrate-russian-tokenization-and-bm25` becomes the next
task whose prerequisites resolve. Updated `docs/impl/current.md`,
[lexical retrieval](../current/lexical-retrieval.md), `docs/impl/current/pipeline-control.md`,
`docs/guide/commands.md`, `docs/guide/operator-workflow.md` and the record index; the two plan
dependencies that named this task id now link this record. No human review handoff applies.
Next action: none for this task; the two audit notes are routed to the retrieval checkpoint.
