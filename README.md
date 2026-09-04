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

Requirements: Git, Make, and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/volod/arxiv-int.git
cd arxiv-int
make bootstrap
make doctor
make run
make ci
```

`make bootstrap` creates `.venv` from the committed lockfile. `make doctor` checks the local tools,
repository markers, package import, and distribution identity. `make run` executes `arxiv-int info`.

## Available commands

```bash
arxiv-int info
arxiv-int features [--stage STAGE]
```

`info` reports the distribution name, installed version, and import package. It is a packaging and
executable-path smoke test. `features` lists the optional dependency groups, their install status
and install command, the licence of every declared distribution, and the system dependencies they
expect; `--stage` narrows the list to one pipeline stage. Domain pipeline commands will be added
only as their specified capabilities are implemented.

## Daily commands

| Command | Purpose |
| --- | --- |
| `make help` | List supported workflows |
| `make bootstrap` | Create or update the locked development environment |
| `make doctor` | Check tools, repository markers, and installed package identity |
| `make run` | Run `arxiv-int info` |
| `make features` | List optional feature groups, licences, and install commands |
| `make test` | Run the deterministic unit test suite |
| `make coverage` | Run tests with the coverage gate |
| `make format` | Apply Ruff formatting |
| `make ci` | Run required local and CI checks |
| `make quality` | Run CI checks, coverage, Markdown lint, and package build |
| `make plan-status` | Count tasks and show the next agent and human work |
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

The specification is living. New product behavior is specified and evaluated before it enters the
plan or production package. When work becomes available, its implementation detail moves out of the
plan and into the narrowest current-state page.

## Repository layout

```text
src/arxiv_int/             production package and repository quality checks
src/arxiv_int/features/    optional dependency groups, licences, and install guards
src/arxiv_int/interfaces/  typed seams for extractors, embedders, providers, stores, stages
tests/                     mirrored unit and governance tests
docs/design/               product specification
docs/impl/plan.md          forward-only work
docs/impl/current/         available implementation
docs/guide/                contributor workflows
scripts/shared/            shared shell environment helpers
.github/workflows/         required CI
```

Runtime output belongs under `$DATA_DIR/<method>/<run-id>/`, which defaults to `.data/` and is
ignored by Git.

## License

MIT. See [LICENSE](LICENSE).
