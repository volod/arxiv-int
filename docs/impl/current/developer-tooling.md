# Developer Tooling

## Environment

`pyproject.toml` declares Python 3.12+ package metadata and a `dev` extra. `uv.lock` fixes the full
resolution. `make bootstrap` creates a missing `.env` from `.env.example`, append-syncs newly
declared variables without replacing operator values, installs the locked environment, and runs
the package identity check followed by readiness. Direct uv investigations use
`scripts/shared/common.sh` so `DATA_DIR`, caches, and adaptive link mode have one implementation.
Its functions use the `arxiv_int_` namespace; direct uv investigations begin with
`arxiv_int_load_env`.

## Quality gates

The Makefile exposes individual checks and two composed workflows:

- `make ci` runs formatting, linting, typing, Radon and cognitive complexity, shell parsing and
  ShellCheck, documentation links, spec-plan integrity, and deterministic tests.
- `make quality` adds branch coverage, Markdown lint, and source/wheel builds.

GitHub Actions runs `make ci-github`, an explicit alias of the same required gate, on Python 3.12
and 3.13 after `uv sync --locked --extra dev`.

Tests under `tests/quality/` exercise failure cases for the documentation checks rather than only
asserting the repository passes. `make quality-report` reports source and shell files over the
250-line soft limit. Configuration tests exercise missing-template copying, append-only declaration
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
