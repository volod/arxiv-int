# Developer Tooling

See [record 0050](../records/0050-govern-refactor-package-layout-and-make.md) for the split Makefile,
packaged resources, nested packages, and mirrored tests tree.

## Environment

`pyproject.toml` declares Python 3.12+ package metadata and a `dev` extra. `uv.lock` fixes the full
resolution. `make bootstrap` creates a missing `.env` from `.env.example`, append-syncs newly
declared variables without replacing operator values, installs the locked environment, and runs
the package identity check followed by readiness. `make setup` uses the same dotenv sync, then
prepares models, services and schema; see [Portable runtime](portable-runtime.md). Direct uv
investigations use
`scripts/shared/common.sh` so `DATA_DIR`, caches, and adaptive link mode have one implementation.
Its functions use the `arxiv_int_` namespace; direct uv investigations begin with
`arxiv_int_load_env`.

## Quality gates

The root `Makefile` includes grouped fragments under `make/` (`bootstrap`, `services`,
`contracts`, `transform`, `inference`, `pipeline`, `quality`) with `##@` help sections.
`make help` lists those targets. The composed workflows are:

- `make ci` runs formatting, linting, typing, Radon and cognitive complexity, shell parsing and
  ShellCheck, documentation links, spec-plan integrity, contract generation drift, evolution policy
  without disposable Postgres, the migration revision graph (`make db-check`), ontology checks,
  structured-output schema drift, and deterministic tests (`make test` excludes both `heavy` and
  `archive`). It does not start Docker or read operator archives.
- `make test-heavy` runs tests marked `heavy`: live Compose `docker compose config` rendering,
  disposable Postgres apply of baseline SQL, and declared store/dbt/projection/image suites.
- `make test-archive` loads `.env` and runs the ordinary corpus pipeline plus independent integrity
  cross-checks against the configured archive.
- `make contracts-evolution-live` applies generated `baseline.sql` on disposable Postgres.
- `make quality` adds a diagnostic coverage report (also excluding `heavy` and `archive`),
  Markdown lint, and source/wheel builds. A numeric coverage percentage is not an acceptance gate
  ([behavior-first test policy](../records/0026-foundation-adopt-behavior-first-test-policy.md)).

GitHub Actions runs `make ci-github`, the same required gate with a lighter dependency profile,
on Python 3.12 and 3.13 after `uv sync --locked --extra dev --extra contracts --extra graph --extra store
--extra lake --extra data-quality --extra inference --extra transform`. The `store` extra carries
Alembic, which owns the migration revision graph checked by `make ci`. The `lake` and
`data-quality` extras carry Polars/PyArrow and Pandera for contract-derived dataset checks. The
`transform` extra carries dbt Core and `dbt-postgres` for isolated derived-model runs, including
projection input models. Local syncing Make targets share one `SYNC_EXTRAS` set so consecutive
targets cannot uninstall each other's dependencies. `ci-github` removes `extraction` from that set
for all its prerequisite syncs, preserving the workflow's dependency profile throughout the gate.

GitHub omits the optional `extraction` extra, so the native Tika test skips there. The isolated
worker import supports type checking with the backend absent or installed without typing metadata;
lightweight regression checks hide site packages for both Python targets
([CI import repair](../records/0067-foundation-fix-optional-tika-ci-typecheck.md)).

Tests under `tests/quality/` exercise failure cases for the documentation checks rather than only
asserting the repository passes. `make quality-report` reports source and shell files over the
250-line soft limit; generated Alembic revisions under `src/arxiv_int/migrations/versions/` are
frozen review evidence and are excluded from Ruff formatting so a formatter upgrade cannot rewrite an
applied revision. Generated Pydantic adapters under
`src/arxiv_int/resources/contracts/generated/pydantic/` are excluded for the same reason. Those
revision files and `migrations/env.py` are also omitted from branch coverage
because they execute only against a live database; the declared schema suite covers them.
Configuration tests exercise missing-template copying, append-only declaration
sync, idempotency, and preservation of operator values.

## Artifact paths

`.env.example` declares `DATA_DIR=.data`. Relative values resolve against the project root. Runtime
results use `$DATA_DIR/<method>/<run-id>/`; Ruff, mypy, pytest, and complexipy caches stay below the
same root. `.gitignore` excludes runtime artifacts, local environments, secrets, caches, and root
build outputs without hiding same-named source subpackages.

`.env.example` also documents the operator roots -- `ARCHIVE_DIR`, additional named silos,
`RESULTS_DIR`, `PGDATA_DIR`, their derived defaults, and the optional second database device -- as
commented placeholders annotated with the storage class each one needs. Only `DATA_DIR` and
`LOG_LEVEL` carry values, so no machine-specific path is committed. The resolution, validation,
storage evidence, and empty layout are documented in [Portable runtime](portable-runtime.md).
`scripts/shared/common.sh` preserves pre-existing process values while loading `.env`, then exports
`DATA_DIR` and the tool caches derived from it.

Product ODCS, ontology, operator configs, and the dbt project ship as
`src/arxiv_int/resources/{contracts,ontology,configs,dbt}` so a wheel install does not depend on
checkout-root trees. `arxiv_int.resources.paths` prefers a same-named overlay under a caller
`project_root` when that directory exists.
