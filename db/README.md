# Database migrations

`db/migrations/` holds legacy dbmate-shaped SQL (`YYYYMMDDHHMMSS_slug.sql`). `db/schema.sql` is a
committed SQL snapshot; current checks do not prove it is a dump of an applied revision history.
Generated ODCS DDL under `contracts/generated/postgres/` does not auto-migrate a live database.

Destructive statements (`DROP TABLE`, `TRUNCATE`, `DROP COLUMN`) require an explicit
`-- arxiv-int: destructive-approved` marker in the migration file. `make contracts-evolution`
enforces ordering, approval markers, and schema dump coverage. When `dbmate` is on PATH and
`DATABASE_URL` is set, `dbmate status` is also invoked.

The regex and marker are limited lint checks; missing dbmate is currently skipped. See the
[implementation review](../docs/impl/records/0015-govern-review-data-engineering-tooling.md).
The target is contract-derived SQLAlchemy metadata and immutable Alembic Python revisions, with
verified legacy adoption and live catalog comparisons. The
[refactoring task](../docs/impl/plan.md#refactor-contract-schema-and-migration-tooling) implements
that workflow before canonical-store acceptance. Alembic is not installed or usable here yet.
