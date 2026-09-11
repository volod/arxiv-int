# Lexical Retrieval Provided-Archive Integration

## Task and scope

- Id / capability / checkpoint: `prove-lexical-retrieval-on-provided-archive` /
  `lexical-retrieval` / `review-investigation-and-report-integrity`
- State: accepted; current proof verification and all required gates pass.
- Source: `docs/impl/plan.md`, section "Lexical retrieval -- `lexical-retrieval`".
  `make plan-status` reported 59 tasks (49 agent, 10 human) and
  `establish-versioned-udc-derived-scheme` as the next eligible agent task because this
  proof listed the still-open checkpoint `review-retrieval-and-classification-boundaries`
  after its accepted record prerequisites. The user directed this task. Record
  prerequisites [0072](0072-lexical-review-and-deepen-russian-lexical-calibration.md) and
  [0053](0053-pipeline-prove-pipeline-control-on-provided-archive.md) are accepted. The
  checkpoint remains the later retrieval/classification review; it is not a missing
  lexical implementation input.
- Accepted task:

```markdown
#### prove-lexical-retrieval-on-provided-archive

Build and query the lexical projection for the supplied archive through an explicit integration test.

- Serves: `lexical-retrieval` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: [Russian lexical calibration second opinion](records/0072-lexical-review-and-deepen-russian-lexical-calibration.md);
[Pipeline-control provided-archive proof](records/0053-pipeline-prove-pipeline-control-on-provided-archive.md).
`review-retrieval-and-classification-boundaries`.
- User-visible outcome: Supplied documents are searchable through the selected Russian lexical
profile, with filters, snippets, identifiers, and citations that resolve to source evidence.
- Scope boundary: Prove lexical load/query behavior and declared evaluation queries; do not claim
semantic retrieval or full-archive relevance from this test archive.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, lexical tables/indexes, and
`$RUNS_DIR/<run-id>/search/`, plus test logs below `$DATA_DIR/integration/lexical-retrieval/`.
- Execution path: Forecast; load/build the selected lexical projection; reconcile counts/checksums;
run archive-appropriate smoke and held-out queries; validate citations and limits; rerun unchanged
and record load/index cache decisions.
- Acceptance gates: Projection and source counts reconcile; required queries return valid evidence
under declared metrics; index/query manifests validate; unchanged rerun does not rebuild or reload
unchanged partitions; failures or missing citations keep the task open.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/lexical-retrieval.md`
- Review checkpoint: `review-investigation-and-report-integrity`.
```

- Amendments: none.

## Implementation

Extra cross-checks live under `tests/integration/lexical/` only. Ordinary artifacts stay under
`$RUNS_DIR/<run-id>/search/` and the canonical store. Tool logs stay under
`$DATA_DIR/integration/lexical-retrieval/`. The test forecasts, walks the ordinary DAG to
`load-lexical`, reconciles the active covering table, runs declared query kinds against live
sampled chunks (no committed gold file), then replays the same plan and requires cache hits with
no worker invocations.

`require_ident` previously allowed 48-character tokens. dbt generation tables are
`<model>__g_<32-char-version>`; a uuid-style `run-<hex>` produces a 53-character
`proj_lexical_rows__g_run_...` name that PostgreSQL accepts (NAMEDATALEN 63) but the guard
rejected after a successful dbt build. The first provided-archive walk halted with
`unsafe identifier` and no covering table. The bound now matches PostgreSQL's 63-character
unquoted identifier limit. Pytest assertions no longer dump `RunContext` on a halted DAG.

`make test-archive` now runs `-m archive` (corpus and lexical) instead of a hardcoded corpus
module path.

Current state: [lexical retrieval](../current/lexical-retrieval.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Task selection | `make plan-status` | 59 tasks (49 agent, 10 human); user-directed; record prerequisites accepted |
| CUDA host | `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader` | NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84; unused on the passing run (extract cache-hit; BM25 is CPU/database) |
| Forecast | `$RUNS_DIR/run-b432670ba9974eac974e0ed36312ebb4/forecast/decision.json` | pass; decision `degraded` not `blocked`; load-lexical had no measured amplification; a rotational scratch/database device widened the time range |
| Ordinary DAG through `load-lexical` | `tests/integration/lexical/test_archive_lexical.py` first pass | pass in 28.63 s; corpus stages cache-hit; load-lexical `cacheHit=false`, `workerInvoked=true` |
| Projection and source counts | `$RUNS_DIR/<run-id>/search/lexical.json` and live `reconcile()` | pass; this load 414 documents / 70550 chunks; live store 414 / 70598; projection 70598; unindexed 0; `checksumScope=partial` |
| Index/query manifest | same `lexical.json` SHA-256 `65d6108a99a85a0f0fd0105bcf6b75846abb7c5d2888a9712e7c9a038c98a445` | pass; activated `unicode-russian-v1` / `russian-guarded-v2`; tokenizer `3b277b2329ad0f884d7af43261e195bc8577f8790b40792aaa3b0ac0b62ed47e`; query policy `8c020cf3dbced44695043d12a8d00678807d663f6c44df2ef6545d2525ed41cc`; index 28,729,344 bytes; table 69,148,672 bytes |
| Declared queries and citations | `$DATA_DIR/integration/lexical-retrieval/run-b432670ba9974eac974e0ed36312ebb4.json` | pass; eight known-item cases, recall@10 1.0, span intact 1.0, MRR 0.9375, identifier exactness 1.0, p95 24.785 ms, unresolved citations 0; kinds known-item, identifier, document-filter, language-facet, limit, offset, explain, missing-identifier |
| Unchanged replay | same pytest; orchestrator `execute_plan` | pass; every stage `cache_hit` and `not worker_invoked` |
| Identifier regression | `tests/stores/projections/test_projection_units.py::test_uuid_run_derived_tables_fit_postgres_idents` | pass |
| Helper unit tests | `tests/retrieval/test_archive_lexical_checks.py` | pass |
| Required CI | `make ci` | pass; 1327 passed, 55 deselected |
| Source-derived commit | `git status` | nothing source-derived staged; integration log stays under `$DATA_DIR` |

The first halted walk was `run-e5aa89928f1a4641afff2c82f0b8e097` (extract rebuilt, then load-lexical
failed on the identifier bound). The accepted run reused that corpus chain. Nothing source-derived
was committed.

## Audit handoff

| Note | Observation |
| --- | --- |
| `AUD-prove-lexical-retrieval-on-provided-archive-1` | Nonblocking, resolved. `load-lexical` upserted by `chunk_id` and never retracted superseded ids. Live store mixed 70,550 current chunks with 48 earlier spans from one re-chunked document (138 overlapping intervals). Repair: [0074](0074-lexical-retract-superseded-lexical-chunks.md) deletes canonical chunk ids absent from the complete snapshot in the same upsert transaction. Owner: [review-investigation-and-report-integrity](../plan.md#review-investigation-and-report-integrity). Disposition: resolved by record 0074. |

## Close or resume

Required implementation and provided-archive gates pass; judged archive-wide gold remains a
promotion gate, not this task. Plan tasks: 59 before, 58 after (49 agent to 48; 10 human unchanged).
Capability `lexical-retrieval` changes from planned to shipped for structural archive integration
plus synthetic calibration. The `lexical-retrieval` group is removed from `docs/impl/plan.md`.
Dependents `prove-discovery-and-visualization-on-provided-archive` and
`prove-semantic-retrieval-on-provided-archive` now link this record. Next eligible agent task
remains `establish-versioned-udc-derived-scheme`. Updated
[lexical retrieval](../current/lexical-retrieval.md), `docs/impl/current.md`,
[evaluation foundation](../current/evaluation-foundation.md),
[evaluation](../current/evaluation.md), [developer tooling](../current/developer-tooling.md),
[corpus foundation](../current/corpus-foundation.md), `docs/guide/development.md`,
`docs/design/spec.md`, this record index, and the 0070/0071/0072 remaining plan links.
No human review handoff applies. Next action: none for this task. The audit note is resolved by
[0074](0074-lexical-retract-superseded-lexical-chunks.md).
