# Task Record

## Task and scope

- Id / capability / checkpoint: `define-domain-investigation-contracts-and-ontology` /
  `contract-governance` / `review-foundation-and-store-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `define-domain-investigation-contracts-and-ontology`; code
  revision `e4de15c` with accepted versioned ontology assets present.
- Initial count: 82 tasks (71 agent, 11 human).
- Accepted task:

```markdown
#### define-domain-investigation-contracts-and-ontology

Define evidence semantics and output contracts for design relationships, bills of materials,
supply chains, invoices, payments, and their run-artifact registry entries.

- Serves: `contract-governance` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: CLEAR
- Dependencies: [Versioned ontology assets](records/0013-contract-gov-establish-versioned-ontology-assets.md);
[Deterministic schema generation](records/0011-contract-gov-implement-deterministic-schema-generation.md).
- User-visible outcome: Operators see consistent definitions for `part-of`, supply roles, invoice
obligations, payment allocations, conflicts, and empty/partial results before graphs are generated.
- Scope boundary: Define source-asserted investigation semantics and schemas; do not infer missing
ownership, delivery, settlement, liability, engineering completeness, or accounting truth.
- Data and artifact paths: `contracts/datasets/domain-artifacts*.odcs.yaml`,
`contracts/canonical/`, `ontology/`, generated table/JSON/graph schemas, and domain fixtures.
- Execution path: Model designs, revisions, assemblies, components, materials, parties, locations,
natural persons versus legal entities, product/model/revision versus equipment instances, scoped
identifiers, time-qualified party roles, accounts, orders, shipments, invoices, invoice lines,
ledger postings, payments, credit notes/reversals, currencies, decimal quantities, allocations, and
typed relations; define evidence, review/inclusion, arithmetic, conflict, and artifact-status rules.
- Acceptance gates: Contract and ontology validation pass; positive and negative fixtures separate
reference from `part-of`, invoice from delivery, and amount/date similarity from payment;
same-name nonmatches, explicit versus candidate ownership, table/cell/container anchors, BOM
cycles/alternatives/effectivity, units, currencies, direction, cardinality, and creation statuses
are unambiguous and versioned.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Added five product ODCS datasets under `contracts/datasets/domain-artifacts-*.odcs.yaml` with
mappings, canonical extracts, reviewed evolution baselines, generated physical schemas, and
migration `db/migrations/20260906130000_domain_investigation_tables.sql` (schema dump updated).

Extended ontology to `1.1.0` with `domain.ttl`, `domain-mappings.ttl`, and `domain.shacl.ttl`:
`part-of` vs `references`, explicit vs candidate ownership, allocation vs amount/date similarity,
party roles, BOM/supply/invoice classes, and units. `domain_rules.py` encodes BOM cycle/alternative,
currency/allocation, supply-stage, registry creation-status, and enum checks. Fixtures under
`tests/ontology/domain_fixtures/` cover the required separations. Capability `contract-governance`
is marked shipped. Current-state: [Contracts](../current/contracts.md).

## Acceptance evidence

Commands use `DATA_DIR=/tmp/arxiv-int-domain`. Evidence under that root.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Contract validation | `lint_contracts`; `make contracts-check`; product registry | Pass; 20 datasets |
| Ontology validation | `make ontology-check`; catalog 35 classes / 30 predicates | Pass; version 1.1.0 |
| Fixtures separate required distinctions | `tests/ontology/test_domain_investigation.py` | Pass; 12 domain fixtures |
| SHACL/app agreement on structural cases | domain + foundation SHACL tests | Pass |
| Formatting and required CI | `make format`; `make ci DATA_DIR=/tmp/arxiv-int-domain` | Pass; 432 tests |
| Full quality | `make quality DATA_DIR=/tmp/arxiv-int-domain` | Pass; coverage 90.16% |

Fixtures prove contract/ontology semantics, not real-archive quality or CUDA fit. No ownership,
delivery, settlement, liability, engineering completeness, or accounting truth is inferred.

## Audit handoff

none identified. Reviewed ODCS bindings, ontology additive evolution baseline refresh, migration
dump coverage, and fixture coverage of the named separations.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts move from 82 to 81 tasks (71 to 70
agent; 11 human unchanged). `contract-governance` marked shipped. Next agent work follows
`make plan-status`.
