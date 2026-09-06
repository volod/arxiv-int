# Task Record

## Task and scope

- Id / capability / checkpoint: `establish-canonical-contract-registry` / `contract-governance` /
  `review-foundation-and-store-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `establish-canonical-contract-registry`; code revision `c1f9eda`
  at task start with prior accepted contract-identity work present.
- Initial count: 86 tasks (75 agent, 11 human).
- Accepted task:

```markdown
#### establish-canonical-contract-registry

Define ODCS contracts, a canonical semantic model, dataset registry, and physical-to-canonical
mappings for the first pipeline entities.

- Serves: `contract-governance` --
[Contract-first data governance](../design/spec.md#contract-first-data-governance)
- Agent status: CLEAR
- Dependencies: The contract primitives and package/CLI identity documented in
[Project foundation](current/project-foundation.md#contract-primitives).
[Contract identity and reference validation](records/refactor-contract-identity-and-reference-validation.md).
- User-visible outcome: Documents, spans, chunks, objects, mentions, facts, topics, ontology terms,
embeddings, source occurrences, transactions, catalogs, anomaly findings, and evaluation items
have one reviewable schema source of truth.
- Scope boundary: Define contracts and semantic bindings; do not create live database tables or
infer domain-specific ontology terms from the corpus.
- Data and artifact paths: `contracts/registry.yaml`, `contracts/canonical/`, `contracts/datasets/`,
`contracts/mappings/`, and `src/arxiv_int/contracts/`.
- Execution path: Extend the existing registry and canonical-model interfaces with project-specific
ODCS 3.1 adapters; namespace project hints under `x-arxiv-int`; add Data Contract CLI validation and
Pydantic loaders that preserve unknown metadata.
- Acceptance gates: Official ODCS JSON Schema and Data Contract CLI lint pass; ids, versions,
references, canonical bindings, relationship targets, and required identities are unique and
complete.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Shipped `contracts/` as the product ODCS 3.1 registry: 15 datasets with mappings, canonical model
and entity ODCS extracts, and reviewed semantic fingerprints in `registry.yaml`. Project hints use
`customProperties` property `x-arxiv-int` (nested `canonicalBinding` and postgres schema/table).
The official ODCS JSON Schema is vendored at `contracts/odcs/odcs-json-schema-v3.1.0.json`
(Bitol pin `f5bfbb8`).

Python support adds `odcs_ext` binding resolution (with legacy `canonicalBinding` compatibility),
Pydantic loaders that preserve unknown metadata, official-schema validation, registry integrity
checks, Data Contract CLI lint via on-PATH `datacontract` or `uv tool run`, `arxiv-int contracts
lint`, and `make contracts`. The `contracts` extra now includes `pydantic`; bootstrap and CI sync
`--extra contracts` with `dev`.

No live database tables and no corpus-derived ontology terms were introduced. Current-state page:
[Contracts](../current/contracts.md).

## Acceptance evidence

Commands use `DATA_DIR=/tmp/arxiv-int-contract-registry`. Evidence is under
`$DATA_DIR/regression/20260906/`. Offline quality reused
`UV_CACHE_DIR=/tmp/arxiv-int-service-planning/cache/uv`. Data Contract CLI `1.1.3` was installed
with `uv tool install` so offline quality could find `datacontract` on PATH.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Official ODCS JSON Schema | `validate_dataset_files(contracts)`; product tests; `contracts-lint.txt` | Pass; 15 datasets, 0 schema findings |
| Data Contract CLI lint | `arxiv-int contracts lint`; `test_datacontract_cli_lints_every_dataset` | Pass; 15 datasets with CLI `1.1.3` |
| Ids/refs/bindings/relationships/identities | `validate_registry_integrity`; product registry tests | Pass; unique ids, rooted refs, FK targets, required PKs |
| Pydantic unknown metadata | `test_loaders_preserve_unknown_metadata` | Pass |
| Existing primitive fixtures | `tests/contracts/test_*.py` | Pass; legacy bindings retained |
| Formatting and required CI | `make format`; `make ci DATA_DIR=/tmp/arxiv-int-contract-registry`; `ci.txt` | Pass; 327 deterministic tests |
| Full quality | `UV_OFFLINE=1 ... make quality ...`; `quality.txt` | Pass; 327 tests, 90.94% coverage, Markdown, typing, complexity, shell, links, plan, build |

Complexity on integrity helpers was split without weakening gates. Fixtures prove contract/lint
behavior, not real-archive or CUDA fit.

## Audit handoff

Self-review covered ODCS schema pin, `x-arxiv-int` nesting, fingerprint stability, readiness load
of the shipped registry, offline Data Contract CLI availability, and documentation links.
`none identified`. No service, model job, port or external corpus resource was started.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts move from 86 to 85 tasks (75 to 74
agent; 11 human unchanged). `contract-governance` now has a reviewable ODCS source of truth; no
capability shipment status changed. Next agent work follows `make plan-status`.
