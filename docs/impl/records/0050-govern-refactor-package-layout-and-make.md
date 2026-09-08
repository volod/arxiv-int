# Task Record

## Task and scope

- Id / capability / checkpoint: `refactor-package-layout-and-make` / `governance` / none
- State: accepted
- Source: ad hoc request to split the Makefile, package non-Python assets for library
  delivery, rename the dbt project away from `transformations/`, and nest oversized
  `src/arxiv_int/` subpackages. Initial `make plan-status` next eligible agent task
  remains `implement-streaming-inventory` (this chore does not consume it).
- Amendments: 2026-09-08 user request that the tests tree mirror `src/arxiv_int`
  subpackages. Original block retained below. Revised full block:

```markdown
#### refactor-package-layout-and-make

Provide the following refactoring to improve code quality and readability:

1. Refactor Makefile to improve modularity and readability; use
   https://github.com/volod/loc-lm-bench/blob/main/Makefile as an example;
2. In the future, I want to use this repo as a Python library. We have configs,
   contracts, and ontology directories in the project root. Please investigate
   whether we can move them into the src/arxiv_int package to simplify delivery;
3. We have a dbt transformations directory in the project root and
   src/arxiv_int/transformations subpackage, which is confusing. Please rename
   the root dbt transformations directory to, e.g., dbt_trans. Also, think about
   whether we will follow best practices or use a custom approach if we move
   dbt_trans (or a name you find better) into src/arxiv_int/
4. Some src/arxiv_int/ subpackages have a small number of modules in the
   subpackage root without their own submodules, and it is readable. Some of the
   src/arxiv_int/ subpackages, such as contracts, data_quality, evaluation,
   inference, observability, and pipeline, have a mix of subpackages and modules
   at the root, or more than 7-8 modules, making the list long and hard to
   understand. Please refactor such large subpackages, create an additional
   level of subpackages, and keep the root of the first level of subpackages
   without modules, but only subpackages, or, if needed, an entry-point module
   like cli.py or metadata.py, etc., at the root of such subpackages.
5. tests structure should reflect arxiv_int subpackages tree structure.
```

```markdown
#### refactor-package-layout-and-make

Provide the following refactoring to improve code quality and readability:

1. Refactor Makefile to improve modularity and readability; use
   https://github.com/volod/loc-lm-bench/blob/main/Makefile as an example;
2. In the future, I want to use this repo as a Python library. We have configs,
   contracts, and ontology directories in the project root. Please investigate
   whether we can move them into the src/arxiv_int package to simplify delivery;
3. We have a dbt transformations directory in the project root and
   src/arxiv_int/transformations subpackage, which is confusing. Please rename
   the root dbt transformations directory to, e.g., dbt_trans. Also, think about
   whether we will follow best practices or use a custom approach if we move
   dbt_trans (or a name you find better) into src/arxiv_int/
4. Some src/arxiv_int/ subpackages have a small number of modules in the
   subpackage root without their own submodules, and it is readable. Some of the
   src/arxiv_int/ subpackages, such as contracts, data_quality, evaluation,
   inference, observability, and pipeline, have a mix of subpackages and modules
   at the root, or more than 7-8 modules, making the list long and hard to
   understand. Please refactor such large subpackages, create an additional
   level of subpackages, and keep the root of the first level of subpackages
   without modules, but only subpackages, or, if needed, an entry-point module
   like cli.py or metadata.py, etc., at the root of such subpackages.
```

## Implementation

Layout decisions:

- Make fragments live under `make/` with grouped `##@` help, matching loc-lm-bench.
- Product ODCS, ontology, configs, and the dbt project ship as
  `src/arxiv_int/resources/{contracts,ontology,configs,dbt}` so a wheel install
  does not depend on a checkout-root `find_project_root()` walk.
  `arxiv_int.resources.paths` prefers a same-named overlay under a caller
  `project_root` when that directory exists. Writes use `output_root` /
  `configs_output_root` so disposable trees cannot mutate packaged sources.
- The dbt project is named `dbt` (not `dbt_trans`): Python stays
  `arxiv_int.transformations`; dbt still runs from a copied working tree under
  `DATA_DIR` (existing custom assembly, required because dbt needs a writable
  filesystem project).
- Nested packages: `contracts/{catalog,lint}`, `data_quality/{engine,rules,generate}`,
  `evaluation/{bundles,export,fixtures,families,proof,evaluate,scoring}`,
  `inference/{client,providers,scheduler,policy}`,
  `observability/{logging,metrics,sinks}`, `pipeline/{dag,run,quality}`.
  First-level package roots keep `__init__.py` plus entry modules (`cli.py`,
  `commands.py`) where needed. Declared model footprints live in
  `inference.policy.footprint` so `inference.client` does not import the scheduler
  package.
- Tests mirror those packages. Compose/config units moved to `tests/runtime/`;
  extras pin checks to `tests/features/test_extras.py`; DAG units to
  `tests/pipeline/dag/`. Shared helpers (`conftest.py`, `_builders.py`, `fakes.py`)
  stay at the owning package root. `tests/fixtures/` and `tests/integration/`
  remain non-package trees. Generated Pydantic adapters under
  `src/arxiv_int/resources/contracts/generated/pydantic/` are excluded from Ruff
  and mypy like Alembic revisions.

Current-state: [Developer tooling](../current/developer-tooling.md),
[Contracts](../current/contracts.md), [Canonical store](../current/canonical-store.md),
[Project foundation](../current/project-foundation.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Format, lint, types, complexity, shell, doc links, spec-plan | `make ci` (includes `format-check`, `lint`, `typecheck`, `complexity-gate`, `shell-lint-gate`, `lint-doc-links`, `lint-spec-plan`) | pass |
| Contracts, ontology, inference schemas, identity policy, fixtures | `make ci` (`contracts-check`, `contracts-evolution`, `db-check`, `ontology-check`, `inference-schemas-check`, `identity-policy-check`, `evaluation-fixtures-check`) | pass; live SQL `not-run` |
| Deterministic tests | `make ci` / `make test` (`-m "not heavy"`) | pass; 1103 passed, 50 deselected (heavy) |
| Plan counts | `make plan-status` | 68 tasks; next agent `implement-streaming-inventory`; this chore did not consume a plan task |

## Audit handoff

`none identified`. Reviewed layout, packaged-resource resolvers, nested imports, and mirrored
tests. Leftover empty `tests/compose`, `tests/config`, `tests/dependencies`, and
`tests/pipeline/orchestration` directories were removed.

## Close or resume

Accepted. Spec layout, current-state pages, and record index updated. Plan task counts are
unchanged. Next eligible plan task remains `implement-streaming-inventory`.
