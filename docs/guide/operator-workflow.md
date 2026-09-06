# Operator Workflow and Atomic Commands

The short workflow in [README](../../README.md#quick-start) is the target interface.
`make setup` is available. `make pipeline` and the pipeline commands below are
**planned, unavailable now**. [Current implementation](../impl/current.md) records available
capabilities; the
[operator specification](../design/spec.md#retryable-setup-and-default-pipeline-command) defines
defaults and acceptance. This guide provides the explicit command chain for diagnosis and development.

## Host prerequisites and checkout

Install Git, Make, Bash, Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/),
Docker Engine with Compose, and the selected inference runtime. The eventual complete pipeline
needs the evaluated NVIDIA driver/CUDA host; vLLM also needs NVIDIA container support. Setup reports
missing host prerequisites but does not install OS packages, modify systemd or change permissions.

```bash
git clone https://github.com/volod/arxiv-int.git
cd arxiv-int
uv --version
python3 --version
docker compose version
docker info
nvidia-smi
```

Skip cloning for an existing checkout. Run commands from that checkout. For host Ollama, follow its
[Linux installation instructions](https://docs.ollama.com/linux) and start/check the service with
the host service manager. Downloads occur during setup; pipeline processing stays local.

## Manual setup -- diagnostic expansion

Run each step separately and inspect its result before continuing. `make setup` calls these same
handlers in order. A successful infrastructure audit does not mean the archive pipeline exists.

1. Create `.env` only when absent, then edit it:

   ```bash
   test -e .env || cp .env.example .env
   ```

   Set readable `ARCHIVE_DIR`, writable `RESULTS_DIR`, PostgreSQL-compatible `PGDATA_DIR`, private
   `POSTGRES_PASSWORD`, `INFERENCE_BACKEND` and explicit model identity. Use the
   [storage and readiness guide](setup.md) for root boundaries and backend settings. Edit `.env`,
   not the generated `.venv`. Never overwrite existing configuration with the template.

2. Prepare the locked contributor environment:

   ```bash
   make bootstrap
   ```

   Bootstrap checks package identity and audits readiness after syncing. A missing model or stopped
   service can fail its final audit even when dependency installation succeeded. Inspect the result;
   fix dependency/configuration errors first, then use the following commands to prepare services.

3. Load configuration before the current direct uv/model commands:

   ```bash
   source scripts/shared/common.sh
   arxiv_int_load_env
   uv sync --locked --extra dev --extra contracts --extra lake --extra store \
     --extra inference --extra graph --extra data-quality
   make features
   ```

   Use a fresh shell and repeat configuration loading after editing `.env`, since exported values
   take precedence. Direct installed commands below use `.venv/bin/`; activation is unnecessary.
   Reserved extras do not install unimplemented stages. Existing syncing Make targets retain their
   consolidated development extras; `make setup` preserves the selected runtime extra union.

4. For the selected host Ollama backend, acquire the configured model:

   ```bash
   ollama pull "${GENERATION_MODEL:?Set GENERATION_MODEL in .env}"
   ollama list
   ```

   Ollama uses its host service storage; `MODEL_CACHE_DIR` does not relocate that service. Model
   presence is not a memory-fit or quality result. For vLLM, use the configured model/revision and
   include `vllm` in the service profile for each current service/readiness invocation.

5. Build the pinned database image, validate roots/Compose, and start the selected services:

   ```bash
   make postgres-image
   make services-config
   make services-up
   make services-status
   ```

   The current default `pipeline` service alias means `core ui observability`. For vLLM, append
   `SERVICE_PROFILES="pipeline vllm"` to each service/readiness command. `graph` and `cadvisor` are
   opt-ins. These service profiles differ from the future `investigation` pipeline profile.

6. Verify shipped assets and apply reviewed schema revisions to the intended service:

   ```bash
   make contracts-check
   make db-check
   make ontology-check
   ```

   Prefer `make setup-schema`, which binds to the configured service, refuses a conflicting
   `ARXIV_INT_MIGRATION_DATABASE_URL`, and never uses a disposable store. Direct `db-apply-schema`
   still requires an explicit matching URL; without it, that command can operate on a disposable
   database, which cannot prove the configured service has the schema. An existing unversioned
   catalog needs the separate reviewed adoption workflow (`make db-adopt`).

7. Recheck readiness and inspect interfaces:

   ```bash
   make readiness
   make logs LOG_TAIL=100
   .venv/bin/arxiv-int info
   .venv/bin/arxiv-int --help
   ```

   Inspect `$RESULTS_DIR/reports/readiness.json`. CLI states are ready `0`, blocked `1`, degraded
   `2`; Make reports failure as nonzero. Follow each finding's next action. Grafana is available at
   `http://127.0.0.1:3000` on its default port; analyst knowledge views remain planned.

## Setup atomic chain

`make setup` calls these handlers in order, sharing resolved configuration and attempt
context. Each command remains usable independently. Stop at a failed phase, correct its reported
cause, and retry `make setup`; an unchanged retry reuses verified work and probes readiness again.
An independent phase validates its own prerequisites and records evidence for later reconciliation.

| Order | Atomic command | Responsibility |
| --- | --- | --- |
| 1 | `make setup-config` | Create/append `.env`, validate edits and host prerequisites before `.venv` or product writes; stop for required edits. |
| 2 | `make setup-env` | Sync the locked union of selected extras once; offline sync from cache with `SETUP_DOWNLOADS=0`. |
| 3 | `make package-check` | Verify the installed package identity. |
| 4 | `make services-config` | Validate/prepare safe roots and Compose configuration. |
| 5 | `make postgres-image` | Reuse or build the pinned database image; offline mode refuses a cache miss. |
| 6 | `make services-pull` | Acquire/cache-check the other selected pinned service images, preserving the locally built database image. |
| 7 | `make models-pull` | Acquire/cache-check the selected backend's configured model assets. Cached tags are not a memory-fit or quality result. |
| 8 | `make services-up` | Start/wait for selected containers; offline mode never implicitly pulls. |
| 9 | `make setup-wait` | Bounded service transport/model health checks; schema initialization follows. |
| 10 | `make contracts-check`, `make db-check`, `make ontology-check` | Shipped asset validators, invoked without repeating dependency sync. |
| 11 | `make setup-schema` | Bind to the configured service, apply eligible Alembic revisions and inspect its catalog; no disposable fallback or automatic adoption. |
| 12 | `make readiness` | Final audit with shared profile requirements. Missing pipeline providers stay unavailable. |

Infrastructure health and pipeline implementation availability remain separate. A required missing
provider cannot become a successful readiness result. Safe reports go to
`$RESULTS_DIR/reports/{setup,readiness}.json`; tool evidence goes to `$DATA_DIR/setup/<attempt-id>/`.
No setup command resets service data, changes source files or starts corpus processing.

## Pipeline atomic chain -- planned

The normal command is `make pipeline`. It reads `.env`, defaults to `PIPELINE_PROFILE=investigation`,
creates a run, preflights, forecasts, executes the selected DAG, validates and publishes the report.
It does not require a prior manual forecast or a later report/quality command. Default service
selection includes the configured inference backend; optional vector/AGE branches remain explicit.

For a diagnostic execution, first create the run and copy its returned id into `RUN_ID`:

```bash
make run-create
RUN_ID='replace-with-returned-run-id'
```

`run-create` records resolved roots, profile and secret-free configuration evidence. All following
commands use that same context. Run each command separately, inspect its status, and stop on failure.
This is one valid linear order of the baseline registry, not a second executable DAG definition:

```bash
make stage STAGE=preflight RUN_ID="$RUN_ID"
make forecast RUN_ID="$RUN_ID"
make stage STAGE=inventory RUN_ID="$RUN_ID"
make stage STAGE=extract RUN_ID="$RUN_ID"
make stage STAGE=normalize RUN_ID="$RUN_ID"
make stage STAGE=dedupe RUN_ID="$RUN_ID"
make stage STAGE=chunk RUN_ID="$RUN_ID"
make stage STAGE=classify RUN_ID="$RUN_ID"
make stage STAGE=load-lexical RUN_ID="$RUN_ID"
make stage STAGE=nlp RUN_ID="$RUN_ID"
make stage STAGE=topics RUN_ID="$RUN_ID"
make stage STAGE=entities RUN_ID="$RUN_ID"
make stage STAGE=ontology RUN_ID="$RUN_ID"
make stage STAGE=facts RUN_ID="$RUN_ID"
make stage STAGE=validate-facts RUN_ID="$RUN_ID"
make stage STAGE=domain-artifacts RUN_ID="$RUN_ID"
make stage STAGE=catalogs RUN_ID="$RUN_ID"
make stage STAGE=anomalies RUN_ID="$RUN_ID"
make stage STAGE=evaluate RUN_ID="$RUN_ID"
make stage STAGE=report RUN_ID="$RUN_ID"
make run-finalize RUN_ID="$RUN_ID"
```

Use the same registered handlers for aggregate and atomic calls, with the same dependency, lease,
forecast, source-scope and quality checks. Relational transformations call the shared dbt runner;
local batches use Polars/PyArrow and shared Pandera checks. A failed or unexecuted required validator
stops publication. `report` renders the staged report; `run-finalize` verifies manifests and switches
the complete knowledge-base generation. Archive organization never joins this chain.

Optional selected stages such as `embed`, `load-vector` and `graph` enter the registry's dependency
closure before evaluation/reporting. Disabled branches record `not-selected`. Missing required
stages fail explicitly. An explicit stage command cannot bypass stale inputs or forecast refusal.
Configuration changes require a new run or the declared invalidation/resume policy.

The returned run id, `$RUNS_DIR/<run-id>/knowledge-base.json` and report entry path identify the
result. Product artifacts use configured operator roots, never developer `DATA_DIR`. Compare
aggregate and atomic results by logical ids, checksums, lineage, quality and completion state;
run ids and timestamps may differ. A partial result must not replace the last complete generation.

## Inspect, recover and analyze -- planned

These optional commands inspect or recover the result; they are not extra completion steps.
Use the returned run id and replace query/document placeholders with actual values.

| Command or action | Purpose |
| --- | --- |
| `arxiv-int run status RUN_ID` | Inspect per-stage progress and blockers. |
| `arxiv-int run resume RUN_ID` | Resume the recorded generation after correcting an interruption. |
| `arxiv-int run artifacts RUN_ID`, `arxiv-int inspect RUN_ID` | Inspect manifest, artifact states, coverage, provenance and errors. |
| Open the returned `reports/index.html`; `arxiv-int report build RUN_ID` | Read the entry report or explicitly rebuild its rendering. |
| `arxiv-int catalog company --run RUN_ID`, `arxiv-int catalog product --run RUN_ID`, `arxiv-int catalog person --run RUN_ID` | Inspect roles, aliases, identities and evidence in the three catalogs. |
| Follow financial-party, transaction, supply-chain and BOM links | Trace quantities, relations and gaps to source anchors. |
| `arxiv-int anomalies list --run RUN_ID` | Review detector, baseline, severity and supporting/contradicting evidence. |
| `arxiv-int search lexical "QUERY"`, `arxiv-int archive locate DOCUMENT_ID` | Find source-anchored hits; verify the result's generation. |
| `arxiv-int pipeline update --archive-dir PATH` | Reconcile a changed archive into a new generation and inspect its report. |

Use `.venv/bin/arxiv-int` when the executable is not on the shell's path. After the session, the
available `make services-down` stops project containers and preserves their data. Host Ollama is
managed separately. See [README's organization utility](../../README.md#3-organize-an-archive----separate-planned-utility)
for the independent, reviewed placement workflow.
