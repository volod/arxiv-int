# Task Record

## Task and scope

- Id / capability / checkpoint: `establish-versioned-ontology-assets` / `contract-governance` /
  `review-foundation-and-store-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `establish-versioned-ontology-assets`; code revision `80df283`
  with accepted evolution/migration policy present.
- Initial count: 83 tasks (72 agent, 11 human).
- Accepted task:

```markdown
#### establish-versioned-ontology-assets

Create the controlled vocabulary, classes, predicates, semantic mappings, SHACL shapes, and open RDF
exports that validate the knowledge model.

- Serves: `contract-governance` -- [AGE graph projection](../design/spec.md#age-graph-projection)
- Agent status: CLEAR
- Dependencies: [Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
representative domain vocabulary can begin
from reviewed fixtures.
- User-visible outcome: Object/fact semantics are inspectable, versioned, exportable, and testable
independently of AGE.
- Scope boundary: Establish a minimal evidence-backed ontology; do not claim automated ontology
induction is authoritative.
- Data and artifact paths: `contracts/canonical/`, `ontology/*.ttl`, `ontology/*.shacl.ttl`,
generated `ontology.*` bindings, and `tests/ontology/`.
- Execution path: Define stable URIs, labels in source languages, domain/range, units, selected
disjoint/functional constraints, mappings, and deprecation/alias rules; validate with
rdflib/pySHACL and a second reasoner where practical.
- Acceptance gates: RDF parses; SHACL positive/negative fixtures agree with application validation;
every active predicate maps to a contract binding; breaking ontology changes follow evolution
policy.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Shipped pinned ontology assets under `ontology/`: `manifest.yaml`, `core.ttl`, `mappings.ttl`, and
`shapes.shacl.ttl` for foundation classes/predicates (not domain BOM induction). English and
transliterated Russian labels use language tags. Selected disjoint pairs
(NaturalPerson/LegalEntity, ProductModel/EquipmentInstance), functional properties
(`preferredName`, `supersedes`), units, and a deprecated `sameAs` -> `aliasOf` successor rule are
included.

`src/arxiv_int/ontology/` loads the catalog, validates assertions, wraps pySHACL, runs owlrl
disjointness probes, generates deterministic `ontology/generated/ontology.*.json` bindings, and
classifies ontology evolution against `ontology/evolution/baseline.json`. Active predicates map to
canonical binding `fact.predicateId`. Operator entrypoints: `arxiv-int ontology check|generate` and
`make ontology-check|ontology-gen` (ontology-check is in `make ci`). Canonical model metadata now
records `ontologyRef` / `ontologyVersion`. Current-state: [Contracts](../current/contracts.md).

## Acceptance evidence

Commands use `DATA_DIR=/tmp/arxiv-int-ontology`. Evidence under `$DATA_DIR/`.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| RDF parses | `load_ontology_graphs`; `test_product_ontology_rdf_parses`; ontology-check | Pass; core/mappings/shapes non-empty |
| SHACL and application agree | `tests/ontology/test_shacl_agreement.py` + fixtures | Pass; 2 positive and 4 negative cases agree |
| Active predicates map to contract binding | ontology-check binding coverage; product catalog test | Pass; all active predicates bind `fact.predicateId` |
| Breaking ontology changes follow evolution | `tests/ontology/test_evolution.py`; reviewed baseline | Pass; additive/breaking/identical + version rules |
| Second reasoner | owlrl disjointness probe in ontology-check | Pass; NaturalPerson+LegalEntity detected |
| Formatting and required CI | `make format`; `make ci DATA_DIR=/tmp/arxiv-int-ontology`; `ci.txt` | Pass; 413 deterministic tests |
| Full quality | `make quality DATA_DIR=/tmp/arxiv-int-ontology`; `quality.txt` | Pass; 413 tests, 90.28% coverage, Markdown, typing, complexity, shell, links, plan, build |

Fixtures prove ontology/SHACL agreement, not real-archive quality or CUDA fit. Domain investigation
predicates remain out of scope for this task.

## Audit handoff

none identified. Reviewed RDF parse paths, binding coverage against the canonical model, SHACL and
application parity on fixtures, owlrl disjointness, generation drift, and evolution baseline fail-
closed version policy. No service, model job, port, or external corpus resource was started for
acceptance beyond disposable Docker used by unrelated contract SQL checks in CI.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts move from 83 to 82 tasks (72 to 71
agent; 11 human unchanged). `contract-governance` now exposes inspectable versioned ontology assets;
no capability shipment status changed. Next agent work follows `make plan-status`.
