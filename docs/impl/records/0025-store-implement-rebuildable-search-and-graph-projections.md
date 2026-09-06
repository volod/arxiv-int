# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-rebuildable-search-and-graph-projections` /
  `canonical-store` / `review-foundation-and-store-boundaries`
- State: accepted
- Source: [plan](../plan.md) (task removed after gates). Working tree also contains
  unrelated corpus, setup, and evolution-baseline files that this task did not absorb.
- Initial count: 78 tasks (68 agent, 10 human); next agent task
  `implement-rebuildable-search-and-graph-projections`.
- Accepted task:

```markdown
#### implement-rebuildable-search-and-graph-projections

Create projection lifecycle code for ParadeDB, pgvector candidates, and AGE without making any
projection canonical.

- Serves: `canonical-store` --
[Search and vector projections](../design/spec.md#search-and-vector-projections)
- Agent status: CLEAR
- Dependencies: [Canonical relational schema](records/0021-store-create-canonical-relational-schema.md);
[dbt transformation foundation](records/0024-store-implement-dbt-transformation-foundation.md).
- User-visible outcome: Search/vector/graph projections can be built, validated, version-switched,
and dropped without losing canonical rows.
- Scope boundary: Implement lifecycle and correctness checks on fixtures; relevance and scale
promotion belong to later capabilities.
- Data and artifact paths: `src/arxiv_int/stores/projections/`, Alembic revisions,
`transformations/models/projections/`,
`tests/integration/projections/`, and `$RUNS_DIR/<run-id>/manifests/`.
- Execution path: Add versioned projection metadata, staging builds, row/count/checksum
reconciliation, sampled SQL/Cypher parity, active-pointer switch, and cleanup planning; preserve
full evidence relationally. Prepare relational projection inputs in described dbt models with
source/ref and data tests; keep index DDL and AGE/Cypher in reviewed engine adapters. Use shared
quality results before activation and typed SQLAlchemy operations for pointer transactions.
- Acceptance gates: Rebuild from normalized/canonical fixtures yields identical logical ids; failed
builds never replace active projections; graph-disabled mode supports recursive SQL and open
exports.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Frozen Alembic revision `0003_projection_metadata.py` (revises `0002`, SHA-256
`f9158090d9ee4291e9bf659314d32ca2ad02a48444844aadb30cb4b5025f2488`) adds `ctl.projections`,
`ctl.projection_active`, `ctl.projection_evidence`, and `ctl.projection_cleanup`, plus pipeline
write grants and `GRANT USAGE, CREATE ON SCHEMA search`. Head is `0003`. Overlay adopt stamps
`0001`/`0002`/`0003` from partition and projection-table completeness.

dbt models `transformations/models/projections/` (`tag:projections`) build isolated
`derived.proj_*__g_<generation>` inputs with `source`/`ref` tests. Version tokens reuse
`sanitize_generation_id` so adapter lookups match dbt aliases.

`src/arxiv_int/stores/projections/` owns lifecycle, exclusive version locks, shared quality
publication, typed pointer transactions, cleanup planning, and engine adapters:

- ParadeDB BM25 covering index with Russian stemmer and keyword identifier tokenizer
- pgvector HNSW on selected embeddings (empty source allowed)
- AGE graph load on autocommit (create_graph cannot run in a metadata transaction), plus recursive
  SQL and GraphML/JSON-LD/Turtle when AGE is disabled

Activation writes `ctl.projection_active` only when all requested kinds are publishable. Failed
builds, missing derived inputs, and engine errors leave the pointer unchanged. Commands:
`arxiv-int store projections-build|status|cleanup` and matching Make targets (`APPLY=1` activates
or executes cleanup). Docs: [canonical-store.md](../current/canonical-store.md).

Limitations: fixture lifecycle only; no relevance, scale, or canonical-projection claim. Backup and
restore remain later work.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Rebuild identical logical ids | `ARXIV_INT_RUN_PROJECTIONS=1 pytest tests/integration/projections/test_live_projections.py` on image `arxiv-int/postgres:17-0.25.6-age1.7.0` | pass; `proj-a` and `proj-b` checksums match for lexical/vector/graph |
| Failed builds never replace active | same test: skip-dbt `proj-fail` after `proj-b` | pass; pointer stays `lexical:proj_b`; `corpus.documents` count remains 1 |
| Graph-disabled recursive SQL and open exports | same test: `proj-sql` with `age_enabled=False` | pass; engine `recursive-sql`; GraphML/JSON-LD/Turtle under `$DATA_DIR/projections/proj-sql/exports/` |
| Missing adapter/database | unit `not-run` without URL; live suite skips unless `ARXIV_INT_RUN_PROJECTIONS=1` | valid-negative |
| Offline units | `pytest tests/stores/projections` | pass |
| `make ci` | `make ci` | pass; 727 passed, 13 skipped |
| `make quality` | coverage, Markdown, build | pass; coverage 91.28% (floor 90); lint-md; wheel |
| Relevance / corpus-scale | out of scope | not claimed |

Live pytest used per-test `tmp_path` for `DATA_DIR`. Fixture evidence is not a real-archive run.

## Audit handoff

none identified. Reviewed disposable vs canonical ownership, dbt input isolation vs engine DDL,
pointer refusal on unpublished quality, AGE autocommit vs metadata transactions, version/generation
token alignment, and graph-disabled recursive SQL plus open exports. Checkpoint
`review-foundation-and-store-boundaries` remains the next agent task.

## Close or resume

Accepted after the declared disposable projection run on `arxiv-int/postgres:17-0.25.6-age1.7.0`,
documentation, `make ci` (727 passed, 13 skipped), and `make quality` (coverage 91.28%).
`make lint-doc-links` and `make lint-spec-plan` pass after plan removal. Plan counts: 78 tasks
before, 77 after (agent lane 68 to 67; human 10 unchanged). Next agent work:
`review-foundation-and-store-boundaries`. Capability `canonical-store` is not marked shipped
(backup/restore remain). No commit or push was made.
