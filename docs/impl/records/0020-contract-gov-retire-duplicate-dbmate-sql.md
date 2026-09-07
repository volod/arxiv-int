# Task Record

## Task and scope

- Id / capability / checkpoint: `retire-duplicate-dbmate-sql` / `contract-governance` /
  `review-foundation-and-store-boundaries`
- State: accepted
- Source: ad hoc operator request after [0019](0019-contract-gov-implement-contract-data-quality-checks.md);
  the committed `db/*.sql` dumps were a stale second schema beside Alembic.
- Initial count: 82 tasks (71 agent, 11 human); next agent task was
  [Canonical relational schema](0021-store-create-canonical-relational-schema.md).
- Accepted task:

```markdown
#### retire-duplicate-dbmate-sql

Remove the parallel dbmate SQL dump so schema change has one authored history.

- Serves: `contract-governance` -- [Evolution and migrations](../design/spec.md#evolution-and-migrations)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Contract schema and migration tooling](0017-contract-gov-refactor-contract-schema-and-migration-tooling.md).
- User-visible outcome: `db/` no longer looks like a writable SQL migration engine; operators
follow Alembic revisions, and leftover CREATE TABLE dumps are not committed beside them.
- Scope boundary: Delete the stale product SQL dumps, stop requiring them in evolution checks,
keep adoption inventory for optional/fixture SQL, and document why `$DATA_DIR` is the wrong home
for this evidence. Do not apply migrations, stamp a database, or absorb
`create-canonical-relational-schema`.
- Data and artifact paths: `db/`, `src/arxiv_int/contracts/{evolution,migrations}/`,
`tests/contracts/migrations/`, spec/current/plan/development docs, this record.
- Execution path: Treat ODCS plus Alembic Python revisions as the only product schema history.
Inventory leftover SQL only when present (tests or a future operator dump). Fail evolution if
`db/migrations/*.sql` reappears in the product tree. Rewrite `db/README.md`. Point
`db/schema.sql` at a later live catalog dump, not a hand-maintained copy.
- Acceptance gates: Product tree has no `db/migrations/*.sql` or authored `db/schema.sql`.
Adoption still refuses unqualified/unknown names and missing live catalog evidence. Fixture
inventory still parses CREATE TABLE names. `make ci` passes; `make quality` if docs/infrastructure
gates require it. No live-store claim.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments:

```markdown
#### retire-duplicate-dbmate-sql

Remove the leftover `db/` tree so schema change has one authored history.

- Serves: `contract-governance` -- [Evolution and migrations](../design/spec.md#evolution-and-migrations)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Contract schema and migration tooling](0017-contract-gov-refactor-contract-schema-and-migration-tooling.md).
- User-visible outcome: The repository has no `db/` directory. Operators follow Alembic revisions;
live review SQL stays under `$DATA_DIR/migrations/<run-id>/`.
- Scope boundary: Delete `db/` including the explanatory README. Stop requiring leftover SQL in
evolution checks. Keep adoption inventory for optional/fixture SQL. Do not apply migrations or
absorb `create-canonical-relational-schema`.
- Data and artifact paths: `src/arxiv_int/contracts/{evolution,migrations}/`,
`tests/contracts/migrations/`, spec/current/plan/development docs, this record.
- Execution path: Treat ODCS plus Alembic Python revisions as the only product schema history.
Inventory leftover SQL only when a test or operator supplies it. Fail evolution if a product
`db/migrations/*.sql` dump is recreated. Live catalog dumps use `$DATA_DIR`, not a committed
`db/schema.sql`.
- Acceptance gates: Product tree has no `db/` directory. Adoption still refuses unqualified/unknown
names and missing live catalog evidence. Fixture inventory still parses CREATE TABLE names.
`make ci` passes. No live-store claim.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

Reason/authorization: operator asked to delete `db/` entirely after the README-only remainder was
still confusing. Original task text is retained above.

```markdown
#### retire-duplicate-dbmate-sql

Remove leftover dbmate SQL inventory from product code now that `db/` is gone.

- Serves: `contract-governance` -- [Evolution and migrations](../design/spec.md#evolution-and-migrations)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Contract schema and migration tooling](0017-contract-gov-refactor-contract-schema-and-migration-tooling.md).
- User-visible outcome: Evolution and tests no longer mention a parallel SQL history. Adoption
refuses stamping until live catalog equivalence is proved.
- Scope boundary: Delete SQL-dump inventory, evolution guards, and tests that only asserted the
gone `db/` tree. Keep Alembic revision checks and catalog-based adoption refusal. Do not apply
migrations.
- Data and artifact paths: `src/arxiv_int/contracts/{evolution,migrations}/`, matching tests,
spec/current/plan, this record.
- Execution path: Drop `legacy_evidence_findings` and `inventory_legacy_sql`. Keep
`adoption_findings` as a catalog-equivalence gate.
- Acceptance gates: Focused migration/evolution tests pass. `make ci` if run. No live-store claim.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

Reason/authorization: operator asked to delete tests and logic that only warned about the removed
historical dump.

## Implementation

The dumps under `db/migrations/` and `db/schema.sql` were leftover dbmate-era copies of generated
DDL. They were not run artifacts, so they did not belong in `$DATA_DIR`. They were also not the
execution engine: Alembic `0001` already creates schema-qualified tables, keys, and partition
columns the dumps omitted. Keeping them was a DRY second schema.

Deleted the whole `db/` tree. Then removed the SQL-dump inventory, evolution guard, fixture file,
and tests that only asserted the gone tree. Adoption now reports catalog-equivalence refusal only.
Live review SQL stays under `$DATA_DIR/migrations/<run-id>/`.

Limitations: no database was stamped. Current state: [contracts](../current/contracts.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| SQL-dump inventory and parallel-history tests removed | `rg` over `src/` and `tests/` for `inventory_legacy_sql` / `legacy_evidence_findings` | no matches |
| Adoption still refuses missing live catalog | `test_adoption_without_live_evidence_is_refused` | pass; valid negative |
| Focused migration/evolution tests | `pytest tests/contracts/migrations tests/contracts/evolution` | pass |
| `make ci` | full composed gate | not-run after this amendment; focused tests and doc-link/spec-plan lints passed |
| Live store / adoption of an operator database | none at 0020 close | not-run then; later recorded in [0021](0021-store-create-canonical-relational-schema.md) |

## Audit handoff

`none identified` for the reviewed scope: removing `db/` and the leftover SQL-dump inventory.

## Close or resume

Accepted. Counts unchanged: 82 tasks (71 agent, 11 human). Next agent task remains
[Canonical relational schema](0021-store-create-canonical-relational-schema.md).
Live review SQL stays under
`$DATA_DIR/migrations/<run-id>/`. No commit or push was made.
