# Project Foundation

## Project identity

The Python distribution and installed command are `arxiv-int`; the import package is `arxiv_int`.
`src/arxiv_int/metadata.py` provides the typed `ProjectInfo` value through `project_info()`. It
reports the distribution, package, and installed version, with a source-checkout fallback when
distribution metadata is unavailable.

`src/arxiv_int/cli.py` owns argument parsing. The installed `arxiv-int info` command logs the same
identity, providing an import, packaging, and executable-path smoke test without selecting a corpus,
store, or application framework.

Run it through the stable Make entrypoint:

```bash
make package-check
```

`make bootstrap` invokes this check after installing the locked environment, so a successful
bootstrap already proves the package entrypoint and identity.

The separate `arxiv-int-plan` entrypoint supports `make plan-status`. Repository quality modules
remain under `src/arxiv_int/quality/`, and shared shell functions use the `arxiv_int_` prefix.

## Feature groups

The feature catalog and domain interfaces are available with the base package. Backend stacks for
contracts, storage, extraction, NLP, embeddings, graph, inference, evaluation, and the UI are
organized as named optional groups.

`src/arxiv_int/features/catalog.py` is the single source of truth for group identity: summary,
owning capability, declared distributions with import name, SPDX licence and purpose, system
dependencies, and the `STAGE_FEATURES` map from a pipeline stage to the groups it activates.
`pyproject.toml` owns version pins for the groups that carry members, and a unit test keeps the two
in agreement in both directions.

| Group | State | Declared distributions |
| --- | --- | --- |
| `contracts` | populated | `fastavro` (MIT), `jsonschema` (MIT), `pydantic` (MIT), `pyyaml` (MIT), `sqlalchemy` (MIT), `sqlglot` (MIT) |
| `data-quality` | populated | `pandera` (MIT) |
| `graph` | populated | `pyshacl` (Apache-2.0), `rdflib` (BSD-3-Clause) |
| `inference` | populated | `httpx` (BSD-3-Clause) |
| `lake` | populated | `duckdb` (MIT), `polars` (MIT), `pyarrow` (Apache-2.0) |
| `store` | populated | `alembic` (MIT), `psycopg[binary]` (LGPL-3.0-only) |
| `transform` | populated | `dbt-core` (Apache-2.0), `dbt-postgres` (Apache-2.0) |
| `embeddings` | reserved for `semantic-retrieval` | none yet |
| `evaluation` | reserved for `evaluation-foundation` | none yet |
| `extraction` | reserved for `corpus-foundation` | none yet |
| `gpu` | reserved for `local-inference` | none yet |
| `nlp` | reserved for `russian-nlp` | none yet |
| `ui` | reserved for `discovery-visualization` | none yet |

A reserved group carries its summary, system dependencies, and owning capability but no extra in
`pyproject.toml` until the owning capability selects its implementation.

`arxiv-int features [--stage STAGE]`, wrapped by `make features [STAGE=...]`, prints every group
with its status -- `installed`, `missing`, or `reserved` -- the stages that activate it, its install
command, the licence and purpose of each declared distribution, and the system dependencies it
needs. That output is the dependency licence inventory.

`arxiv_int.features.require_module()` imports one declared optional module or raises
`MissingFeatureError` naming the module, its group, and the exact install command. Requiring a
module that no group declares raises `LookupError`, so an optional import cannot reach production
code without a catalog entry.

## Runtime primitives

`arxiv_int.pipeline.steps`, `arxiv_int.observability.logging`, and
`arxiv_int.inference.scheduling` provide monotonic step timing with
partial-result preservation, queue-serialized logging, GPU-budget placement, and guaranteed model
release. The local Ollama/vLLM request client is documented in
[Local inference](local-inference.md). The foundational configuration merge and containment helpers
have grown into the [portable runtime](portable-runtime.md).

## Contract primitives

`arxiv_int.contracts` provides an explicit-root file registry, an immutable canonical semantic
model, deterministic semantic metadata hashes, registered generator dispatch, schema
snapshot/change/version/baseline primitives, deterministic multi-format generation, and evolution
policy with reviewed baselines and Alembic Python revisions. The shipped registry, `x-arxiv-int`
bindings, loaders, generation tree, and evolution checks are documented in
[Contracts](contracts.md). Contract-governance ODCS, generation, evolution, and ontology assets are
documented there; the initial store schema, dbt generations, and rebuildable search/graph projections
are recorded in [Canonical store](canonical-store.md). The
[foundation checkpoint](../records/0027-store-review-foundation-and-store-boundaries.md) records
integrated acceptance and the remaining nonblocking follow-up.

## Evaluation and retrieval primitives

