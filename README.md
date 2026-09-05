# arxiv-int

`arxiv-int` is a local-first knowledge discovery platform for multi-terabyte, mostly
Russian-language document archives. It is designed to inventory and normalize an immutable archive,
build reproducible lexical and selected semantic indexes, discover topics, extract and resolve
entities and facts, project a knowledge graph, and support evidence-bearing local analysis without
document or prompt egress.

The repository currently provides the personalized Python package, `arxiv-int info` identity
command, locked development environment, executable quality gates, and specification-to-plan
governance. Corpus, storage, retrieval, NLP, graph, and visualization capabilities remain staged in
the [forward implementation plan](docs/impl/plan.md); the
[current implementation index](docs/impl/current.md) records only behavior that exists now.

## Quick start

### 1. Configure the environment and start services

Install Git, Make, [uv](https://docs.astral.sh/uv/), and Docker with the Compose plugin. Then create
the local configuration:

```bash
git clone https://github.com/volod/arxiv-int.git
cd arxiv-int
cp .env.example .env
```

Edit `.env` to set `ARCHIVE_DIR`, `RESULTS_DIR`, `PGDATA_DIR`, and `POSTGRES_PASSWORD`. The
[setup guide](docs/guide/setup.md) explains the required storage classes and optional model values.

```bash
make bootstrap
make services-up
make readiness
```

The readiness audit persists `$RESULTS_DIR/reports/readiness.json` and exits `0` when ready, `1` when
blocked, or `2` when degraded. Interactive output highlights degraded findings in yellow and blocked
findings in red. `make bootstrap` also creates a missing `.env`, appends new declarations from
`.env.example` without replacing operator values, verifies the installed package identity, and
finishes with this readiness audit. Follow each non-ready finding's `next` action, then rerun it.

The default `pipeline` alias checks and starts `core`, `ui`, and `observability`; readiness uses a
running host Ollama service with `qwen3.8:27b` as the default generation model. Override
`GENERATION_MODEL` in `.env` when needed. Select `vllm` explicitly as an alternate, add `graph` or
`cadvisor` explicitly when needed. Use `make services-down` to stop containers while keeping
database and service-state data, or `make services-reset APPLY=1` to stop and erase those service
data roots.

### 2. Run the pipeline

Pipeline commands become available through the normal operator interface in the same change that
implements each stage. The following commands are **currently unimplemented**:

```bash
# Currently unimplemented: run and inspect stages one at a time for early feedback.
make stage STAGE=inventory
arxiv-int inspect RUN_ID

# Currently unimplemented: run the complete registered pipeline.
make pipeline
```

There are no development-only stage commands, aliases, or output trees. Each standard stage command
runs against `ARCHIVE_DIR`, writes normal artifacts beneath `RESULTS_DIR` and `RUNS_DIR`, and is run
against configured data immediately after implementation so problems surface before the complete
pipeline is available.

## Available commands

```bash
arxiv-int info
arxiv-int features [--stage STAGE]
arxiv-int readiness [--profiles PROFILES] [--timeout SECONDS]
```

`info` reports the distribution name, installed version, and import package. It is a packaging and
executable-path smoke test. `features` lists the optional dependency groups, their install status
and install command, the licence of every declared distribution, and the system dependencies they
expect; `--stage` narrows the list to one pipeline stage. Domain pipeline commands will be added
only as their specified capabilities are implemented.

## License

MIT. See [LICENSE](LICENSE).
