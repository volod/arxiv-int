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
make run
```

The separate `arxiv-int-plan` entrypoint supports `make plan-status`. Repository quality modules
remain under `src/arxiv_int/quality/`, and shared shell functions use the `arxiv_int_` prefix.

## Dependency seams and feature groups

The core install declares no runtime dependency. Installing `arxiv-int` gives the CLI, the feature
catalog, and the domain interfaces; every heavy extraction, NLP, embedding, graph, dashboard,
evaluation, and GPU stack stays behind a named optional group.

`src/arxiv_int/features/catalog.py` is the single source of truth for group identity: summary,
owning capability, declared distributions with import name, SPDX licence and purpose, system
dependencies, and the `STAGE_FEATURES` map from a pipeline stage to the groups it activates.
`pyproject.toml` owns version pins for the groups that carry members, and a unit test keeps the two
in agreement in both directions.

| Group | State | Declared distributions |
| --- | --- | --- |
| `contracts` | populated | `jsonschema` (MIT), `pyyaml` (MIT) |
| `graph` | populated | `pyshacl` (Apache-2.0), `rdflib` (BSD-3-Clause) |
| `inference` | populated | `httpx` (BSD-3-Clause) |
| `lake` | populated | `duckdb` (MIT), `pyarrow` (Apache-2.0) |
| `store` | populated | `psycopg[binary]` (LGPL-3.0-only) |
| `embeddings` | reserved for `semantic-retrieval` | none yet |
| `evaluation` | reserved for `evaluation-foundation` | none yet |
| `extraction` | reserved for `corpus-foundation` | none yet |
| `gpu` | reserved for `local-inference` | none yet |
| `nlp` | reserved for `russian-nlp` | none yet |
| `ui` | reserved for `discovery-visualization` | none yet |

A reserved group carries its summary, system dependencies, and owning capability but no extra in
`pyproject.toml`, because the specification leaves those component choices to the evaluation of the
capability that needs them. That capability adds members to the group it already has instead of
adding a dependency to the core.

`arxiv-int features [--stage STAGE]`, wrapped by `make features [STAGE=...]`, prints every group
with its status -- `installed`, `missing`, or `reserved` -- the stages that activate it, its install
command, the licence and purpose of each declared distribution, and the system dependencies it
needs. That output is the dependency licence inventory.

`arxiv_int.features.require_module()` imports one declared optional module or raises
`MissingFeatureError` naming the module, its group, and the exact install command. Requiring a
module that no group declares raises `LookupError`, so an optional import cannot reach production
code without a catalog entry.

## selfsuvis runtime-policy reuse

The configuration, path-safety, preflight, queued-logging, timing, partial-result, and model-lifecycle
seam is an attributed functional extraction from `selfsuvis` revision
`bd0f4447bf20a72e9421c93f208ce1f52f1c622b`. The pinned upstream candidates total 1,495 lines across
eight coupled modules. Its built wheel is 1,081,837 bytes and 3,391,073 bytes unpacked; its 30 direct
requirements resolve to 136 distributions on Python 3.12, including Torch/CUDA, web, database,
vector-store, and model-client packages. The upstream source distribution needs setuptools and
wheel; several dependencies contain native code, while its optional vision lane includes CUDA JIT
components.

The chosen form is a 296-line, 9,439-byte standard-library-only extraction organized by project
function:
`arxiv_int.config`, `arxiv_int.paths`, `arxiv_int.doctor.report`, `arxiv_int.pipeline.steps`,
`arxiv_int.observability.logging`, and `arxiv_int.inference.scheduling`. Together they provide
mapping-based configuration precedence, fail-closed real-path containment, accumulated readiness
findings, monotonic step timing with earlier results preserved after failure, queue-serialized
logging, GPU-budget placement, and guaranteed model release. There is no source-named production
package or adapter. The modules neither import the upstream package nor expose video, IoT, Qdrant,
LangGraph, Torch, or service-client behavior.

Each functional module docstring records the origin, immutable revision, and MIT licence.
`THIRD_PARTY.md` maps those modules to their upstream basis and local changes, and `NOTICE`
reproduces the licence. The measurement and decision evidence is stored under
`$DATA_DIR/reuse/selfsuvis/decision.json`; no upstream change is required, so there is no change
request.

## fl-op contract-governance reuse

The registry, canonical-model, generator-dispatch, semantic-fingerprint, and baseline-policy seam is
an attributed functional extraction from `fl-op` revision
`1f452ecaeded92c6bbbd4a86de9ded1ea7444e60`. The inspected contract package has 4,089 Python lines
and 152,515 source bytes; the cohesive registry/generator/fingerprint/evolution slice has 2,638
lines and 96,830 bytes. The complete upstream wheel is 427,017 bytes and 1,299,085 bytes unpacked.
Its 15 direct runtime requirements resolve to 64 installed distributions and 610,157,079 bytes on
the measured Linux/Python 3.11 environment before installing the upstream wheel itself.

The upstream wheel is pure Python and builds with Hatchling, but its mandatory closure includes
OR-Tools, NumPy, SciPy, scikit-learn, FastAvro, PyArrow, Pydantic Core, PyProj, Shapely,
Cryptography, CFFI, Greenlet, and Pandas wheels containing native code. It also carries solver,
serving, experiment-tracking, and geospatial behavior that the contract seam does not use. The
chosen form is therefore a 484-line, 17,516-byte extraction with PyYAML as its only runtime import;
PyYAML was already in the locked `contracts` extra, and the extraction adds only PyYAML type stubs
to the development extra.

`arxiv_int.contracts` now provides an explicit-root file registry, immutable canonical semantic
model, the upstream-compatible semantic metadata hash, a narrow generator protocol and registered
dispatch, and pure schema snapshot/change/version/baseline primitives. The registry rejects paths
outside its root and detects drift from a reviewed semantic hash. It never discovers a sibling
checkout and imports no fleet, solver, model, serving, Arrow, Elasticsearch, or upstream package.
The later contract-governance tasks own project ODCS documents, `x-arxiv-int` adapters, concrete
physical generators, full adjacent-history policy, migrations, and live-store checks.

Each extracted module records the source, immutable revision, and MIT licence. `THIRD_PARTY.md`
maps the upstream basis and local changes, while `NOTICE` carries the licence. Functional tests
cover upstream-equivalent fingerprint and change classification, canonical loading, registry path
safety and drift detection, generator dispatch, deterministic baselines, and import isolation. The
measurement record is `$DATA_DIR/reuse/fl-op/decision.json`. Extraction needs no upstream change,
so no change request exists.

Output-sensitive tooling is pinned exactly: `complexipy`, `mypy`, `pymarkdownlnt`, `radon`, `ruff`,
and `shellcheck-py`. Formatting, typing, complexity, and Markdown findings therefore do not move
with a resolver update. `make bootstrap` still installs only the core plus the `dev` extra.

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
`tests/quality/` exercise the quality package and verify the repository plan summary.
`tests/features/` covers catalog lookup, stage mapping, install-status reporting, and the missing
and undeclared import messages. `tests/interfaces/` proves fake backends satisfy each protocol.
`tests/dependencies/` keep the extras and the catalog in agreement, require an exact pin for every
output-sensitive tool, and import the package in a subprocess to prove that no declared optional
module reaches the core import graph. Focused tests live beside their corresponding functional areas
and cover layer precedence, symlink escape rejection, accumulated preflight results, partial-result
preservation, concurrent log serialization, model placement and cleanup, and import isolation from
the upstream and heavy stacks.

The locked bootstrap and import doctor pass, and `make run` reports
`arxiv-int 0.1.0 (arxiv_int)`. The required `make ci` gate covers formatting, linting, typing,
complexity, shell, documentation-link, specification-plan, and deterministic tests. `make build`
produces `dist/arxiv_int-0.1.0.tar.gz` and `dist/arxiv_int-0.1.0-py3-none-any.whl`.
