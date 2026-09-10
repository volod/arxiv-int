# Single Initial Store Migration

## Task and scope

- Id / capability / checkpoint: `refactor-single-initial-store-migration` / `canonical-store` /
  none; this repeats the accepted pre-release consolidation policy of
  [record 0052](0052-store-refactor-prerelease-migration-consolidation.md) for the one revision
  added since.
- State: accepted; `make db-check` reports head `0001` with no pending operations and `make ci`
  passes.
- Source: ad hoc operator request (2026-09-10); no public release and no released dataset. Code
  revision `d413383` plus the accepted checkpoint/repair work of
  [0063](0063-corpus-review-corpus-and-control-integrity.md) and
  [0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md) in the working tree.
  `make plan-status` reported 62 tasks (52 agent, 10 human) before and after; this task is an ad hoc
  refactor and adds no plan entry.
- Accepted task: the operator's request, recorded verbatim, and the bounded task block written for
  it.

> We have no releases and no released datasets. Merge migration versions into a single 001 initial
> store migration to reflect the final design, improve readability of the initial data schema for
> humans, and avoid tracking schema changes during development.

```markdown
#### refactor-single-initial-store-migration

Collapse the second pre-release Alembic revision back into one initial store revision, so an empty
database applies one readable CREATE-time schema instead of a development history.

- Serves: `canonical-store` -- [Evolution and migrations](../design/spec.md#evolution-and-migrations)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Prerelease migration consolidation](records/0052-store-refactor-prerelease-migration-consolidation.md);
[Normalization, dedupe and chunking](records/0062-corpus-implement-normalization-dedupe-and-chunking.md).
- User-visible outcome: `make db-check` reports head `0001`, and the initial revision creates every
contract table with the partition and staging convention the store already applies to its peers.
- Scope boundary: Merge the overlay's two tables into frozen `0001`, delete the overlay, and realign
the head revision, manifest and head state. Do not change product contracts, runtime table modules
or operator commands, and do not invent an upgrade path from a deployed `0002`.
- Data and artifact paths: `src/arxiv_int/migrations/versions/`, `revision_manifest.json`,
`head_state.json`, `src/arxiv_int/stores/postgres/constants.py`, mirrored tests, and the
current-state canonical store page.
- Execution path: Move the overlay table definitions and contract fingerprints into `0001`; add both
tables to the revision's partition list and to `PARTITIONED_TABLES`; set `HEAD_REVISION` to `0001`;
rewrite the manifest and head state; align tests with one head.
- Acceptance gates: `make db-check` reports head `0001` with no pending operations; the emitted
offline DDL creates every owned corpus table with its staging clone and HASH partitions and stamps
only `0001`; `make ci` passes. Live disposable apply is not-run without
`ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1`.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: none; this is a bounded pre-release refactor with no dependent consumer.
```

- Amendments: none.

## Implementation

`0002_add_normalized_documents_and_duplicate_groups.py` is deleted and
`src/arxiv_int/migrations/versions/0001_initial_store.py` is again the only revision.
`corpus.normalized_documents` and `corpus.duplicate_groups` now sit with the other corpus contract
tables in the frozen `schema_metadata()`, immediately after `corpus.spans`, with the same column,
comment, primary-key and foreign-key definitions the retired overlay froze. Their contract
fingerprints moved into `0001`'s `CONTRACT_FINGERPRINTS`.

Consolidation also restores the store's own physical convention. `0001` HASH-partitions every
contract table whose ODCS declares `x-arxiv-int.partitionKey`, and `_store_metadata()` clones every
contract table into `staging`. The generated overlay could express neither, so the two tables were
the only ones of the nineteen partition-key contracts created unpartitioned and without a staging
clone. They are now `("corpus", "duplicate_groups", "duplicate_membership_id")` and
`("corpus", "normalized_documents", "normalized_document_id")` in both the revision's `_PARTITIONED`
and `stores.postgres.constants.PARTITIONED_TABLES`, which already listed them in `OWNED_TABLES`.
This is a schema change relative to applying `0001`+`0002`, and it is the intended one: no released
database exists, and the initial revision is the store's final design.

