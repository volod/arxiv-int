# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-dbt-transformation-foundation` / `canonical-store` /
  `review-foundation-and-store-boundaries`
- State: accepted
- Source: [plan](../plan.md) (task removed on acceptance). Working tree also contains unrelated
  corpus, setup, and evolution-baseline files that this task did not absorb.
- Initial count: 79 tasks (69 agent, 10 human); next agent task
  `implement-dbt-transformation-foundation`.
- Accepted task:

```markdown
#### implement-dbt-transformation-foundation

Provide one local, contract-described dbt project and typed runner for relational transformations
before projection, catalog, and report builders introduce embedded business SQL.

- Serves: `canonical-store` -- [Transformations](../design/spec.md#data-transformations-and-quality)
- Agent status: RUN NEEDED
- Audit inputs: [AUD-data-engineering-tooling-2](records/0015-govern-review-data-engineering-tooling.md#audit-handoff).
- Dependencies: [Canonical relational schema](records/0021-store-create-canonical-relational-schema.md);
[Contract data-quality checks](records/0019-contract-gov-implement-contract-data-quality-checks.md).
- User-visible outcome: Named models can be built/tested locally with source lineage and quality
results; failed builds leave the active generation unchanged.
- Scope boundary: Establish dbt execution, ownership and synthetic model fixtures; domain tasks own
their business models. Do not add an orchestrator/service, replace canonical writes, require dbt
Python models on PostgreSQL, or materialize the archive in pandas.
- Data and artifact paths: `transformations/{dbt_project.yml,models,tests,macros}/`, generated dbt
contract YAML, `src/arxiv_int/transformations/`, `tests/transformations/`, feature/lock/Make files,
`$DATA_DIR/dbt/<run-id>/`, and `$RUNS_DIR/<run-id>/{manifests,quality}/`.
- Execution path: Pin compatible Python dbt Core 1.x and `dbt-postgres` in optional `transform`
dependencies; add typed parse/build/test invocation and rooted, environment-only credentials.
Consume generated source/column/test metadata; define descriptive staging/intermediate/mart model
conventions using source/ref. Build only in isolated `derived` generations with bounded threads and
exclusive target ownership; expose results for the existing pipeline to activate. Retain sanitized
manifest/run-results, selected model/input fingerprints and rule outcomes. Keep custom macros small;
invoke local Polars functions for Python-only preparation through the existing stage seam.
- Acceptance gates: dbt parse plus declared compile/build/test runs on synthetic pinned PostgreSQL
fixtures pass. Clean, repeated and incremental builds agree after insert/update/delete and policy
changes; failed data tests or interrupted/concurrent builds cannot activate partial data. Role tests
prove canonical relations and Alembic state cannot be mutated by dbt; migrations ignore dbt-owned
relations. Missing adapter/database and invalid models fail explicitly; secrets stay out of artifacts,
base imports remain light, and `make ci` / `make quality` pass. Keep required live checks open when
unavailable; no corpus-scale or domain-quality claim follows from the fixture DAG.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Pinned optional extra `transform` with `dbt-core==1.12.3` and `dbt-postgres==1.10.2` (Apache-2.0).
dbt Core 1.10/1.11 require `pathspec<0.13`, which conflicts with mypy 1.20.2 (`pathspec>=1.0`).
1.12.3 allows `pathspec>=0.9,<1.1`; the lock resolved `pathspec` to 1.0.4. The feature catalog
owns the group (`canonical-store`); `STAGE_FEATURES` activates it for `graph`, `domain-artifacts`,
and `report`. Make `SYNC_EXTRAS`, `LOCKED_EXTRAS`, and CI sync the extra.

Committed project `transformations/` (`arxiv_int`, profile `arxiv_int`) uses `source`/`ref`,
`SET ROLE arxiv_int_dbt` on run start, and small macros: `generate_schema_name` (always `derived`),
`generate_alias_name` (`<model>__g_<generation_id>`), and `reconcile_deletes`. The synthetic DAG
is `stg_documents` (view), `int_documents_current` (incremental delete+insert plus delete
reconciliation), and `documents_current` (table). A singular test fails when `fail_tests=true`.
Generated `contracts/generated/dbt/sources.yml` is copied into the working project as
`_generated_sources.yml`. Generic tests in generated YAML nest arguments under `arguments` for
dbt 1.12; `GENERATOR_VERSION` stays `2.1.0`.

Typed runner `src/arxiv_int/transformations/` (CLI parse stays light; `run_transform` lazy-imports
dbt through `require_module`):

- Commands: `arxiv-int transform parse|compile|build|test --run-id RUN_ID` and matching
  `make transform-*`. URL from `ARXIV_INT_TRANSFORM_DATABASE_URL` or
  `ARXIV_INT_MIGRATION_DATABASE_URL`. Build/test without a URL is `not-run` (exit 2). Parse/compile
  use dummy host `127.0.0.1` / password `unused` so profiles stay env_var-only.
- Isolation: exclusive `fcntl` lock under `$DATA_DIR/dbt/locks/` before assembling
  `$DATA_DIR/dbt/<run-id>/project/`. Threads capped at 4. Default select `tag:fixture tag:quality`.
- Activation: `$DATA_DIR/dbt/active-generation.json` only when `activatable` after a successful
  build or test. `--publish` copies sanitized manifests and rule outcomes to
  `$RUNS_DIR/<run-id>/{manifests,quality}/`.
- Secrets: drop `env` from manifests, redact URLs/passwords, sanitize logs.
- Polars seam: `prepare_document_frame` / `run_polars_prepare` via `StageContext`/`StageResult`.
  No dbt Python models and no pandas archive materialization.

Reuse: contract-generated sources/tests, canonical overlay roles/`derived`, staging COPY for
fixture rows, `compare_live_catalog` owned-object filter, `StageRunner` protocol.

Limitations: fixture DAG only; no orchestrator; dbt cannot write canonical or Alembic state;
no corpus-scale or domain-quality claim. Docs:
[canonical-store.md](../current/canonical-store.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Parse/compile/build/test, clean/repeat/incremental insert/update/delete, policy full-refresh | `ARXIV_INT_RUN_DBT=1 pytest tests/integration/dbt/test_live_dbt.py::test_parse_compile_build_test_and_parity` on image `arxiv-int/postgres:17-0.25.6-age1.7.0` | pass |
| Failed data tests cannot activate | `test_failed_tests_do_not_activate` | pass; active pointer unchanged |
| dbt role cannot mutate canonical/Alembic; migrations ignore derived | `test_dbt_role_and_migrations_ignore_derived` | pass; `compare_live_catalog` ignores `derived`; re-apply Alembic ok |
| Full declared live suite | `ARXIV_INT_RUN_DBT=1 pytest tests/integration/dbt/test_live_dbt.py` | pass; 3 tests in 33.71s; per-test disposable PGDATA |
| Missing adapter/database | unit `not-run` without URL; live suite skips unless `ARXIV_INT_RUN_DBT=1` and Docker/image | valid-negative |
| Invalid models fail explicitly | `pytest tests/transformations/test_invalid_models.py` | pass; missing `ref` fails compile |
| Secrets out of artifacts | `pytest tests/transformations/test_artifacts.py` | pass; password URL absent from sanitized JSON |
| Light base imports | CLI `add_transform_parser` does not import dbt; `run_transform` lazy-imports | pass via command/unit coverage |
| Offline units | `pytest tests/transformations/` | pass |
| `make ci` | `make ci` | pass; 700 passed, 12 skipped |
| `make quality` | coverage, Markdown, build | pass; coverage 90.95% (floor 90); lint-md; wheel |
| Corpus-scale / domain quality | out of scope | not claimed |

Live pytest used per-test `tmp_path` for `DATA_DIR`. Fixture evidence is not a real-archive run.

## Audit handoff

none identified. Reviewed generation isolation, exclusive locks, activation refusal, dbt-role
grants versus canonical/Alembic, catalog ignore of `derived`, secret-free artifacts, bounded
threads, and light base imports. Incoming `AUD-data-engineering-tooling-2` is resolved on
[0015](0015-govern-review-data-engineering-tooling.md).

## Close or resume

Accepted after the declared disposable dbt run on `arxiv-int/postgres:17-0.25.6-age1.7.0`,
documentation, `make ci` (700 passed, 12 skipped), and `make quality` (coverage 90.95%).
`make lint-doc-links` and `make lint-spec-plan` pass after plan removal. Plan counts: 79 tasks
before, 78 after (agent lane 69 to 68; human 10 unchanged). Next agent work:
`implement-rebuildable-search-and-graph-projections`. Capability `canonical-store` is not marked
shipped (projections, backup/restore remain). No commit or push was made.