`arxiv_int.evaluation` provides normalized text and multiset extraction precision/recall/F1,
labelled linkage-pair metrics, seeded paired bootstrap intervals with exact sign tests, three-way
comparison verdicts, and atomic checksum-verified run bundles. A published bundle cannot overwrite
an existing run. Verification refuses path traversal, symlinks, nonregular entries, escaped paths,
corrupt bytes, unregistered files, and malformed manifest identities. Artifact hashing is chunked;
the claimed durability and memory bounds are recorded in
[Evaluation foundation](evaluation-foundation.md).

`arxiv_int.retrieval` provides source-span recall, MRR, character coverage, intactness, duplicate
source occurrences, and served-character cost. `InferenceProvider` and `LocalInferenceClient`
record normalized timeout, cancel, backend-error, and unsupported-architecture outcomes together
with prompt/completion token counts, latency, and successful completion throughput. See
[Local inference](local-inference.md). Probabilistic model fitting remains behind the
identity capability's Splink integration.

Output-sensitive tooling is pinned exactly: `complexipy`, `mypy`, `pymarkdownlnt`, `radon`, `ruff`,
and `shellcheck-py`. Formatting, typing, complexity, and Markdown findings therefore do not move
with a resolver update. `make bootstrap` still installs the core plus the `dev` and `contracts` extras.

## Domain interfaces

`src/arxiv_int/interfaces/` holds the typed seams between pipeline policy and the backends that
feature groups provide. They are `typing.Protocol` definitions with small frozen value types and no
optional import, so an adapter can be declared and tested before its stack is installed.

| Protocol | Seam it defines |
| --- | --- |
| `DocumentExtractor` | one extraction backend to `ExtractedDocument` text, media type, and backend metadata |
| `TextEmbedder` | vectors produced under one `EmbeddingProfile` identity |
| `InferenceProvider` | local model discovery and one bounded generation with an explicit result status |
| `ArtifactStore` | locating and publishing normalized dataset generations by `DatasetRef` |
| `CanonicalStore` | reachability and canonical schema names of the relational store |
| `StageRunner` | one restartable stage over a declared archive and results root |

Every protocol carries a `feature` attribute naming the group an implementation requires, so the
orchestrator can report a missing stack before selecting a backend rather than at import time.

## Metadata and documentation

`pyproject.toml` carries the `arxiv-int` distribution metadata, project URLs, console scripts,
package discovery, type-check path, and coverage source. `README.md`, `AGENTS.md`, the contributor
guide, current-state pages, tests, Make workflows, and `uv.lock` use the same active identity.

## Tests and verification

`tests/test_metadata.py` covers installed-version lookup and the source-checkout fallback.
`tests/test_cli.py` covers parsing, logged identity, and the feature inventory command. Tests under
`tests/quality/` exercise the quality package with isolated plan fixtures; they verify summary
selection and invalid-plan handling without pinning the live repository's task counts.
`tests/features/` covers catalog lookup, stage mapping, install-status reporting, and the missing
and undeclared import messages. `tests/interfaces/` proves fake backends satisfy each protocol.
`tests/dependencies/` keep extras and the feature catalog in agreement and require exact pins for
output-sensitive tools. Focused tests cover accumulated preflight results, partial-result
preservation, concurrent log serialization, model placement and cleanup, local inference
conformance, contract behavior,
evaluation metrics and verdicts, run bundles, and source-span retrieval. Configuration and path
coverage is documented in [Portable runtime](portable-runtime.md#tests-and-verification).

`tests/compose/test_profiles.py` renders the Compose topology once per module through the
`rendered_topology` fixture and asserts one invariant family per test: image pinning with health
and stop policy, loopback-only published ports, the vLLM GPU/model/revision pins, database-root
mount isolation, and read-only config mounts with dropped privileges. Rendering stays a
`docker compose config` call, so no service starts.

The locked bootstrap and package identity checks pass, and `make package-check` reports
`arxiv-int 0.1.0 (arxiv_int)`. The required `make ci` gate covers formatting, linting, typing,
complexity, shell, documentation-link, specification-plan, and deterministic tests, and it passes
at 172 tests; the complexity gate rejects Radon D-or-worse and cognitive complexity above 15, so
both subchecks now run to completion. `make quality` adds a diagnostic coverage report, Markdown
lint, and the build. A numeric coverage percentage is not an acceptance gate; see
[behavior-first test policy](../records/0026-foundation-adopt-behavior-first-test-policy.md).
The quality baseline repair recorded 90.14% total coverage against a then-required 90% floor
([quality baseline repair](../records/0003-foundation-restore-quality-gate-baseline.md)).
`make build` produces `dist/arxiv_int-0.1.0.tar.gz` and
`dist/arxiv_int-0.1.0-py3-none-any.whl`.
