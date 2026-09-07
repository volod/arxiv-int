# Foundation Store Acceptance Boundary Repair

## Task and scope

- Id: `refactor-foundation-store-acceptance-boundaries`; capability: `canonical-store`.
- State: accepted.
- Source: checkpoint 0027 at revision `2597b531`; checkpoint record/index already edited.
- Initial count: 78 tasks after adding this prerequisite (68 agent, 10 human).
- Amendments: three, documented below.

```markdown
#### refactor-foundation-store-acceptance-boundaries

Repair verified entrypoint, catalog and publication gaps found by the foundation checkpoint.

- Serves: `canonical-store` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Setup](records/0022-runtime-implement-retryable-setup-command.md);
[Projections](records/0025-store-implement-rebuildable-search-and-graph-projections.md).
- User-visible outcome: Failed prerequisites and missing validation evidence cannot report success;
active data and verified catalog identities survive refused retries and adoption.
- Scope boundary: Repair observed Make/dotenv parity, dbt evidence/secret/publication handling,
active projection rebuild refusal, and revision-aware catalog/adoption/setup checks. Preserve
immutable revisions, canonical rows, existing producer semantics and optional imports; no models,
corpus processing, service reset or operator database adoption.
- Data and artifact paths: `Makefile`, `scripts/shared/dotenv.sh`, runtime setup, transformations,
PostgreSQL and projection modules under `src/arxiv_int/`, mirrored tests, frozen catalog evidence
under `src/arxiv_int/migrations/`, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Reproduce failures with deterministic regressions and declared disposable database
runs. Propagate dependency/environment failures before commands; reconcile shell export/whitespace
semantics. Require current selected model/test evidence and existing relations before activation,
redact invocation errors and artifacts, atomically publish pointers and refuse active rebuilds.
Compare owned live definitions against revision-bound pristine catalogs, refuse partial overlays
before stamping, and allow verified prior revisions to upgrade through setup.
- Acceptance gates: Regressions fail before repairs and pass after; no dependent command runs after
failed sync/config; missing/stale/failed dbt checks cannot activate; secret markers are absent from
retained results; failed retries preserve active relations and pointers. Disposable tests detect
catalog/constraint/role drift, preserve rows and refuse partial adoption; prior-to-head setup works.
Existing live schema/dbt/projection suites, `make ci`, and `make quality` pass.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

The declared live run reproduced initialization-server acceptance, and command tracing reproduced
cleanup dispatching into build. Both are within the requested run/fix review; the complete scope
amendment follows. Original task text above is unchanged.

```markdown
#### refactor-foundation-store-acceptance-boundaries

Repair verified entrypoint, catalog and publication gaps found by the foundation checkpoint.

- Serves: `canonical-store` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Setup](records/0022-runtime-implement-retryable-setup-command.md);
[Projections](records/0025-store-implement-rebuildable-search-and-graph-projections.md).
- User-visible outcome: Failed prerequisites and missing validation evidence cannot report success;
active data and verified catalog identities survive refused retries and adoption.
- Scope boundary: Repair observed Make/dotenv parity, dbt evidence/secret/publication handling,
active projection rebuild refusal, cleanup-only command dispatch, final database startup readiness,
and revision-aware catalog/adoption/setup checks. Preserve
immutable revisions, canonical rows, existing producer semantics and optional imports; no models,
corpus processing, service reset or operator database adoption.
- Data and artifact paths: `Makefile`, `scripts/shared/dotenv.sh`, runtime setup, transformations,
PostgreSQL and projection modules under `src/arxiv_int/`, mirrored tests, frozen catalog evidence
under `src/arxiv_int/migrations/`, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Reproduce failures with deterministic regressions and declared disposable database
runs. Propagate dependency/environment failures before commands; reconcile shell export/whitespace
semantics. Require current selected model/test evidence and existing relations before activation,
redact invocation errors and artifacts, atomically publish pointers and refuse active rebuilds.
Compare owned live definitions against revision-bound pristine catalogs, refuse partial overlays
before stamping, and allow verified prior revisions to upgrade through setup.
- Acceptance gates: Regressions fail before repairs and pass after; no dependent command runs after
failed sync/config; missing/stale/failed dbt checks cannot activate; secret markers are absent from
retained results; failed retries preserve active relations and pointers. Disposable tests detect
catalog/constraint/role drift, preserve rows and refuse partial adoption; prior-to-head setup works.
Existing live schema/dbt/projection suites, `make ci`, and `make quality` pass.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

