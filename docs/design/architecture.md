# Execution Architecture

The [specification](spec.md) owns product behavior, scope, and acceptance. This page defines how
the archive-to-knowledge pipeline is assembled. It is a target design; available modules and
commands remain indexed by [current implementation](../impl/current.md).

## Runtime boundaries

One typed Python application coordinates bounded CPU workers, local inference, and one PostgreSQL
service on a CUDA host. PostgreSQL holds canonical records and decision overlays; normalized
artifacts retain portable, versioned extraction and analysis outputs. Search indexes and graph
projections can be rebuilt. Operator review history and source path ledgers require backup.

```text
Directory silos (read-only)
  -> inventory -> extract -> normalize -> dedupe -> chunk
                              |                    |
                              +-> classify         +-> lexical search
                              |                    +-> NLP -> entity anchors
                              |                    +-> topics          |
                              |                          ontology + facts
                              |                                    |
                              |                         validation + identity view
                              |                                    |
                              |                     catalogs + domain artifacts
                              |                                    |
                              |                              anomaly analysis
                              |                                    |
                              +------------------------> evaluate -> entry report
                                                                   |
                                                    knowledge-base.json generation

Optional projections: selected embeddings/vector search; AGE; local viewers
Separate utility: classification export -> archive reorganize -> path-event ledger
```

The arrows represent data dependencies, not one process per box. Stage control, forecast,
resource leases, artifact validation, and progress reporting surround every stage. CPU-only
stages do not reserve CUDA. Heavy OCR, NER, embedding, and generation share the same host-wide
GPU lease; an optional runtime cannot bypass it. Work that needs more than the selected device
budget is refused or uses an explicitly evaluated smaller/offloaded profile.

## Stage dependency contract

Every stage declares its required input contracts, output contracts, configuration fingerprint,
resource estimator, shard/reuse key, validator, and runner in one registry. Dependencies are
artifact references, never a test that a directory happens to exist. Conditional inputs become
mandatory only when their feature/profile is selected.

| Stage | Required inputs | Conditional inputs and limits |
| --- | --- | --- |
| `preflight` | Resolved roots, selected profile, available tools and contracts | Check only selected services/models |
| `inventory` | Source roots and completed preflight | Bounded discovery; strong hashes; no extraction |
| `extract` | Inventory content and member manifest | OCR/layout lanes share the model resource scheduler |
| `normalize` | Extraction records and source-coordinate maps | Preserve original text and table/cell structure |
| `dedupe` | Inventory hashes and normalized documents | Near-duplicate suppression is a reversible overlay |
| `chunk` | Normalized documents/spans and duplicate policy | Stable coordinates and chunker profile |
| `classify` | Inventory accounting, normalized content, pinned hierarchy | Chunk evidence if used; no placement executor |
| `load-lexical` | Chunks, document metadata, source locations | Classification filters can join later by snapshot |
| `nlp` | Normalized documents/chunks and language/model profiles | CPU baseline; optional measured GPU lane |
| `entities` | Mentions and identifier/type contracts | Create unresolved anchors, then propose cluster overlays |
| `ontology` | Pinned vocabulary, domain contracts and SHACL assets | Validate configuration before facts; no automatic axiom invention |
| `facts` | Source tables/spans, mention anchors, ontology/domain contracts | Local structured models only for selected bounded lanes |
| `validate-facts` | Proposed facts, ontology and review policy | Type/evidence/conflict validation; preserve proposed and rejected records |
| `topics` | Normalized content and NLP term statistics | Embeddings optional; no graph requirement |
| `catalogs` | Entity/identity snapshot and validated fact view | Topic/class filters join pinned snapshots |
| `domain-artifacts` | Validated facts, identity and domain inclusion policy | Operates relationally; graph rendering needs no AGE |
| `anomalies` | Inventory quality, validated facts and domain artifacts | Topic drift only when comparable topic snapshots exist |
| `graph` | Validated facts and identity snapshot | AGE optional; bounded relational/open graph exports required |
| `embed`, `load-vector` | Selected chunk tier, embedding profile and artifacts | Explicit optional branch, resource/quality gates |
| `evaluate` | Requested outputs, source manifest, validators | Gold metrics only when a reviewed scoring set is selected |
| `report` | Coverage/evaluation, topics, catalogs, facts, domain and anomaly registries | Optional graph/viewer links; deterministic HTML/JSON baseline |

