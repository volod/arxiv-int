# Portable Runtime

Runtime configuration and path behavior lives cohesively under `src/arxiv_int/runtime/`. The
top-level package contains only its initializer, CLI entry point, and metadata module; runtime
implementation details do not expand that namespace.

## Layered configuration

`arxiv_int.runtime.load_runtime_config()` resolves runtime values with CLI, process environment,
checkout `.env`, and documented defaults in descending precedence. It discovers or accepts an
explicit project root, resolves relative paths and `${VARIABLE}` references from that checkout, and
returns a typed immutable `RuntimeConfig`. Missing operator roots identify every variable the
operator must set. Rendering is stable and masks passwords, tokens, secrets, and database URLs.
`arxiv_int.runtime.config_model` owns the immutable values, while `arxiv_int.runtime.dotenv` keeps
file parsing dependency-free.

The three required operator placements are one or more archive silos, `RESULTS_DIR`, and
`PGDATA_DIR`. `ARCHIVE_DIR` is the one-silo form with id `default`; additional or alternative silos
use `ARCHIVE_SILO_<ID>_DIR`, with underscores in the variable id rendered as hyphens. `RUNS_DIR`,
`DEV_RESULTS_DIR`, `SERVICE_STATE_DIR`, `MODEL_CACHE_DIR`, and `TMP_DIR` derive from
`RESULTS_DIR` unless individually overridden. Optional `PG_WAL_DIR` and
`PG_TABLESPACE_<NAME>_DIR` roots remain unset by default. `DEV_ARCHIVE_DIR` defaults to
`PROOF_ARCHIVE_DIR`, while `DATA_DIR` remains checkout-relative developer-tooling state and is not a
runtime output root.

`scripts/shared/common.sh` loads the same checkout `.env` without replacing variables already in
the process environment. This preserves Make and shell overrides while retaining the adaptive uv
link mode and repository-local tool-cache behavior.

## Path safety and storage evidence

`arxiv_int.runtime.validate_runtime_paths()` operates on resolved real paths, accumulates all
findings, and does not create directories. It refuses filesystem-root targets; source, results,
database, WAL, and tablespace overlaps; output inside or around the checkout; symlink-resolved
escapes; unreadable sources; unwritable or full destinations; and a writable
`PROOF_ARCHIVE_DIR`. Database roots on a filesystem without PostgreSQL-compatible ownership and
exclusive-use semantics are blocked. Rotational database, scratch, and model placements and
non-owning service-state placements are degraded warnings that name the variable to move.

`arxiv_int.runtime.inspect_filesystem()` records the resolved path, filesystem type, device id,
rotational flag when the operating system exposes it, accessible free bytes, ownership capability,
and read-only mount state. This evidence is retained with every configured placement and is exposed
to later doctor, forecast, and run-manifest work. `arxiv_int.runtime.path_model` owns the typed
association between each variable, resolved path, and storage class.

After a report has no blocking findings, `create_results_layout()` creates the fixed
`normalized/`, `quarantine/`, `proofs/`, and `exports/` trees, the five resolved derived roots, and
the configured PostgreSQL, WAL, and tablespace directories. It creates no corpus artifact and
starts no process or container.

## Operator interface

`arxiv-int config show --redact`, wrapped by `make config`, loads and validates configuration,
creates the empty runtime layout, and prints redacted resolved values plus storage class,
filesystem, device, rotational, and free-space evidence. CLI root options override both the process
environment and `.env`. The command exits non-zero on missing or unsafe configuration and never
logs configured secrets.

## Tests and verification

Tests under `tests/config/` cover layer precedence, shell precedence, checkout and current-directory
independence, paths containing spaces, named silos, derived overrides, variable references,
redaction, missing values, root and symlink hazards, all root-overlap boundaries, permissions,
free space, proof read-only enforcement, distinct device evidence, results layout creation, and
storage-class refusal versus warning fixtures. CLI coverage proves its explicit options and
redacted output. The required format, lint, typing, complexity, shell, documentation, plan-integrity,
and deterministic test gates pass.
