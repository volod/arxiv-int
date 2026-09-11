# arxiv-int

`arxiv-int` is a local-first knowledge discovery platform for multi-terabyte document archives.
It is designed to inventory an archive, extract contents, topics, entities and relations,
and produce searchable knowledge, catalogs, graphs, anomaly findings and evidence-bearing reports
on one CUDA host.

Configuration, readiness checks, local service management, typed foundation primitives,
quality gates, the run ledger and stage DAG, and serialized progress logs exist today. The corpus
foundation is shipped: an archive can be inventoried, extracted, normalized, deduplicated and
chunked into validated, source-anchored artifacts. Lexical retrieval is also shipped: those chunks
load into the canonical store and are searchable with filters, snippets, facets and citations.
The archive-to-knowledge pipeline is **not complete**: semantic retrieval, classification, NLP,
knowledge extraction and reporting remain in the [forward plan](docs/impl/plan.md). See
[current implementation](docs/impl/current.md) for available behavior and the
[specification](docs/design/spec.md) and [architecture](docs/design/architecture.md) for the
target.

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

Infrastructure-ready is not pipeline-ready. The corpus and lexical stages below are available; the
later investigation stages are not.

### 2. Archive to analyst results -- corpus and lexical stages available

After setup, the DAG commands allocate a unique run id and walk the selected profile. The chain from
an untouched archive to a searchable lexical projection runs end to end today:

```bash
make run-create
# Set RUN_ID to the run-<hex> id printed above.
make forecast RUN_ID="$RUN_ID"
make stage STAGE=preflight RUN_ID="$RUN_ID"
make stage STAGE=inventory RUN_ID="$RUN_ID"
make stage STAGE=extract RUN_ID="$RUN_ID"
make stage STAGE=normalize RUN_ID="$RUN_ID"
make stage STAGE=dedupe RUN_ID="$RUN_ID"
make stage STAGE=chunk RUN_ID="$RUN_ID"
make stage STAGE=load-lexical RUN_ID="$RUN_ID"
make search-lexical QUERY="..."
make inspect RUN_ID="$RUN_ID"
```

`preflight`, `inventory`, `extract`, `normalize`, `dedupe`, `chunk`, `load-lexical` and `evaluate`
are shipped runners. `make search-lexical QUERY=...` queries the active ParadeDB projection; see
[lexical retrieval](docs/impl/current/lexical-retrieval.md).

The default investigation profile still names unimplemented later stages, so the aggregate
`make pipeline` fails explicitly rather than activating an incomplete knowledge base.
`make run-finalize RUN_ID=...` seals the run's `knowledge-base.json`;
only a succeeded profile replaces `$RUNS_DIR/active-generation.json`.

Do not pass Make's developer `RUN_ID=local` fallback. The source archive is read without
modification; outputs use configured operator roots. Refresh `make forecast` before repeating a
completed stage, and use `make update` or a new run after source changes. Resource limits and
archive-scope authorization still apply.

See the [step-by-step operator workflow](docs/guide/operator-workflow.md) for the full command
chain, recovery commands, and the remaining planned stages. The aggregate targets reuse those same
command handlers and checks.

### 3. Organize an archive -- separate planned utility

Organization consumes accepted classification artifacts and never runs automatically after analysis.
It previews a plan first and leaves the source archive intact:

```bash
arxiv-int archive reorganize --classification CLASSIFICATION_PATH --silo SILO_ID \
  --mode copy --target TARGET_DIR
```

See [archive organization](docs/guide/archive-organization.md) for placement modes, the apply,
resume and rollback steps, and the safety boundaries. The command is **planned**; today
`arxiv-int archive` offers only `locate` and `import-ledger`.

After the session, the **available** `make services-down` stops containers and preserves service
data. It does not stop host Ollama; use the host service manager when that is desired.

## Available commands

```bash
make help
```

`make help` lists every target with its purpose, grouped by area. The
[command reference](docs/guide/commands.md) explains the CLI surface behind those targets and marks
each command available or planned.

## Development

Start with [AGENTS.md](AGENTS.md). Load its linked guidance only when needed for the selected task.
Preserve full task scope and evidence in [task records](docs/impl/records/README.md).

## License

MIT. See [LICENSE](LICENSE).
