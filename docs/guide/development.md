# Development Guide

## Setup

Follow [Workstation setup and readiness](setup.md) for system prerequisites, `.env` roots, storage
requirements, and readiness remediation. The normal operator setup is `make setup`. Contributors
who only need the locked environment and a readiness audit can use:

```bash
make bootstrap
make readiness
```

The lockfile is committed. After changing dependencies in `pyproject.toml`, run `make lock` and
include the resulting `uv.lock` change.

## Feature groups

Optional stacks are installed by feature-group name:

```bash
source scripts/shared/common.sh
arxiv_int_load_env
uv sync --locked --extra dev --extra lake
make features
make features STAGE=extract
```

`make features` lists every group with its status, the pipeline stages that activate it, its
install command, the licence and purpose of each declared distribution, and the system dependencies
it expects. Populated groups are `contracts`, `data-quality`, `graph`, `inference`, `lake`,
`store`, and `transform`. The `embeddings`, `evaluation`, `extraction`, `gpu`, `nlp`, and `ui`
groups are declared and reserved for the capability that will choose their components.

System dependencies are not installed by an extra. The `extraction` group expects a reachable
Apache Tika server plus `tesseract-ocr` and `ocrmypdf` for the scanned-PDF lane, `store` expects a
reachable PostgreSQL service, `transform` expects that same service with the `derived` schema and
dbt role, `inference` expects an Ollama system service or the optional vLLM profile, `gpu` expects
a matching NVIDIA driver and CUDA runtime, and `ui` expects Docker.

Adding a dependency means adding it to the group that owns it in
`src/arxiv_int/features/catalog.py` and to the matching extra in `pyproject.toml`, then running
`make lock`. Never add one to the core `dependencies` list, and never import an optional module
directly: call `arxiv_int.features.require_module()` so a missing stack reports its install command
instead of a traceback.

## Quality workflows

`make ci` is the required fast gate and is the command GitHub Actions runs on Python 3.12 and 3.13.
It checks formatting, Ruff rules, mypy, complexity, shell scripts, documentation links, specification
and plan integrity, and deterministic tests. It does not start Docker. Tests marked `heavy`
(Compose rendering against the daemon, disposable Postgres apply, live store/dbt/projection/image
suites) run only with `make test-heavy`. Evolution policy in CI is `make contracts-evolution`,
which passes `--skip-live-sql`; `make contracts-evolution-live` applies baseline SQL.

`make quality` adds a diagnostic coverage report, Markdown style, and source/wheel builds. Run it
before release or after changing project infrastructure. A numeric coverage percentage is not an
acceptance gate; tests must cover integrity, correctness, and business logic and must not freeze
current implementation or historical policy. `make quality-report` reports files over the 250-line
soft limit without turning cohesion into a numeric failure.

## Direct uv commands

Make targets are the stable workflow. For one-off dependency debugging:

```bash
source scripts/shared/common.sh
arxiv_int_load_env
uv <command>
```

This resolves `DATA_DIR`, moves supported tool caches with it, and avoids cross-filesystem link
warnings.

## Runtime artifacts

Developer-tool output belongs under `$DATA_DIR/<method>/<run-id>/`. Use a stable method name and a
unique run id. Product runtime output belongs under the operator roots configured in `.env`; the
readiness audit writes `$RESULTS_DIR/reports/readiness.json`. Keep fixtures under `tests/` only when
they are small, deterministic, safe to publish, and required for CI.

## Daily commands