Operator scope amendment during implementation:

> a) we have no exited database and public releases. so we can have single intitial migrations
> src/arxiv_int/migrations/versions b) do we need have under git control
> src/arxiv_int/migrations/catalogs, that json files looks like temporary staf that can changes
> every new run ont other computer

This explicitly authorizes prerelease consolidation. The initial revision becomes the sole
baseline; generated catalog snapshots are run evidence, not committed schema authorities.
Historical producer snapshots remain unchanged.

```markdown
#### refactor-foundation-store-acceptance-boundaries

Repair verified entrypoint, catalog and publication gaps found by the foundation checkpoint.

- Serves: `canonical-store` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Setup](records/0022-runtime-implement-retryable-setup-command.md);
[Projections](records/0025-store-implement-rebuildable-search-and-graph-projections.md).
- User-visible outcome: Failed prerequisites and missing validation evidence cannot report success;
active data and verified catalog identities survive refused retries and adoption.
- Scope boundary: Repair observed Make/dotenv parity, dbt evidence/secret/publication handling,
active projection rebuild refusal, cleanup-only command dispatch, final database startup readiness,
and revision-aware catalog/adoption/setup checks. Preserve canonical rows, producer semantics and
optional imports; consolidate the unreleased
migration history into one initial revision as authorized by the operator; no models,
corpus processing, service reset or operator database adoption.
- Data and artifact paths: `Makefile`, `scripts/shared/dotenv.sh`, runtime setup, transformations,
PostgreSQL and projection modules under `src/arxiv_int/`, mirrored tests, one initial Alembic
revision, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Reproduce failures with deterministic regressions and declared disposable database
runs. Propagate dependency/environment failures before commands; reconcile shell export/whitespace
semantics. Require current selected model/test evidence and existing relations before activation,
redact invocation errors and artifacts, atomically publish pointers and refuse active rebuilds.
Compare owned live definitions directly against contract metadata and initial revision definitions;
keep run catalog evidence only under DATA_DIR. Refuse drift and partial adoption before stamping.
Remove the superseded unreleased overlays and their historical upgrade assumptions; retain
generic future-revision tooling tests.
- Acceptance gates: Regressions fail before repairs and pass after; no dependent command runs after
failed sync/config; missing/stale/failed dbt checks cannot activate; secret markers are absent from
retained results; failed retries preserve active relations and pointers. Disposable tests detect
catalog/constraint/role drift, preserve rows and refuse partial adoption; initial setup and
repeat-at-head work, and interrupted initial application rolls back.
Existing live schema/dbt/projection suites, `make ci`, and `make quality` pass.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

Final optional-import review reproduced a base CLI failure without extras: setup dispatch imported
contract/schema dependencies before the environment phase could install them. This blocks the
explicit checkpoint invariant. The complete final repair scope follows; lazy phase imports reuse
the existing setup dispatcher.

```markdown
#### refactor-foundation-store-acceptance-boundaries

Repair verified entrypoint, catalog and publication gaps found by the foundation checkpoint.

- Serves: `canonical-store` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Setup](records/0022-runtime-implement-retryable-setup-command.md);
[Projections](records/0025-store-implement-rebuildable-search-and-graph-projections.md).
- User-visible outcome: Failed prerequisites and missing validation evidence cannot report success;
active data and verified catalog identities survive refused retries and adoption.
- Scope boundary: Repair observed Make/dotenv parity, dbt evidence/secret/publication handling,
active projection rebuild refusal, cleanup-only command dispatch, final database startup readiness,
optional-import isolation for the base CLI and setup bootstrap,
and revision-aware catalog/adoption/setup checks. Preserve canonical rows, producer semantics and
optional imports; consolidate the unreleased
migration history into one initial revision as authorized by the operator; no models,
corpus processing, service reset or operator database adoption.
- Data and artifact paths: `Makefile`, `scripts/shared/dotenv.sh`, runtime setup, transformations,
PostgreSQL and projection modules under `src/arxiv_int/`, mirrored tests, one initial Alembic
revision, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Reproduce failures with deterministic regressions and declared disposable database
runs. Propagate dependency/environment failures before commands; reconcile shell export/whitespace
semantics. Require current selected model/test evidence and existing relations before activation,
redact invocation errors and artifacts, atomically publish pointers and refuse active rebuilds.
Compare owned live definitions directly against contract metadata and initial revision definitions;
keep run catalog evidence only under DATA_DIR. Refuse drift and partial adoption before stamping.
Remove the superseded unreleased overlays and their historical upgrade assumptions; retain
generic future-revision tooling tests. Defer store imports until the schema phase executes.
- Acceptance gates: Regressions fail before repairs and pass after; no dependent command runs after
failed sync/config; missing/stale/failed dbt checks cannot activate; secret markers are absent from
retained results; failed retries preserve active relations and pointers. Disposable tests detect
catalog/constraint/role drift, preserve rows and refuse partial adoption; initial setup and
repeat-at-head work, and interrupted initial application rolls back.
Base CLI/help remains usable without extras. Existing live schema/dbt/projection suites,
`make ci`, and `make quality` pass.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.

