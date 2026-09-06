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

### 1. Environment and services -- target workflow, planned

From a checkout with the [host prerequisites](docs/guide/operator-workflow.md#host-prerequisites-and-checkout)
installed:

```bash
make setup
```

Edit `.env` when requested, then rerun `make setup` until the selected infrastructure is ready.
Setup will prepare the Python environment, configured models, services and schema, reuse verified
work on retries, and report what still needs attention. Edit `.env`; `.venv` is managed automatically.
No activation or manual exports are required.

This target is **not implemented yet**. The [setup task](docs/impl/plan.md#implement-retryable-setup-command)
owns it; use the [available manual setup](docs/guide/operator-workflow.md#manual-setup-available-now)
today. Storage requirements and remediation are in the [setup guide](docs/guide/setup.md).

### 2. Archive to analyst results -- planned, unavailable now

After setup, run the full pipeline with the default `.env` settings:

```bash
make pipeline
```

The target will run preflight, resource forecast, all required stages, quality checks, evaluation
and report publication. It will return the run id, knowledge-base manifest, report entry path and
status/resume commands if interrupted. Outputs use configured operator roots; partial results
cannot appear complete. Resource limits and archive-scope authorization still apply.

See the [step-by-step operator workflow](docs/guide/operator-workflow.md) for the underlying atomic
command chain, expected results, recovery and analyst commands. The aggregate targets reuse those
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
