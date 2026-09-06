# arxiv-int

`arxiv-int` is a local-first knowledge discovery platform for multi-terabyte, mostly
Russian-language document archives. It is designed to inventory an immutable archive, extract
contents, topics, entities and relations, and produce searchable knowledge, catalogs, graphs,
anomaly findings and evidence-bearing reports on one CUDA host.

Configuration, readiness checks, local service management, typed foundation primitives, and
quality gates exist today. The archive-to-knowledge pipeline is **not runnable yet**. Its stages
and analyst commands remain in the [forward plan](docs/impl/plan.md). See
[current implementation](docs/impl/current.md) for available behavior and the
[specification](docs/design/spec.md) and [architecture](docs/design/architecture.md) for the target.

## Quick start

### 1. Environment and services -- available now

Use a Linux host with a CUDA-capable NVIDIA GPU for the eventual complete pipeline. Run the rows
in order, in the same Bash session; run each command in a cell separately. Installation and model
downloads need network access during setup. Pipeline processing is designed to stay local afterward.

| Step | Command or action | Check or result |
| --- | --- | --- |
| 1. Install prerequisites | Install Git, Make, Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Docker Engine with Compose, and the matching NVIDIA driver. Check `uv --version`, `python3 --version`, `docker compose version`, `docker info`, `nvidia-smi`. | Docker is usable by the invoking user; the GPU is visible. vLLM additionally needs NVIDIA container support. |
| 2. Get the repository | `git clone https://github.com/volod/arxiv-int.git` then `cd arxiv-int` | Skip cloning for an existing checkout. |
| 3. Configure roots | Copy `.env.example` to `.env` only if `.env` does not exist; edit `.env`. | Set readable `ARCHIVE_DIR`, writable `RESULTS_DIR`, PostgreSQL-compatible `PGDATA_DIR`, and private `POSTGRES_PASSWORD`. Keep product outputs outside the checkout and source archives; separate database/service data from source/proof roots. See [storage setup](docs/guide/setup.md). |
| 4. Select inference | Install the host service using the [Ollama Linux instructions](https://docs.ollama.com/linux); run `sudo systemctl start ollama` and `systemctl status ollama`. Set `INFERENCE_BACKEND=ollama` and an explicit `GENERATION_MODEL` in `.env`. | Choose a model that fits the host. The configured default is not evidence of memory fit or extraction quality. |
| 5. Bootstrap | `make bootstrap` | Syncs the locked development environment, preserves `.env` values, checks package identity, and audits readiness. Follow missing-model/service findings' `next` actions. A blocked audit fails bootstrap; degraded is allowed here. |
| 6. Prepare the shell | `source .venv/bin/activate` then `source scripts/shared/common.sh` then `arxiv_int_load_env` | Makes `arxiv-int` available and loads configured roots/cache settings before direct `uv` commands. After editing `.env`, use a fresh terminal session and repeat this step from the checkout. |
| 7. Install available stacks | `uv sync --locked --extra dev --extra contracts --extra lake --extra store --extra inference --extra graph --extra data-quality` then `make features` | Installs populated extras from the lockfile. Several stage extras remain reserved; this does not install a finished pipeline. Use `make features STAGE=extract` as stages arrive. |
| 8. Fetch the model | `ollama pull "${GENERATION_MODEL:?Set GENERATION_MODEL in .env}"` then `ollama list` | Downloads into the host Ollama service's configured storage. The Compose model-cache root does not relocate that host service. |
| 9. Start services | `make services-config` then `make services-up` then `make services-status` | Validates/prepares the layout and starts the default service set. This is service setup, not a pipeline run. |
| 10. Audit readiness | `make readiness`; inspect logs with `make logs LOG_TAIL=100` when needed. | Read `$RESULTS_DIR/reports/readiness.json`; fix blocked findings and evaluate degraded ones. Exit codes: ready `0`, blocked `1`, degraded `2`. Service/model presence does not prove pipeline acceptance. |
| 11. Inspect interfaces | `arxiv-int info`, `arxiv-int features`, `arxiv-int --help`; open `http://127.0.0.1:3000` for Grafana on its default port. | Confirms the installed command and service UI. Product knowledge views and analyst dashboards remain planned. |

The service alias `pipeline` means `core ui observability`, separately from the planned
`investigation` run profile. The optional vLLM backend needs `INFERENCE_BACKEND=vllm`, a matching
model/revision, and `make services-up SERVICE_PROFILES="pipeline vllm"`; use the same profile value
for readiness and status. See the [setup guide](docs/guide/setup.md) for overrides. The `graph` and
`cadvisor` profiles are opt-ins; project-owned AGE/viewer integration remains forward work.

### 2. Archive to analyst results -- planned, unavailable now

This is the complete target sequence. Run it only after the corresponding capabilities ship.
Replace `RUN_ID`, `DOCUMENT_ID`, and `QUERY` with real values from the run or inspection.
Runtime outputs go under configured `RESULTS_DIR`/`RUNS_DIR`, never the developer `DATA_DIR`.

| Step | Target command or action | Expected result to inspect |
| --- | --- | --- |
| 1. Forecast | `arxiv-int pipeline forecast --archive-dir "$ARCHIVE_DIR"` | Scope, space/RAM/VRAM budget, model fit, work estimate and blockers. Review limits before starting a large run. |
| 2. Inspect a stage when developing or diagnosing | `arxiv-int stage inventory --archive-dir "$ARCHIVE_DIR" --results-dir "$RESULTS_DIR"` then `arxiv-int inspect RUN_ID` | Early inventory and errors. Optional for a complete run, which schedules its own stages. |
| 3. Run the pipeline | `arxiv-int pipeline run --archive-dir "$ARCHIVE_DIR" --results-dir "$RESULTS_DIR" --profile investigation` | Inventory, extraction, normalization, lexical retrieval, classification, NLP/identity, facts, domain artifacts, topics, catalogs, anomalies and reports. Record the returned run id. |
| 4. Monitor or recover | `arxiv-int run status RUN_ID`; after an interruption, `arxiv-int run resume RUN_ID` | Per-stage progress and checkpoints for that generation. Partial output must not appear complete. |
| 5. Verify outputs | `arxiv-int run artifacts RUN_ID` then `arxiv-int inspect RUN_ID` | Open the returned `knowledge-base.json` beneath the run root; check required artifact states, coverage, errors, provenance and generation consistency. |
| 6. Start analysis | Open `reports/index.html` beneath that run's artifact root; `arxiv-int report build RUN_ID` requests report generation. | Coverage, supported findings, topics/content overviews, evidence links and areas needing review. Start here before opening large graphs. |
| 7. Inspect entity lists | `arxiv-int catalog company --run RUN_ID`, `arxiv-int catalog product --run RUN_ID`, `arxiv-int catalog person --run RUN_ID` | Three catalogs with roles, aliases, unresolved identities, relations and source evidence. |
| 8. Investigate relations | Follow financial-party, transaction, supply-chain and BOM links from the report; open bounded graph views and exports. | Trace company/person roles through documents and transactions; inspect product revisions, components, quantities/units and gaps. A supply edge is not automatically a BOM component. |
| 9. Triage anomalies | `arxiv-int anomalies list --run RUN_ID`; open a finding's report link. | Review detector, cohort/baseline, severity and supporting/contradicting evidence. An empty, well-supported result is valid. |
| 10. Deep dive | `arxiv-int search lexical "QUERY"` then `arxiv-int archive locate DOCUMENT_ID` | Hits with source/page/table anchors and read-only source lookup. Check the search generation against the report; semantic/hybrid search is a separately accepted option. |
| 11. Refresh the archive | `arxiv-int pipeline update --archive-dir "$ARCHIVE_DIR"` | A new reconciled generation; inspect its status, manifest and report again. Retain the prior run id for comparison. |

### 3. Organize an archive -- separate planned utility

Organization consumes accepted classification artifacts and never runs automatically after analysis.
Replace `CLASSIFICATION_PATH`, `SILO_ID`, `TARGET_DIR`, and `PLAN_PATH` with reviewed values.

| Step | Target command | Result |
| --- | --- | --- |
| 1. Preview copies | `arxiv-int archive reorganize --classification CLASSIFICATION_PATH --silo SILO_ID --mode copy --target TARGET_DIR` | Dry-run plan with hierarchical directory/file names, unresolved cases, collisions and capacity checks; source files remain intact. |
| 2. Or preview in-place placement | `arxiv-int archive reorganize --classification CLASSIFICATION_PATH --silo SILO_ID --mode move` | Alternative plan for moving files within the selected silo; review the proposed path changes. |
| 3. Apply the authorized plan | `arxiv-int archive reorganize --apply --plan PLAN_PATH` | Journaled placement with source-location updates; inspect the journal and sample resulting paths. Resume/rollback use the recorded plan id and documented preconditions. |

After the session, the **available** `make services-down` stops containers and preserves service
data. It does not stop host Ollama; use the host service manager when that is desired.

## Available commands

```text
arxiv-int info
arxiv-int features [--stage STAGE]
arxiv-int config show --redact
arxiv-int readiness [--profiles PROFILES] [--timeout SECONDS]
arxiv-int services --help
arxiv-int contracts --help
arxiv-int data-quality check DATASET --run-id RUN_ID --input PATH
```

`info` is a packaging and executable-path smoke test. `features` lists optional dependency groups,
install status and commands, distribution licences, and expected system dependencies.
`data-quality check` validates one contract dataset and writes secret-free evidence; a missing or
unexecuted required check cannot look publishable. Domain commands arrive as their specified
capabilities are implemented.

## Development

Start with [AGENTS.md](AGENTS.md). Load its linked guidance only when needed for the selected task.
Preserve full task scope and evidence in [task records](docs/impl/records/README.md).

## License

MIT. See [LICENSE](LICENSE).
