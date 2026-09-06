# Database migrations

`db/migrations/` holds dbmate-shaped SQL (`YYYYMMDDHHMMSS_slug.sql`). `db/schema.sql` is the
reviewed dump of applied migrations. Generated ODCS DDL under `contracts/generated/postgres/` does
not auto-migrate a live database.

Destructive statements (`DROP TABLE`, `TRUNCATE`, `DROP COLUMN`) require an explicit
`-- arxiv-int: destructive-approved` marker in the migration file. `make contracts-evolution`
enforces ordering, approval markers, and schema dump coverage. When `dbmate` is on PATH and
`DATABASE_URL` is set, `dbmate status` is also invoked.