The `facts` stage owns extraction and `validate-facts` owns claim validation. Ontology definitions
are upstream configuration, not an output that fact extraction has to invent. Identity remapping
invalidates views that consume the cluster snapshot, while unchanged source-level assertions
retain their extraction cache.

The investigation profile requires every baseline output in the specification. A user-selected
stage executes its dependency closure or validates exact existing upstream artifacts. `--from`
does not excuse missing/stale inputs; `--to` includes only the selected endpoint's closure. Disabled
optional branches are explicit `not-selected` records. Missing required runners or failed validators
cannot be silently skipped. Registry order in the plan expresses priority; cross-group proof
dependencies are allowed and are not runtime cycles.

## Module ownership and durable interfaces

| Owner | Responsibility |
| --- | --- |
| `cli.py` and Make | Parse commands and delegate to typed application services |
| `runtime/`, `readiness/` | Resolve roots, profiles, tools, storage classes, and service availability |
| `pipeline/` | Registry, DAG, leases, journals, forecast, generations, update/rebuild/prune |
| `contracts/`, `interfaces/` | Canonical schema, identity/provenance, validators, and backend seams |
| `extraction/`, `nlp/`, `identity/` | Source records, mentions, proposed assertions, reversible identity mappings |
| `classification/` | Hierarchy and per-physical-file classification exports |
| `stores/`, `retrieval/`, `graph/` | Canonical access and rebuildable query projections |
| `domain_artifacts/` | Party/transaction, BOM, supply-chain, and reconciliation calculations |
| `analytics/` | Explainable anomaly detectors, cohorts, grouped findings, and review views |
| `query/`, `reporting/` | Three catalogs, bounded queries, evidence expansion, entry report, portable renders |
| `archive/` | Standalone artifact-consuming organization and source-location lookup |
| `evaluation/`, `observability/` | Replayable quality evidence, coverage, resource metrics, and progress |

Rendered graphs reuse contracted node/edge tables. Grafana and AGE Viewer consume read-only views;
they do not define the semantics of relations or own required report generation. A model may propose
facts or wording but cannot execute archive operations, select arbitrary filesystem paths, issue
unbounded SQL, or publish an accepted relationship. Source text is data, including instructions
embedded in documents. Rendered snippets are escaped and active document content is never executed.

## Publication, recovery, and location

Workers publish validated content-addressed artifacts with checksums through the control layer.
Database loads stage rows and commit bounded transactions. Publication has three distinct steps:

1. Seal artifact and projection manifests for the requested generation.
2. Validate contracts, complete file/family accounting, evidence links, and the entry report.
3. Commit one active knowledge-base pointer referring to those exact snapshots.

Files and PostgreSQL do not share a distributed transaction. A crash can leave unreferenced staging
files, but cannot make an incomplete generation active. Startup reconciliation repairs a missing
database registry entry from a verified sealed manifest, or quarantines an unverified output.
Pruning later removes only unreferenced derived data according to the retention policy. Updating a
graph or catalog cannot mix it with unrelated active identity/fact versions within one report.

Source additions/changes/removals are reconciled only from complete scans of the same source scope.
An unavailable disk never retracts an archive's knowledge. Container and spreadsheet evidence can
resolve through a physical source occurrence even if the corresponding content is deduplicated.
The organizer consumes classification and location manifests, takes an exclusive placement lease,
and journals verified copies or per-file moves. Its ledger is portable and can be imported without
rerunning classification; future scans record path changes rather than changing document identity.

## First complete vertical slice

Use a small network-free mixed fixture containing plain text, a structured financial table, a
product description with an explicit assembly, two same-name parties, a malformed input, and a
cross-document relation. Predeclare expected source anchors, identity nonmatches, invoice/payment
allocations, partial BOM, anomaly findings, and empty cases. This fixture exercises actual adapters
selected for the baseline; mocked model responses test error paths but cannot prove CUDA execution.

One `pipeline run --profile investigation` must produce the complete manifest and portable report;
the same source bytes run twice must reuse heavy outputs. Then prove the selected local model on one
CUDA device with bounded real inference and publish the authorized provided-archive proof. The proof
captures resources, quality limits, output checksums, source immutability, and error/empty states.
Directory-to-report acceptance is independent of vector comparisons, AGE, UI services, and archive
organization. Required gates and future work are owned by the [specification](spec.md#required-acceptance-gates)
and [plan](../impl/plan.md), not duplicated here as a second backlog.