`HEAD_REVISION` is `0001` again, so `HEAD_REVISION == INITIAL_REVISION` and
`catalog_boundary.catalog_boundary_findings` compares live catalogs against the one revision it
already loads. `revision_manifest.json` holds a single entry with the recomputed checksum, and
`head_state.json` was rewritten from `contract_state(load_schema_model(...))` at revision `0001`,
so future `make db-revision` runs diff against a state that matches the contracts.

No contract, runtime table module, operator command or CLI surface changed. Current-state page:
[canonical store](../current/canonical-store.md).

Limitations: this is a pre-release consolidation, valid only because no database has been deployed
and no dataset released. A live database stamped `0002` cannot be upgraded to this tree; it must be
rebuilt. After a release, additive changes take new reviewed revisions as before.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Head `0001`, no pending operations | `make db-check` | Pass; `migration check passed at head 0001; live evidence: not-run` |
| One revision on disk and in the manifest | `ls src/arxiv_int/migrations/versions/`; `revision_manifest.json` | Pass; only `0001_initial_store.py`, one manifest entry with `downRevision: null` |
| Head state matches the contracts | regenerated `head_state.json` at revision `0001`, then `make db-check` | Pass; zero pending operations, so the frozen state equals `contract_state` for today's contracts |
| Every corpus contract table in the initial DDL | `tests/contracts/migrations/test_offline_sql.py::test_one_initial_revision_creates_every_owned_corpus_table` | Pass; `documents`, `source_occurrences`, `document_path_event`, `chunks`, `spans`, `normalized_documents` and `duplicate_groups` each get a `corpus` table, an `UNLOGGED staging` clone and a `_p00` HASH partition, and no `0002` stamp is emitted |
| Offline SQL stays deterministic and schema-qualified | `tests/contracts/migrations/test_offline_sql.py::test_offline_upgrade_sql_is_deterministic_and_schema_qualified` | Pass; identical on repeat, no path-event `ALTER TABLE` |
| Revision graph and product head | `tests/contracts/migrations/test_graph_and_check.py` | Pass; product head `0001`, single head, checksums match |
| Frozen revision aligns with contracts and store constants | `tests/stores/postgres/test_path_event_revision.py` | Pass; `HEAD_REVISION == INITIAL_REVISION == "0001"` |
| Store apply, adopt and stamp behavior | `pytest tests/stores/postgres -q` | Pass; partition expectations are driven by `PARTITIONED_TABLES`, which now includes both tables |
| Live disposable apply | not run | Not-run; requires `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1` and a disposable PGDATA. Offline SQL and catalog comparison are the evidence here |
| Corpus stage identity untouched | `make forecast`; `make stage STAGE=preflight..chunk` on a new run id after the change | Pass; all six stages `cache_hit=true`, so the revision, manifest and store constants are outside every corpus stage's declared asset closure, as expected for stages that publish to the lake |
| Required repository gate | `make ci` | Pass; 1269 tests, 50 deselected |

## Audit handoff

Unresolved task-local audit notes: `none identified`.

Reviewed scope: the revision directory, revision manifest and head state, `stores.postgres`
constants and catalog boundary, and the migration and store test suites. Self-review found one
defect before acceptance: the first merge left `normalized_documents` and `duplicate_groups` out of
`PARTITIONED_TABLES` while the revision partitioned them, so the two authorities disagreed; the
constants now match the revision and a test asserts the partitions exist in the emitted DDL.
Splitting the offline-SQL assertions into a second test also cleared a Radon `D` finding that the
added assertions introduced.

This record changes no product contract and establishes no live-database evidence. Live apply,
adoption and rebuild behavior stay with their existing owners.

## Close or resume

All acceptance gates pass except the explicitly not-run live apply. Next action: none. Indexed in
the [record index](README.md); current-state update in
[canonical store](../current/canonical-store.md). Plan counts unchanged at 62 tasks (52 agent,
10 human); next agent task remains
[prove-corpus-foundation-on-provided-archive](0068-corpus-prove-corpus-foundation-on-provided-archive.md).
Capability change: none; the canonical store's shape is unchanged apart from the two tables now
following the same partition and staging convention as their peers.
