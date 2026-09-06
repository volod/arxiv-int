# Task Record

## Task and scope

- Id / capability / checkpoint: `refactor-contract-schema-and-migration-tooling` /
  `contract-governance` / `review-foundation-and-store-boundaries`
- State: accepted for its offline scope; every declared gate passed, including `make ci`.
- Source: `docs/impl/plan.md#refactor-contract-schema-and-migration-tooling` at code revision
  `1346674`. The working tree was clean at task start. `docs/impl/records/0016-...` was edited by
  its own in-flight owner during this task and is preserved untouched.
- Initial count: unavailable at task start -- `make plan-status` refused to run because
  `make lint-spec-plan` already failed on two `design-simple-operator-entrypoints` findings that
  predate this task. Those were repaired at the user's explicit request near the end of this task
  (see Close or resume). After repair and plan removal `make plan-status` reports 84 tasks
  (73 agent, 11 human); next agent task `implement-contract-data-quality-checks`.
- Accepted task:

```markdown
#### refactor-contract-schema-and-migration-tooling

Replace SQL text and optional dbmate checks with contract-derived Python schema objects and a
required, reviewable Alembic revision workflow.

- Serves: `contract-governance` -- [Evolution and migrations](../design/spec.md#evolution-and-migrations)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-data-engineering-tooling-1](records/0015-govern-review-data-engineering-tooling.md#audit-handoff).
- Dependencies: [Deterministic schema generation](records/0011-contract-gov-implement-deterministic-schema-generation.md);
[Evolution and migration policy](records/0012-contract-gov-enforce-evolution-and-migration-policy.md);
[Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md).
- User-visible outcome: A contract change yields reviewable Python migration operations and explicit
revision/drift status without maintaining a second handwritten table model.
- Scope boundary: Replace schema/migration plumbing and preserve semantic/evolution policy; provide
the offline workflow and live adapter. Actual legacy adoption and pinned-store upgrade acceptance
belong to `create-canonical-relational-schema`; no automatic adoption of an operator database.
- Data and artifact paths: `src/arxiv_int/contracts/{generate,sqlalchemy,evolution}/`,
`src/arxiv_int/migrations/versions/`, legacy `db/migrations/`, `db/schema.sql`, `pyproject.toml`,
`uv.lock`, feature metadata, Make/CLI, mirrored tests, and `$DATA_DIR/migrations/<run-id>/`.
- Execution path: Normalize existing ODCS bindings into schema-qualified SQLAlchemy Core metadata;
preserve types/decimal precision/nullability/keys/references/descriptions with named constraints;
fail unsupported mappings. Compile review DDL with the PostgreSQL dialect, retire competing generic
SQL export and regex conformance, and generate candidate immutable Alembic Python revisions using
frozen definitions and contract fingerprints. Implement revision/check/status/upgrade/downgrade
wrappers with existing environment/root policy, owned-object filters, prior ownership for removals,
secret redaction, graph/checksum checks, and explicit irreversible-change handling. Retain legacy
SQL as adoption evidence; require catalog equivalence before stamping. Reuse the shared evolution
classifier; update optional dependencies, exact output-sensitive pins, lock, licences, and setup.
- Acceptance gates: Network-free regressions prove schema-qualified collisions, renamed/removed
fields, nullability/type/default/constraint changes, unsupported metadata, missing revisions, multiple
heads, cycles, missing runner, and unsafe adoption fail correctly. Generated Python revisions and
offline PostgreSQL DDL are deterministic; old revisions ignore later contract edits; unrelated/dbt
objects are excluded without hiding owned deletions; missing live evidence reports not-run. Existing
serialization and semantic gates, `make ci`, and `make quality` pass. Offline success does not claim
an applied or conformant live database.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

`src/arxiv_int/contracts/sqlalchemy/` replaces generic SQL export as the PostgreSQL model:

- `normalize.py` turns one ODCS document into typed `NormalizedTable`/`NormalizedColumn` values,
  keeping logical/physical type, decimal precision/scale, `maxLength`, nullability, primary-key
  position, uniqueness, description and one `foreignKey` target. Unknown property keys, unknown
  `logicalTypeOptions`, unknown logical types, non-`foreignKey` relationships, malformed targets,
  a primary key without a position, duplicate field names, more than one schema object and empty
  schemas raise `UnsupportedContractMappingError`. A declared `x-arxiv-int.partitionKey` becomes an
  explicit column rather than a separate `ALTER TABLE`.
- `metadata.py` builds one schema-qualified SQLAlchemy Core `MetaData` with a shared naming
  convention (`pk_`/`fk_`/`uq_`/`ck_`/`ix_`), refusing duplicate ODCS schema identities, duplicate
  physical bindings, duplicate key positions, unknown relationship targets and missing primary keys.
- `ddl.py` compiles review DDL with the PostgreSQL dialect: per-contract files plus an ordered
  `baseline.sql` produced with `sort_tables`, with `COMMENT ON` statements so descriptions survive.
- `catalog.py` compares a live catalog to contract metadata by compiled column definitions, not SQL
  substrings, restricted to owned tables and retaining prior ownership so deletions stay visible.

`src/arxiv_int/migrations/` is the owned Alembic script directory: `env.py` (offline and online,
both filtered to owned schemas/tables), `script.py.mako`, immutable `versions/`,
`revision_manifest.json` (per-file SHA-256 and parents) and `head_state.json` (the owned schema
state the history produces). `0001_baseline_contract_schema.py` is the generated baseline; it is
excluded from Ruff formatting so a formatter upgrade cannot rewrite an applied revision.

`src/arxiv_int/contracts/migrations/` implements the workflow with generation, checks and apply
separated: `state.py` (frozen state and reviewed operation diff), `operations.py` (frozen Python
literals per operation), `render.py` (revision module rendering, review notes, irreversible
downgrades), `authoring.py` (candidate revision, manifest, head state), `graph.py` (parents, cycles,
single head, checksum immutability, head-state agreement), `runner.py` (Alembic config, explicit
`ARXIV_INT_MIGRATION_DATABASE_URL` selection, credential redaction, offline SQL, not-run outcomes),
`adoption.py` (legacy inventory, binding mapping, refusal-first stamping), `check.py` and
`commands.py`. `arxiv-int db revision|check|status|upgrade|downgrade|adopt` and `make db-*` expose
them; `make db-check` joins `make ci`.

Retired: `contracts/evolution/conformance.py` (regex table/column diffing), the dbmate ordering,
approval-marker, schema-dump and `dbmate status` checks in `contracts/evolution/migrations.py`, the
Data Contract CLI `sql` export path, and the partition/primary-key `ALTER TABLE` lines in
`generate/adapters.py`. `contracts/evolution/migrations.py` is now a thin bridge to the migration
report plus retained legacy evidence, and the shared evolution classifier is unchanged.
`db/migrations/` and `db/schema.sql` are retained only as adoption evidence.

Dependencies: `sqlalchemy==2.0.52` in the `contracts` extra and `alembic==1.19.2` in the `store`
extra, both exact because their output is committed and drift-checked; `uv.lock`, the feature
catalog licences and the GitHub workflow carry them. Every syncing Make target now shares one
`SYNC_EXTRAS` set, because consecutive targets with different extras were uninstalling each other's
dependencies before `make test` ran. `GENERATOR_VERSION` moved to `2.0.0`;
`contracts/generated/`, the committed evolution baselines and the golden fingerprints were
regenerated.

Limitations: no database has been stamped or upgraded. Offline success makes no claim about an
applied or conformant live store; live upgrade, previous-release-to-head and adoption evidence
remain with `create-canonical-relational-schema`. Current state:
[contracts](../current/contracts.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Schema-qualified collisions, renamed/removed fields, nullability/type/default/constraint changes, unsupported metadata | `tests/contracts/sqlalchemy/test_normalize.py`, `test_metadata_ddl.py`; `tests/contracts/migrations/test_state_and_render.py` | pass; fixtures only |
| Missing revisions, multiple heads, cycles, missing parent, missing runner, edited revision | `tests/contracts/migrations/test_graph_and_check.py` | pass; network-free |
| Unsafe adoption fails; legacy SQL retained as evidence | `tests/contracts/migrations/test_runner_and_adoption.py`; `tests/contracts/evolution/test_migrations_and_product.py` | pass; adoption stays refused, valid negative |
| Deterministic generated Python revisions and offline PostgreSQL DDL | `tests/contracts/migrations/test_offline_sql.py`; `test_graph_and_check.py::test_generated_revision_files_are_deterministic` | pass |
| Old revisions ignore later contract edits | `test_graph_and_check.py::test_second_revision_only_covers_the_new_change` | pass |
| Unrelated/dbt objects excluded without hiding owned deletions | `tests/contracts/sqlalchemy/test_catalog.py`; `test_runner_and_adoption.py::test_owned_object_filter_excludes_foreign_relations` | pass |
| Missing live evidence reports not-run | `arxiv-int db status` exit 2; `test_runner_and_adoption.py::test_missing_database_is_not_run_never_success` | pass; never reported as success |
| Existing serialization and semantic gates | `make contracts-check`; `make contracts-evolution` (20 contracts, disposable Postgres accepted `baseline.sql`); `make ontology-check` | pass |
| Migration gate | `make db-check` -- head `0001`, live evidence `not-run` | pass |
| `make ci` | `make ci` | pass; 522 tests, all gates green |
| `make quality` | `make coverage` 90.31% (floor 90); `make lint-md`; `make build` (wheel ships the Alembic environment, template and manifests); `make complexity-gate`; `make shell-lint-gate` | pass |
| Live upgrade, downgrade, previous-release-to-head, stamping | none | not-run; no database was contacted, owned by `create-canonical-relational-schema` |

Artifacts: `contracts/generated/postgres/*.sql` and `baseline.sql`,
`src/arxiv_int/migrations/versions/0001_baseline_contract_schema.py`, `revision_manifest.json`
(baseline checksum recorded in the manifest), `head_state.json`. Offline review SQL is written under
`$DATA_DIR/migrations/<run-id>/upgrade.sql` and was not retained.

## Audit handoff

`none identified` for the reviewed scope: contract normalization, SQLAlchemy metadata and review
DDL, the Alembic revision workflow, live catalog comparison, legacy adoption, and the retired dbmate
and regex checks.

## Close or resume

Every declared gate passed, including `make ci` (522 tests) and the `make quality` gates. Current
contracts, the database README, developer tooling, the record index and the 0015 audit note link
this record; `AUD-data-engineering-tooling-1` is resolved. The task block was removed from the plan
and its two references (`create-canonical-relational-schema`,
`implement-contract-data-quality-checks`) point at this record.

Two plan findings predating this task blocked `make lint-spec-plan` for its whole duration and were
repaired at the end on the user's explicit instruction, in the work owned by
`design-simple-operator-entrypoints`: its record now declares `AUD-operator-entrypoints-1` in the
audit handoff, routed to [implement-retryable-setup-command](../plan.md#implement-retryable-setup-command),
and is linked from the [record index](README.md). No other part of that in-flight task was changed,
including the owner's own concurrent edit to its original-request text.

Counts: unavailable before the repair; after it `make plan-status` reports 84 tasks (73 agent,
11 human), statuses 29 CLEAR, 44 RUN NEEDED, 10 HUMAN-GATED and 1 BLOCKED BY HUMAN, with 79 tasks
holding open prerequisites. Next agent task: `implement-contract-data-quality-checks`.

Capabilities: contract-governance gains contract-derived Python schema objects, a required reviewable
Alembic revision workflow, offline review SQL and refusal-first adoption. No live database behavior
is claimed. Working tree contains only the intended source, contract, test and documentation files.
No services were left running; the disposable Postgres container used by `make contracts-evolution`
is removed by its own cleanup. No commit or push was made.