| Command | Purpose |
| --- | --- |
| `make help` | List supported workflows |
| `make bootstrap` | Append-sync `.env`, update the locked environment, and audit readiness |
| `make setup` | Retryable environment, model, service and schema preparation |
| `make readiness` | Emit console and JSON workstation readiness reports |
| `make services-up` | Start and health-check the default `pipeline` service set |
| `make postgres-image` | Build the pinned ParadeDB + AGE database image (`NO_CACHE=1` for clean cache) |
| `make postgres-image-probe` | Run disposable extension probes (`WRITE_GATE=1` records the AGE gate) |
| `make services-down` | Stop containers; preserve bind-mounted service data |
| `make services-reset` | Stop containers; list erasable roots (add `APPLY=1` to erase) |
| `make package-check` | Verify the installed package identity; bootstrap runs it automatically |
| `make features` | List optional feature groups, licences, and install commands |
| `make contracts-gen` | Generate committed physical schemas, quality catalogs, and dbt YAML |
| `make db-revision` | Write a candidate Alembic revision from contract metadata (`MESSAGE=...`) |
| `make db-check` | Revision graph, checksums, and pending contract changes (part of `make ci`) |
| `make db-status` | Report the applied revision of `ARXIV_INT_MIGRATION_DATABASE_URL` |
| `make db-upgrade` | Apply owned Alembic revisions to that URL (`REVISION=head`) |
| `make db-apply-schema` | Apply owned revisions on the URL or a disposable PGDATA; evidence under `$DATA_DIR/migrations` |
| `make db-adopt` | Stamp a live catalog after equivalence, or report why stamping is refused |
| `make data-quality` | Validate `DATASET` contents for `RUN_ID` (`INPUT=...` required) |
| `make eval` | Score frozen evaluation fixtures into `$RUNS_DIR/<run-id>/evaluation` (`RUN_ID=`) |
| `make proof` | Publish a capability proof (`CAPABILITY=`, `RUN_ID=`) |
| `make proof-export` | Write identity-obfuscated Git-bound copies (`SOURCE_BUNDLE=`, `MAP=`, `RUN_ID=`) |
| `make identity-policy-check` | Fail when the committed proof-identity policy drifts |
| `make evaluation-fixtures-check` | Fail when frozen fixtures or the proof registry drift |
| `make transform-parse` | Parse the dbt project for `RUN_ID` without materializing relations |
| `make transform-compile` | Compile selected dbt models for `RUN_ID` |
| `make transform-build` | Build and test an isolated derived generation for `RUN_ID` |
| `make transform-test` | Run dbt data tests for `RUN_ID` without replacing the active generation |
| `make projections-build` | Build search/vector/graph projections for `RUN_ID` (`KIND=`, `APPLY=1` activates) |
| `make projections-status` | Show active projection pointers |
| `make projections-cleanup` | Plan retired/failed projection drops (`APPLY=1` executes) |
| `make test` | Run the deterministic unit test suite (`-m "not heavy"`) |
| `make test-heavy` | Run Docker and other host-service tests marked `heavy` |
| `make coverage` | Run unit tests and report coverage (diagnostic, not a percentage floor) |
| `make format` | Apply Ruff formatting |
| `make ci` | Run required local and CI checks |
| `make quality` | Run CI checks, coverage, Markdown lint, and package build |
| `make plan-status` | Count tasks and show lane priority; check dependencies separately |
| `make lint-spec-plan` | Check the capability registry against the plan |
| `make lint-doc-links` | Check relative Markdown files and anchors |
| `make quality-report` | Report files over the soft size limit |

Use Make targets for repeatable workflows. Before direct uv debugging, source
`scripts/shared/common.sh` and run `arxiv_int_load_env` so cache and link behavior follows `.env`.

## Documentation model

```text
docs/design/spec.md        product behavior, boundaries, and capability evaluations
          |
          v
docs/impl/plan.md          only work that remains, ordered by capability
          |
          v
docs/impl/current.md       index of behavior available now
```

Follow the [AGENTS task cycle](../../AGENTS.md#task-cycle). Current pages describe available behavior;
[task records](../impl/records/README.md) retain full scope and evidence after plan removal.
Use the [planning workflow](planning-workflow.md) when editing tasks, capabilities or checkpoints.

## Repository layout

```text
src/arxiv_int/             production package and repository quality checks
src/arxiv_int/features/    optional dependency groups, licences, and install guards
src/arxiv_int/interfaces/  typed seams for extractors, embedders, providers, stores, stages
tests/                     mirrored unit and governance tests
docs/design/               product specification
docs/impl/plan.md          forward-only work
docs/impl/current/         available implementation
docs/impl/records/         sequenced task records (`NNNN-group-task-id.md`), evidence, audits
docs/guide/                contributor workflows
scripts/shared/            shared shell environment helpers
.github/workflows/         required CI
```