```

## Implementation

The repair reuses existing runtime configuration, contract metadata, Alembic, dbt result handling,
projection registry transactions, and the disposable image harness. No dependency was added.

- Make propagates environment and sync failures before invoking a dependent command; cache paths
  remain one argument when they contain spaces. Bash counts only exported process overrides and
  trims whitespace before unquoting, matching the dependency-free Python dotenv grammar.
- Setup defers contract/schema imports to the schema phase. Projection argument parsing lives in
  dependency-free `stores/projections/cli.py`; the base CLI no longer imports SQLAlchemy merely to
  build help. This preserves bootstrap before optional extras are installed.
- dbt removes stale execution artifacts, requires matching current invocation ids, selected model
  and attached test outcomes, and existing generation relations before activation. Counts include
  views. Reserved schema/generation variables cannot escape runner ownership. Logs, target JSON,
  result details, and retained manifests redact known passwords; invocation errors use stable text.
- Active dbt generations and projection versions cannot be rebuilt. Use a new run id. Atomic dbt
  pointer replacement and separate check/refusal artifacts preserve prior publication, including a
  retry with missing database configuration. Projection build and cleanup share a database advisory
  lock across tooling roots; cleanup honors the selected kinds, rechecks eligibility and dispatches
  only cleanup, never build.
- Disposable readiness requires PostgreSQL's final startup marker and TCP readiness. Accepting the
  temporary initialization server caused real resets/shutdowns in the baseline suite.
- The operator-authorized prerelease consolidation replaces three unreleased revisions with one
  `0001_initial_store.py`. Frozen SQLAlchemy metadata includes canonical, staging and projection
  lifecycle tables, with narrow SQL for partitions, roles, functions and triggers. Deterministic
  table/index order keeps offline SQL stable. Duplicate unused runtime DDL copies were removed.
  `revision_manifest.json` and `head_state.json` remain intentional versioned review inputs.
- There is no committed `migrations/catalogs/` directory. Live comparison uses contract metadata and
  the frozen initial revision directly. Observed catalog definitions are per-run diagnostic evidence
  under `DATA_DIR`. Comparison checks keys/references/check definitions and validation, defaults,
  indexes, protected table privileges, role attributes, functions and the embedding trigger;
  existing physical store checks also run before setup reuses the current head.

The initially attempted pristine-catalog snapshot approach was superseded by the operator's
amendment. Its captures remain historical diagnostic evidence only. No historical database upgrade
is required before first deployment; generic future revision/evolution tests remain. The initial
migration refuses destructive downgrade explicitly. Historical producer records retain their
original revision numbers and decisions. Current behavior is documented in
[Canonical store](../current/canonical-store.md), [Contracts](../current/contracts.md), and
[Portable runtime](../current/portable-runtime.md).

## Acceptance evidence

Evidence root: `$DATA_DIR/architecture-review/20260906-foundation-store/`. Commands use the shared
bootstrap and configured environment. Live commands explicitly declare their external Docker run;
all databases are disposable fixtures. The final resumed run uses the currently configured root;
prior logs are retained in its `prior-run/` directory. No operator database was migrated or adopted.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Dependency/config failure propagation and shell parity | `tests/compose/test_make_failures.py`; `tests/config/test_parity.py`; `runtime-baseline.log`, `runtime-fixed.log` | valid-negative before repair (27 failures); repaired fixtures cover sync/config failures and successful dispatch, exported overrides, quotes and spaces |
| Base CLI without extras | `tests/runtime/setup/test_optional_imports.py` starts Python with `-S`; `imports-negative.log`, `imports-fixed.log` | 3 failed before, 3 passed after; help, setup help and features work without site packages |
| Current required dbt evidence and secret handling | `tests/transformations/test_publication_boundaries.py`, `test_validation.py`; live dbt suite | missing/stale/failed evidence cannot activate; synthetic password absent from retained failure detail |
| Active publication and failure preservation | `tests/transformations/test_lock_and_activation.py`; live dbt/projection suites; `retry-negative.log`, `retry-fixed.log` | atomic replacement failure preserves old pointer; active rebuild refused; missing-URL retry regression failed before and passes after |
| Cleanup is cleanup; active objects survive stale plans | `tests/stores/projections/test_publication_boundaries.py`; live projection suite | no build on cleanup; selected-kind filtering has a failing/passing regression; active metadata/objects remain; retired lexical object removed without changing canonical rows |
| Final database startup | `tests/stores/test_disposable_readiness.py`; `prior-run/live-baseline.log`, `live-resumed.log` | valid-negative baseline: 3 failed, 15 passed with initialization shutdown/reset; repaired live suite passes |
| Initial application, retry, rollback, constraints and COPY | `tests/integration/postgres/test_canonical_schema.py` | pass in declared suite: empty-to-head, repeat preserving rows, interrupted real initial DDL rollback/retry, explicit teardown refusal, fact/vector checks, dbt isolation, staging upsert and quality |
| Live catalog/adoption/setup boundaries | `tests/integration/postgres/test_catalog_boundaries.py`; `catalog-final.log` | 5 passed: weakened same-name CHECK, missing FK, forbidden dbt grant, missing projection table, detached partition all refuse inspection/setup reuse/adoption |
| Setup physical checks | `tests/stores/test_catalog_inspection.py`; `setup-negative.log`, `setup-fixed.log` | 1 failed/1 passed before, 2 passed after; current-head reuse cannot bypass partition validation |
| Single revision and deterministic future tooling | `make db-check`; `tests/contracts/migrations/`; `tests/contracts/sqlalchemy/` | graph/checksum/head state, deterministic SQL, future additive revisions and logical CHECK grouping covered |
| Declared integrated live suite | `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1 ARXIV_INT_RUN_DBT=1 ARXIV_INT_RUN_PROJECTIONS=1 ARXIV_INT_RUN_EXTENSION_PROBES=1 PYTEST_ADDOPTS="tests/integration --basetemp=$review_dir/live-resumed -x" make test` | 22 passed; `live-resumed.log`; final additional partition/setup case covered by the separate 5-test catalog run |
| Required CI | `make format`; `make ci`; `ci-final.log` | pass; 791 passed, 18 expected live-test skips |
| Infrastructure quality | `make quality`; `quality-final.log` | pass; diagnostic coverage, Markdown and package build; no percentage gate |

An intermediate initial-schema check found only function-body boundary whitespace; normalization
was corrected and reinspection returned revision `0001` with no findings. A prior disposable suite
was interrupted during consolidation (13 passed), and another process ended without completion;
neither counts as acceptance. The completed resumed suite replaces them. Sandbox-only CI first
could not access the configured uv cache; the required host run uses the approved cache access.
The remaining Pandera/Polars deprecation warning is upstream behavior; it does not fail validation.

## Audit handoff

All verified blockers are repaired within this prerequisite. Required CI and quality pass.
New audit notes: none identified within the repaired boundaries. Integrated disposition and the one
incoming nonblocking root-race note
belong to [checkpoint 0027](0027-store-review-foundation-and-store-boundaries.md).
No new feature, model, corpus processing, reset, or operator database adoption was introduced.

## Close or resume

Accepted after deterministic, disposable live, CI and quality gates. The final projection command
rerun also passes (`projections-final.log`, 1 live test). The selected-kind cleanup regression is
retained as `cleanup-kind-negative.log` and `cleanup-kind-fixed.log`.

Current-state pages and the record index link the accepted repair and checkpoint. Both satisfied
blocks were removed; downstream dependencies now link the accepted checkpoint. Plan counts: 77 at
review start, 78 after planning this prerequisite, 76 after acceptance (66 agent, 10 human).
`canonical-store` is shipped for the documented fixture foundation; real corpus quality and operator
recovery remain with their existing owners. Next action: `implement-local-inference-adapters`.
No commit, push, operator database adoption or reset was performed.
