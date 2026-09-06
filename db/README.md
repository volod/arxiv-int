# Database migrations

Alembic owns the canonical revision graph, applied version state, and upgrade/downgrade execution.
Immutable Python revisions live in `src/arxiv_int/migrations/versions/`; each one carries frozen
definitions and the contract fingerprints it was generated from, so an old revision never follows a
later contract edit. `src/arxiv_int/migrations/revision_manifest.json` pins every revision checksum and
`head_state.json` records the owned schema state the history produces.

`db/migrations/` and `db/schema.sql` are retained **legacy dbmate-shaped evidence** for adoption
only. They are not an execution engine, and generated DDL never auto-migrates a live database.

Operator commands:

- `make db-revision MESSAGE=...` -- diff contract metadata against the frozen head state and write a
  candidate revision for review; no revision is written when nothing changed
- `make db-check` -- revision graph, checksum immutability, frozen-state agreement, and pending
  contract changes (part of `make ci`)
- `make db-status` / `make db-upgrade REVISION=...` / `make db-downgrade REVISION=...` -- act on the
  database named by `ARXIV_INT_MIGRATION_DATABASE_URL`; a missing runner or database is `not-run`
- `make db-adopt` -- inventory legacy SQL, map every declared table to a contract binding, and report
  why adoption stays refused

`arxiv-int db upgrade --sql` writes offline review SQL under `$DATA_DIR/migrations/<run-id>/` without
contacting a database.

Destructive changes are never automatic. A revision that drops an owned table or column renders an
irreversible `downgrade()` and carries `REVIEW_NOTES` requiring a confirmed removal (not a rename),
an approved plan, a backup, a free-space check, and a rollback path. Only a database proved
equivalent to the contract baseline by live catalog comparison may be stamped.

See [current contracts](../docs/impl/current/contracts.md) for the implemented behavior and its
limits, and the
[data engineering review](../docs/impl/records/0015-govern-review-data-engineering-tooling.md) for
the design that replaced the previous dbmate-shaped checks.
