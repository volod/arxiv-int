# arxiv-int

`arxiv-int` is a local-first knowledge discovery platform for multi-terabyte, mostly
Russian-language document archives. It is designed to inventory an immutable archive, extract
contents, topics, entities and relations, and produce searchable knowledge, catalogs, graphs,
anomaly findings and evidence-bearing reports on one CUDA host.

Configuration, readiness checks, local service management, typed foundation primitives,
quality gates, a fixture DAG orchestrator, and serialized progress logs exist today. The
archive-to-knowledge pipeline is
**not complete**: most corpus stages remain in the
[forward plan](docs/impl/plan.md). See
[current implementation](docs/impl/current.md) for available behavior and the
[specification](docs/design/spec.md) and [architecture](docs/design/architecture.md) for the target.

## Quick start

### 1. Environment and services

From a checkout with the [host prerequisites](docs/guide/operator-workflow.md#host-prerequisites-and-checkout)
installed:

```bash
make setup
```

Edit `.env` when requested, then rerun `make setup` until the selected infrastructure is ready.
Setup prepares the Python environment, configured models, services and schema, reuses verified
work on retries, and reports what still needs attention. Edit `.env`; `.venv` is managed
automatically. No activation or manual exports are required. Storage requirements are in the
[setup guide](docs/guide/setup.md).

Infrastructure-ready is not pipeline-ready. Concrete corpus stages remain unimplemented.

### 2. Archive to analyst results -- orchestration only

After setup, the DAG commands allocate a unique run id and walk the selected profile. The default
investigation profile still names unimplemented stages, so `make pipeline` fails explicitly rather
than activating a complete knowledge base. `make run-finalize RUN_ID=...` seals the run's
`knowledge-base.json`; only a succeeded profile replaces `$RUNS_DIR/active-generation.json`.

```bash
make run-create
make pipeline
```

`make run-create` prints a `run-<hex>` id. Use that id with `make forecast`, `make stage`,
`make run-status`, `make resume`, and `make run-finalize`; do not pass Make's developer
`RUN_ID=local` fallback.
Outputs use configured operator roots. Resource limits and archive-scope authorization still
apply.

See the [step-by-step operator workflow](docs/guide/operator-workflow.md) for the atomic command
chain, what is available now, and the remaining planned stages. The aggregate targets reuse those
same command handlers and checks.

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
arxiv-int setup [--phase PHASE]
arxiv-int readiness [--profiles PROFILES] [--timeout SECONDS]
arxiv-int services --help
arxiv-int contracts --help
arxiv-int data-quality check DATASET --run-id RUN_ID --input PATH
arxiv-int transform parse|compile|build|test --run-id RUN_ID
arxiv-int store projections-build|status|cleanup --run-id RUN_ID
arxiv-int run create|status|resume|finalize
arxiv-int pipeline forecast|run|update|rebuild|invalidate
arxiv-int stage STAGE --run-id RUN_ID
arxiv-int artifacts prune --stale
```

`info` is a packaging and executable-path smoke test. `features` lists optional dependency groups,
install status and commands, distribution licences, and expected system dependencies.
`data-quality check` validates one contract dataset and writes secret-free evidence; a missing or
unexecuted required check cannot look publishable. `transform` parses, compiles, builds, or tests
isolated derived dbt models; a failed or unexecuted required live check cannot look like a pass.
`store projections-*` builds, switches, and cleans ParadeDB/pgvector/AGE projections without making
them canonical; a failed build cannot replace an active pointer.
`run` / `pipeline` / `stage` / `artifacts prune` freeze a unique run id and walk or maintain the
selected DAG. A default investigation run refuses unimplemented required stages. Fixture
knowledge-base publication writes `$RUNS_DIR/<run-id>/knowledge-base.json` and activates only a
complete requested profile.
Domain commands arrive as their specified capabilities are implemented.

## Development

Start with [AGENTS.md](AGENTS.md). Load its linked guidance only when needed for the selected task.
Preserve full task scope and evidence in [task records](docs/impl/records/README.md).

## License

MIT. See [LICENSE](LICENSE).
