# Task Record

## Task and scope

- Id / capability / checkpoint: `create-canonical-relational-schema` / `canonical-store` /
  `review-foundation-and-store-boundaries`
- State: accepted
- Source: [plan](../plan.md) (task removed on acceptance)
- Initial count: 82 tasks (71 agent, 11 human).
- Accepted task:

```markdown
#### create-canonical-relational-schema

Apply generated migrations for control, corpus, search, knowledge, ontology, and evaluation schemas
with partition and provenance constraints.

- Serves: `canonical-store` -- [PostgreSQL schemas](../design/spec.md#postgresql-schemas)
- Agent status: RUN NEEDED
- Dependencies: [Pinned ParadeDB + AGE image](records/0018-store-build-pinned-paradedb-age-image.md)
(AGE-enabled or AGE-disabled);
[Contract schema and migration tooling](records/0017-contract-gov-refactor-contract-schema-and-migration-tooling.md);
[Contract data-quality checks](records/0019-contract-gov-implement-contract-data-quality-checks.md);
[Evolution and migration policy](records/0012-contract-gov-enforce-evolution-and-migration-policy.md).
[Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md).

- User-visible outcome: Canonical documents, assertions, reviews, and run state have constrained,
queryable tables independent of search and graph projections.
- Scope boundary: Create schema, roles, partitions, staging/load adapters, and indexes required for
correctness; dbt owns derived relations, and corpus-scale tuning belongs to evaluation.
- Data and artifact paths: `src/arxiv_int/migrations/versions/`, `$DATA_DIR/migrations/<run-id>/`,
`src/arxiv_int/stores/postgres/`, and `tests/integration/postgres/`.
- Execution path: Generate reviewed Alembic Python revisions from ODCS-derived SQLAlchemy metadata;
apply them on the pinned disposable store and inspect actual catalog definitions, including schema,
types, defaults, precision, keys, checks, partitions and extension objects. Define typed literal
fact/provenance constraints, stable hash partitions, role grants, COPY staging, and bound SQLAlchemy
upserts; validate staged batches with shared quality checks. Create the `derived` schema and dbt
role boundary without owning dbt model tables. Test verified legacy-table relocation/adoption and
refuse unknown/drifted states before stamping. Declare the disposable integration run and retain
redacted revision, row-preservation, and live-schema evidence.
- Acceptance gates: Contract-to-live conformance passes; constraint and rollback fixtures reject
invalid fact shapes, missing provenance, duplicates, and cross-version vector mixing; migration
and clean-load schemas match. Empty-to-head, previous-release-to-head, repeat-at-head,
supported downgrade/upgrade or explicit irreversible refusal, and interrupted migration tests pass;
legacy adoption preserves rows and rejects partial/drifted databases. A missing database/tool is
not-run and keeps this task open; `make ci` and `make quality` pass.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

- Revision `0001` stays the frozen contract-table baseline. Overlay revision
  `0002_store_partitions_roles_constraints.py` (manifest SHA-256
  `e6bd6d07f93a860fcec12848b337e4a8b4c4fe69014e20df47aa66b57b878483`) does not import
  `arxiv_int.stores.postgres`. Runtime copies live in `src/arxiv_int/stores/postgres/`.
- HASH partitions use the logical primary key so foreign keys remain valid. Application `bucket`
  is `ctl.partition_bucket` / `partition_bucket()` (SHA-256 prefix, 16 remainders).
- Roles: `arxiv_int_migrator`, `arxiv_int_pipeline`, `arxiv_int_dbt`, `arxiv_int_reader` (`NOLOGIN`).
  `derived` is empty; dbt may create there and `SELECT` canonical tables, not write them or
  `alembic_version`.
- Fact CHECKs, embedding-profile trigger, UNLOGGED `staging.*`, bound upserts, and shared batch
  quality (explicit Polars schema so omitted nullable strings stay typed). Quality runs before
  COPY so staging `NOT NULL` cannot hide the gate.
- Live adopt relocates `public` leftovers, refuses partial/drift, stamps `0001` or `0002`.
- CLI/Make: `arxiv-int store apply-schema|inspect-schema`, `make db-apply-schema`; `db adopt`
  live-adopts when `ARXIV_INT_MIGRATION_DATABASE_URL` is set.
- Disposable store: pinned image `arxiv-int/postgres:17-0.25.6-age1.7.0`, host-owned PGDATA.
- Out of scope kept: dbt models, corpus-scale tuning, full `ctl.runs` ledger.
- Docs: [canonical-store.md](../current/canonical-store.md).
- Working tree also contains unrelated `0020` dbmate-retirement files; this task did not absorb them.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Empty-to-head, repeat-at-head, catalog conformance | `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1 pytest tests/integration/postgres/test_canonical_schema.py::test_empty_to_head_conformance_and_repeat` on image `arxiv-int/postgres:17-0.25.6-age1.7.0` | pass; revision `0002`; overlay findings empty |
| Previous-release-to-head row preservation | `test_previous_release_to_head_preserves_rows` | pass |
| Downgrade/upgrade round trip | `test_downgrade_and_upgrade_round_trip` | pass |
| Interrupted upgrade rolls back | `test_interrupted_upgrade_rolls_back` | pass |
| Fact/provenance/vector-mix constraints | `test_constraints_reject_invalid_facts_and_vector_mixing` | pass |
| dbt role isolation | `test_dbt_role_cannot_mutate_canonical_or_alembic` | pass |
| COPY, quality, upsert, Python/SQL bucket parity | `test_copy_upsert_and_quality_gate` | pass; row visible in `corpus.documents` |
| Legacy adoption preserve/refuse | `test_legacy_adoption_preserves_rows_and_refuses_drift` | pass |
| Full declared live suite | `DATA_DIR=/tmp/arxiv-int-schema-run ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1 pytest tests/integration/postgres/test_canonical_schema.py` | pass; 8 tests |
| Offline overlay and quality-frame units | `pytest tests/stores/test_canonical_schema_units.py tests/stores/test_canonical_schema_apply.py` | pass; missing URL/image is `not-run` |
| Missing database/tool | apply/adopt without URL or image | valid-negative `not-run` |
| `make ci` | `make ci` | pass; 617 passed, 9 skipped |
| `make quality` | coverage, Markdown, build | pass; coverage 90.33% (floor 90); lint-md; wheel |
| Operator PGDATA stamp | none | not claimed; disposable pytest evidence only |
| dbt models / `ctl.runs` ledger / corpus-scale | out of scope | not claimed |

## Audit handoff

none identified. Reviewed overlay-vs-0001 freeze, HASH-on-PK vs application `bucket`, staging
quality-before-COPY, dbt role grants, adoption refuse/stamp, and disposable evidence paths.
dbt execution is recorded in
[0024](0024-store-implement-dbt-transformation-foundation.md); run ledger stays with
`implement-run-ledger-and-atomic-artifacts`; projections stay with
`implement-rebuildable-search-and-graph-projections`.

## Close or resume

Accepted after the declared disposable schema run on
`arxiv-int/postgres:17-0.25.6-age1.7.0`, documentation, `make ci` (617 passed, 9 skipped), and
`make quality` (coverage 90.33%). Plan counts: 82 tasks before, 81 after (agent lane 71 to 70;
human 11 unchanged). Statuses after: 28 CLEAR, 42 RUN NEEDED, 10 HUMAN-GATED,
1 BLOCKED BY HUMAN.
Capability `canonical-store` is not marked shipped (dbt, projections, backup/restore remain).
Next agent work: `implement-dbt-transformation-foundation`. No commit or push was made.
