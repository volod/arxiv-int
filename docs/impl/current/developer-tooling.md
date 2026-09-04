# Developer Tooling

## Environment

`pyproject.toml` declares Python 3.12+ package metadata and a `dev` extra. `uv.lock` fixes the full
resolution. `make bootstrap` installs the locked environment; direct uv investigations use
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
250-line soft limit.

## Artifact paths

`.env.example` declares `DATA_DIR=.data`. Relative values resolve against the project root. Runtime
results use `$DATA_DIR/<method>/<run-id>/`; Ruff, mypy, pytest, and complexipy caches stay below the
same root. `.gitignore` excludes runtime artifacts, local environments, secrets, caches, and root
build outputs without hiding same-named source subpackages.

`.env.example` also documents the operator roots the pipeline capabilities will resolve --
`ARCHIVE_DIR`, `RESULTS_DIR`, `PGDATA_DIR`, their derived defaults, and the optional second database
device -- as commented placeholders annotated with the storage class each one needs. Only `DATA_DIR`
and `LOG_LEVEL` carry values, so no machine-specific path is committed. The resolution and
validation behavior behind those variables is specified in
[Configuration and multi-SSD paths](../../design/spec.md#configuration-and-multi-ssd-paths) and is
not implemented yet; today `scripts/shared/common.sh` exports only `DATA_DIR` and the tool caches
derived from it.
