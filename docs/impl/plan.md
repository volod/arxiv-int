# arxiv-int Implementation Plan

Forward-only: this file contains only work that remains. Product behavior, boundaries, evaluation,
and delivery strategy belong in [the specification](../design/spec.md). Task structure, statuses,
ordering, and lifecycle rules belong in the
[planning workflow](../guide/planning-workflow.md). Available behavior and durable results belong in
[current-state documentation](current.md).

## Agent Implementation Tasks

All schema and dataset work follows the specification's
[tool ownership and quality policy](../design/spec.md#data-transformations-and-quality):
contract-derived SQLAlchemy metadata and Alembic revisions, dbt models for relational
transformations, Polars/PyArrow for local batches, and Pandera/dbt validation before publication.
Each producer owns its domain models/checks and uses the shared implementations below. Transactional
queries, COPY, extension DDL, and Cypher retain the narrow exceptions defined in the specification.
Archive integration tasks retain tool/rule/model fingerprints and required quality outcomes in the
ordinary run artifacts; a skipped validator cannot establish a pass. Extra cross-checks belong
under `tests/integration/`, never in a production proof publisher or parallel manifest registry.
These requirements also apply to later additive contract/migration work. Integration evidence and
human-review packets stay under the configured roots and are never committed; see
[published proof and evaluation data](../design/spec.md#published-proof-and-evaluation-data).
Each integration task names the ordinary run, artifact roots, manifests, and checksums a reviewer
checks in place.
`Human review handoff` marks an agent producer of human-evaluation evidence; it is not approval or
a prerequisite on the producer. Follow the [handoff workflow](../guide/planning-workflow.md#human-review-handoffs)
and name ready/pending human decisions and the dependent work that must wait at task completion.

### Archive classification -- `archive-classification`

#### prove-archive-classification-on-provided-archive

Classify the supplied archive and validate its complete hierarchical mapping and source references.

- Serves: `archive-classification` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies:
[Hierarchical file classification](records/0079-archive-cls-implement-hierarchical-file-classification.md);
[Pipeline-control provided-archive proof](records/0053-pipeline-prove-pipeline-control-on-provided-archive.md);
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md).
[Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md);
[Retrieval and classification boundaries checkpoint](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md);
[Retrieval and classification identity repair](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md).
- Audit inputs: [AUD-review-retrieval-and-classification-boundaries-8](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff);
[AUD-review-retrieval-and-classification-boundaries-9](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff);
[AUD-repair-retrieval-and-classification-identity-and-evidence-1](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md#audit-handoff);
[AUD-repair-retrieval-and-classification-identity-and-evidence-2](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md#audit-handoff).
- Human review handoff:
[approve-classification-operating-point](#approve-classification-operating-point)
final errors, calibration, coverage and operating-point decision packet.
Packet: `$RUNS_DIR/<run-id>/review/classification/`.
Ready after this proof passes.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`
and `approve-archive-organization-plan`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept/revise the thresholds and exceptional outcomes, or retain unclassified.
- User-visible outcome: Every supplied file has a subject-taxonomy or explicit exceptional result,
with hierarchy, confidence, evidence/failure reasons, and initial source lookup.
- Scope boundary: Run classification and source-manifest validation only; archive placement and its dry-run
are accepted independently under `archive-organization`.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/classifications/`, and
`$RUNS_DIR/<run-id>/classification/`, plus test logs below
`$DATA_DIR/integration/archive-classification/`.
- Execution path: Forecast the closure; classify and validate coverage, hierarchy, evidence, exceptions,
fingerprints, and physical/virtual source accounting; rerun unchanged and record cache hits.
- Acceptance gates: Every physical inventory item has one complete result; virtual members retain container
links; source references and calibration metrics validate; supplied bytes remain unchanged; the
identical rerun invokes no heavy classifier; ordinary artifact manifests and checksums are complete.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Russian NLP -- `russian-nlp`

#### build-russian-language-morphology-and-terminology-lane

Implement language identification, encoding/noise signals, token/morphological analysis, and
versioned dictionaries without changing source evidence.

- Serves: `russian-nlp` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Dependencies: [Normalization, dedupe and chunking](records/0062-corpus-implement-normalization-dedupe-and-chunking.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md).
[Corpus and control integrity checkpoint](records/0063-corpus-review-corpus-and-control-integrity.md).
- Audit inputs: [AUD-review-retrieval-and-classification-boundaries-4](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff);
[AUD-review-retrieval-and-classification-boundaries-6](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff);
[AUD-review-retrieval-and-classification-boundaries-7](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff).
- User-visible outcome: Russian and mixed-language documents expose normalized terms, lemmas where
useful, abbreviations, and corpus terminology for search and extraction.
- Scope boundary: Produce analysis views and mappings only; original text and offsets remain
authoritative.
- Data and artifact paths: `$RESULTS_DIR/normalized/nlp/`, `ontology.term`, `configs/nlp/`,
`src/arxiv_int/nlp/russian/`, and NLP fixtures.
- Execution path: Compare supported local language/morphology libraries; model Cyrillic/Latin,
e/yo variants, abbreviations, technical tokens, and mixed language; emit versioned term statistics
and
glossary proposals.
- Acceptance gates: Language and normalization metrics pass by fixture slice; offsets map to
original evidence; dictionary changes are versioned; unsupported/ambiguous tokens remain explicit.
- Documentation target: `docs/impl/current/russian-nlp.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### evaluate-general-and-domain-ner

Combine a CPU Russian NER baseline with a bounded multilingual/custom-label candidate for people,
organizations, locations, equipment, models, suppliers, materials, standards, and dates.

- Serves: `russian-nlp` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `build-russian-language-morphology-and-terminology-lane`;
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
- User-visible outcome: Entity mentions carry type, confidence, original source span, model/version,
and an understood per-type error rate.
- Scope boundary: Detect mentions; canonical merging belongs to identity resolution and acceptance
does not rely on one aggregate F1.
- Data and artifact paths: `$RESULTS_DIR/normalized/mentions/`, `kg.mention`, `configs/nlp/ner/`, and
`$RUNS_DIR/<run-id>/evaluation/ner/`.
- Execution path: Measure Natasha/Slovnet or equivalent CPU baseline; compare GLiNER-style custom
labels on a bounded sample; calibrate thresholds per type; preserve overlapping mentions and
failure reasons.
- Acceptance gates: Per-type precision/recall and span-overlap metrics produce a declared profile;
high-impact low-precision types stay review-only; inference cost and fallback behavior fit the
resource budget.
- Documentation target: `docs/impl/current/russian-nlp.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### prove-russian-nlp-on-provided-archive

Run the language, morphology, terminology, and NER stages on supplied archive content through an
explicit integration test.

- Serves: `russian-nlp` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `evaluate-general-and-domain-ner`;
[Pipeline-control provided-archive proof](records/0053-pipeline-prove-pipeline-control-on-provided-archive.md).
- User-visible outcome: The supplied Russian and mixed-language documents expose inspectable terms,
language/noise results, mentions, source offsets, model identities, and measured failure classes.
- Scope boundary: Prove configured NLP profiles on available archive languages/types; do not treat
unreviewed mentions as canonical objects or infer quality for absent strata.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/nlp/`, mention tables,
and test logs below `$DATA_DIR/integration/russian-nlp/`.
- Execution path: Forecast; run NLP and mention extraction; validate schemas, language coverage,
offset/source mapping, per-type summaries, and model fingerprints; rerun unchanged and record
dictionary/model cache hits.
- Acceptance gates: All usable NLP outputs validate and resolve to source spans; unsupported and
ambiguous cases are counted; configured metrics are reported by present stratum; unchanged rerun
performs no heavy NER or morphology work; incomplete evidence keeps the task open.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/russian-nlp.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

### Identity, ontology, and graph -- `identity-ontology-graph`

#### implement-ontology-snapshots-and-geotemporal-contracts

Bind evolving ontology and source-asserted place/time semantics to reproducible stage inputs.

- Serves: `identity-ontology-graph` -- [Ontology design](../design/spec.md#ontology-design);
[Geotemporal assertions](../design/spec.md#geotemporal-assertions).
- Agent status: CLEAR
- Dependencies: [Versioned ontology assets](records/0013-contract-gov-establish-versioned-ontology-assets.md);
[Domain contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
- Human review handoff:
[approve-entity-merge-and-ontology-policy](#approve-entity-merge-and-ontology-policy)
ontology/geotemporal candidate semantics and compatibility examples;
include ontology drafts from `review/ontology/`; merge curves come from the resolution producer.
Packet: `$RUNS_DIR/<run-id>/review/identity-ontology/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve/revise merge thresholds, ontology terms and geotemporal interpretation;
keep drafts unpublished.
- User-visible outcome: Every fact/graph/report run names one immutable ontology interpretation and
preserves asserted time/place uncertainty; new terms can be reviewed without changing active meaning.
- Scope boundary: Register the existing `ontology` configuration stage, versioned draft proposals,
and typed geotemporal contracts/validators. Reuse Location and domain terms; no autonomous axiom
acceptance, remote geocoder, GIS platform or extra database extension. Published vocabulary stays
separate from candidates; unknown terms stay proposed/unmapped until human review.
- Data and artifact paths: `src/arxiv_int/resources/ontology/`,
`src/arxiv_int/resources/contracts/`, `src/arxiv_int/ontology/`, mirrored tests,
additive Alembic revisions where required, `$RUNS_DIR/<run-id>/{ontology,review/ontology}/`.
- Execution path: Seal term/mapping/shape/policy fingerprints; retain prior snapshots and explicit
replacement/deprecation mappings; bind ontology identity into validation and projection reuse keys.
Define source-valid versus recorded time, timezone/precision/open intervals, asserted locations,
CRS/axis/units/uncertainty and domain revision/effectivity qualifiers. Implement shared checks and
stage outputs; consumers reuse them. Emit draft-term and compatibility examples for human review.
- Acceptance gates: Additive terms preserve prior replay; changed active meaning, mixed/stale
snapshots and draft leakage refuse publication. Subclass-compatible consumers work; disjoint types
fail. Partial dates/unknown CRS stay uncertain; inverted intervals and invalid coordinates fail;
shared addresses do not merge people/companies; temporal role and product revision boundaries are
replayable. Schema changes follow existing contract/evolution/migration gates.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### implement-probabilistic-entity-resolution

Build reversible object clusters from mentions using blocking, explainable comparisons, and labelled
operating points.

- Serves: `identity-ontology-graph` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Dependencies: `evaluate-general-and-domain-ner`; [Canonical relational schema](records/0021-store-create-canonical-relational-schema.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
`implement-ontology-snapshots-and-geotemporal-contracts`.
- Human review handoff:
[approve-entity-merge-and-ontology-policy](#approve-entity-merge-and-ontology-policy)
merge curves and ontology/geo-time candidate semantics;
include ontology drafts from `review/ontology/`.
Packet: `$RUNS_DIR/<run-id>/review/identity-ontology/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve/revise merge thresholds, ontology terms and geotemporal interpretation;
keep drafts unpublished.
- User-visible outcome: Aliases such as organization names, suppliers, equipment models, and
transliterations resolve to canonical objects with match evidence and uncertainty.
- Scope boundary: Propose or apply reversible cluster overlays; never rewrite source mentions or
auto-merge below the approved precision threshold.
- Data and artifact paths: `kg.object`, `kg.alias`, `kg.resolution_edge`, `kg.cluster_version`,
`$RESULTS_DIR/normalized/linkage/`, and `src/arxiv_int/identity/`.
- Execution path: Create deterministic unresolved anchors before linkage; retain original
mention/fact anchors
through versioned merge/split overlays. Clusters are overlays over domain objects, not new ontology
classes; helper linkage tables stay hidden from catalogs and analyst graph labels per
[Ontology design](../design/spec.md#ontology-design).
Use the selected maintained Splink release directly behind
the local seam with DuckDB; define
blocking and comparison specs; train/calibrate from reviewer labels; persist the model, thresholds,
pair probabilities, and cluster algorithm.
Keep Splink-generated DuckDB SQL inside the maintained adapter; prepare inputs with Polars
and shared Pandera checks. Express relational cluster/alias projection models in dbt with
relationship and stable-key tests; persist review decisions through typed transactions.
- Acceptance gates: Fixture linkage and same-name/jurisdiction/identifier nonmatches pass; archive thresholds
remain proposals until reviewed; only an approved policy may apply automatic merges; replay does
not refit; uncertain/rejected pairs remain separate; rollback restores the
prior cluster view.
Time-bounded roles and shared/ambiguous locations cannot merge unrelated identities;
merge/split replay preserves source anchors, ontology snapshot and asserted validity.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### build-and-validate-age-projection

Project accepted and selected proposed canonical objects/facts into a versioned AGE graph, with
recursive SQL and open export fallbacks.

- Serves: `identity-ontology-graph` -- [AGE graph projection](../design/spec.md#age-graph-projection);
[Ontology design](../design/spec.md#ontology-design).
- Agent status: RUN NEEDED
- Dependencies: `implement-probabilistic-entity-resolution`;
`implement-fact-validation-conflict-and-review-overlays`;
[0025](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
[Versioned ontology assets](records/0013-contract-gov-establish-versioned-ontology-assets.md).
- User-visible outcome: Operators can run bounded Cypher traversals and inspect a graph whose nodes
and edges resolve back to canonical facts and evidence.
- Scope boundary: Projection and bounded query API only; no Neo4j GDS parity claim and no large text
duplication into AGE.
- Data and artifact paths: AGE graph schemas, `ctl.projection`, `$RUNS_DIR/<run-id>/graph/`,
`src/arxiv_int/graph/`, and GraphML/JSON-LD/Turtle exports.
- Execution path: Batch vertices/edges with stable ids; checkpoint high-water marks; validate
counts, ids, sampled paths, and SQL/Cypher results; switch active graph version atomically;
enforce depth/result/time limits.
Project only semantically meaningful ontology classes and predicates; hide helper/projection
bookkeeping from analyst-facing labels. Query exports may yield subclasses of a requested class;
do not invent parallel labels for existing terms.
Use dbt models and data tests for relational vertex/edge inputs, and named SQL/Cypher assets
for bounded parity probes. Alembic owns graph lifecycle metadata; the narrow AGE adapter owns
projection commands and quality results gate the active-pointer transaction.
- Acceptance gates: Rebuild is deterministic; sampled traversals match recursive SQL; evidence
lookup succeeds for every sampled edge; AGE-disabled mode exports the same logical graph; failed
build leaves prior graph active. Analyst-facing labels contain published domain classes only;
helper types are absent from catalogs and graph entry points.
Pinned ontology labels and source-valid/recorded-time/place filters agree with SQL. Draft/deprecated
term handling is explicit, stale snapshots cannot activate, and unknown place/time is not fabricated.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### prove-identity-ontology-graph-on-provided-archive

Resolve identities, validate ontology assets, and build the graph or fallback exports through an
explicit supplied-archive integration test.

- Serves: `identity-ontology-graph` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `build-and-validate-age-projection`;
`prove-knowledge-extraction-on-provided-archive`.
- Human review handoff:
[approve-entity-merge-and-ontology-policy](#approve-entity-merge-and-ontology-policy)
sealed merge/ontology/geo-time review packet.
Packet: `$RUNS_DIR/<run-id>/review/identity-ontology/`.
Ready after this proof and its named producer inputs pass.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve/revise merge thresholds, ontology terms and geotemporal interpretation;
keep drafts unpublished.
- User-visible outcome: Supplied-archive objects, aliases, candidate clusters, ontology terms, and
bounded graph paths are inspectable with reversible decisions and source evidence.
- Scope boundary: Use approved or explicitly proposed review states; do not silently merge uncertain
entities, publish disputed ontology changes, or require AGE when the declared fallback is active.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
identity/ontology/graph stores and
exports, and test logs below `$DATA_DIR/integration/identity-ontology-graph/`.
- Execution path: Forecast; run entity resolution and ontology validation; build the active AGE or
relational/open-export graph; reconcile counts and sampled SQL/path parity; resolve edge evidence;
rerun unchanged and capture linkage/reasoning/projection cache hits.
Apply [Ontology design](../design/spec.md#ontology-design): additive terms only, hidden helpers,
and producer/consumer typing on sampled catalog and graph labels.
- Acceptance gates: Cluster and ontology validators pass at declared policies; graph/fallback counts
and sampled paths agree with canonical facts; every sampled edge has evidence; unchanged rerun avoids
heavy linkage and graph rebuild; failed projection never replaces the prior active version.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### review-knowledge-and-identity-integrity

Review the integrated milestone before domain projection builders.

- Serves: `identity-ontology-graph` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `build-and-validate-age-projection`;
`implement-fact-validation-conflict-and-review-overlays`;
`extract-financial-and-bookkeeping-records`; `extract-product-and-assembly-records`.
`implement-ontology-snapshots-and-geotemporal-contracts`.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
Use deterministic integration evidence and inspect provided-archive runs when available;
this verdict permits fixture implementation, not real-data or CUDA promotion.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/run artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace mention anchors versus clusters,
merge/split replay, exact fact evidence, ontology/domain
constraints including [Ontology design](../design/spec.md#ontology-design) (domain terms, hidden
helpers, additive extension, producer/consumer typing), financial/product roles, review overlays
and SQL/graph parity;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
Review dynamic ontology proposal/publish/deprecate and invalidation/replay boundaries. Verify
source-valid versus recorded time, partial dates/timezones, location/CRS uncertainty, role changes
and product revision/effectivity across facts, SQL and AGE. Distinguish party/account/transaction,
product model/revision/equipment instance and explicit assembly relations; do not expose helper types.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
An additive ontology change preserves old-snapshot answers; stale or incompatible meanings refuse;
geotemporal filters agree across engines. Same-name/shared-address entities stay separable; temporal
coincidence and amount/model similarity cannot invent domain relations or accepted facts.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

### Knowledge extraction -- `knowledge-extraction`

#### implement-provenance-bearing-fact-extraction

Extract proposed facts with deterministic patterns/table rules first and validated local structured
LLM calls for bounded high-value lanes.

- Serves: `knowledge-extraction` --
[Canonical object and fact model](../design/spec.md#canonical-object-and-fact-model)
- Agent status: RUN NEEDED
- Dependencies: `evaluate-general-and-domain-ner`;
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
`implement-probabilistic-entity-resolution`; [Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
[Canonical relational schema](records/0021-store-create-canonical-relational-schema.md).
`implement-ontology-snapshots-and-geotemporal-contracts`.
- Human review handoff:
[approve-fact-review-and-publication-policy](#approve-fact-review-and-publication-policy)
per-type outcomes, conflicts, interval/place ambiguity and proposed inclusion states.
Packet: `$RUNS_DIR/<run-id>/review/facts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: choose auto-accepted/proposed/review-required fact types and conflict treatment.
- User-visible outcome: Design/revision, assembly/component, equipment, supplier, order, shipment,
invoice, payment, date, quantity, and other relations are queryable with exact source evidence and
extraction provenance.
- Scope boundary: Insert `proposed` assertions only; no automatic truth acceptance and no ontology
axiom invention.
- Data and artifact paths: `$RESULTS_DIR/normalized/facts/`, `kg.fact`, `kg.fact_qualifier`,
`src/arxiv_int/extraction/facts/`, generated output schemas, and prompt packages.
- Execution path: Implement generic typed rule/table extractors and unresolved-object bindings; domain-specific
financial and product adapters are separate tasks; register ontology asset validation and facts
through the stage registry; define JSON-schema LLM envelopes; retrieve
bounded evidence; validate source spans,
types, units, currencies, model output, and one bounded repair; batch and checkpoint by content hash.
Reuse existing ontology predicates; do not invent equivalent terms or write disjoint types into
domain/range slots ([Ontology design](../design/spec.md#ontology-design)).
Use generated structured-output validation followed by shared Pandera batch checks; preserve
evidence/semantic validators and write proposed rows through typed SQLAlchemy/COPY adapters.
Consume the pinned ontology and shared geotemporal contracts. Preserve source-valid and recorded
time separately; keep timezone/precision/place uncertainty and raw assertion provenance. An unknown
term or ambiguous place/time remains proposed/unknown, never a newly accepted ontology axiom.
- Acceptance gates: Malformed, unsupported, uncited, and span-mismatched outputs are retained as
typed failures, not facts; per-type precision/recall and citation validity are measured; rerun is
idempotent.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### extract-financial-and-bookkeeping-records

Extract structured financial records and evidenced legal-entity/person roles before reconciliation.

- Serves: `knowledge-extraction` -- [Financial, bookkeeping, and party relationship semantics](../design/spec.md#financial-bookkeeping-and-party-relationship-semantics)
- Agent status: RUN NEEDED
- Dependencies: `implement-provenance-bearing-fact-extraction`; [Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md).
- User-visible outcome: Invoices, payments, bookkeeping postings, corrections and party roles
become typed
proposed records with exact table/cell/page evidence and scoped identifiers.
- Scope boundary: Extract source assertions and candidate links; do not equate co-occurrence with ownership,
same names with identity, an invoice with delivery, or a paid label with a bank event.
- Data and artifact paths: `src/arxiv_int/extraction/financial/`, financial contracts and fixtures,
`$RESULTS_DIR/normalized/facts/`, and `$RUNS_DIR/<run-id>/evaluation/financial/`.
- Execution path: Integrate table/document adapters for invoice and bank records, journal/ledger exports,
credit notes/reversals and contracts; preserve raw/decimal values, currency, debit/credit, dates,
formulas/cached values, role direction, and evidence; expose the lane under the registered facts stage.
Normalize tabular values with typed Polars expressions and explicit decimal/currency schemas;
reuse Pandera and existing domain rules without float arithmetic or silent coercion.
- Acceptance gates: Network-free fixtures cover same-name parties, multi-page/sheet tables,
OCR decimal errors,
negative/reversed entries, mixed currency and missing identifiers; no macros execute; per-field/type
metrics, typed failures, evidence anchors, stable ids and bounded resource usage are recorded.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### extract-product-and-assembly-records

Extract product descriptions, revisions and explicit assembly/component assertions with quantities.

- Serves: `knowledge-extraction` -- [Product, BOM, and supply-chain semantics](../design/spec.md#product-bom-and-supply-chain-semantics)
- Agent status: RUN NEEDED
- Dependencies: `implement-provenance-bearing-fact-extraction`; [Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md).
- User-visible outcome: Products, model/revision identifiers, equipment instances, components,
materials and
manufacturer claims remain distinguishable and evidence-backed.
- Scope boundary: Propose source assertions only; marketing mentions and related accessories do not imply
required components, quantities, manufacturing capability, or actual supply.
- Data and artifact paths: `src/arxiv_int/extraction/products/`, product/assembly fixtures and contracts,
`$RESULTS_DIR/normalized/facts/`, and `$RUNS_DIR/<run-id>/evaluation/products/`.
- Execution path: Parse product and assembly tables through existing extraction adapters; preserve
part number,
revision/effectivity, alternatives, quantity per parent and units; keep unknown values null;
register the bounded product lane under facts and measure against frozen examples.
Use typed Polars/PyArrow batches and shared Pandera quantity/unit/key checks; retain domain
validators for revision/effectivity and evidence semantics.
- Acceptance gates: Fixtures separate model from physical instance, explicit part-of from mention,
alternatives
from mandatory components, and incompatible revisions; citation validity and per-type/quantity
metrics pass; descriptions lacking BOM evidence yield no invented component assertions.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### implement-fact-validation-conflict-and-review-overlays

Validate facts against ontology and temporal/unit rules, group duplicates/contradictions, and expose
reversible review state.

- Serves: `knowledge-extraction` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: CLEAR
- Dependencies: `implement-provenance-bearing-fact-extraction`;
`extract-financial-and-bookkeeping-records`; `extract-product-and-assembly-records`;
[Versioned ontology assets](records/0013-contract-gov-establish-versioned-ontology-assets.md).
- Human review handoff:
[approve-fact-review-and-publication-policy](#approve-fact-review-and-publication-policy)
per-type outcomes, conflicts, interval/place ambiguity and proposed inclusion states.
Packet: `$RUNS_DIR/<run-id>/review/facts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: choose auto-accepted/proposed/review-required fact types and conflict treatment.
- User-visible outcome: Conflicting claims and uncertain facts remain visible and reviewable instead
of being silently collapsed into one value.
- Scope boundary: Validate and group; human acceptance thresholds and domain truth judgments remain
human-gated.
- Data and artifact paths: `kg.fact`, `kg.fact_conflict`, `kg.review_event`,
`$RESULTS_DIR/normalized/fact-findings/`, and `src/arxiv_int/extraction/validation/`.
- Execution path: Add domain/range, typed literal, unit, functional relation, temporal, duplicate,
contradiction, and evidence checks; create immutable decision events and reversible active views;
register `validate-facts` separately
from the upstream ontology configuration stage.
Honor producer/consumer typing: extractors may emit subclasses; validators accept the declared
domain/range or a declared superclass handler and reject disjoint types
([Ontology design](../design/spec.md#ontology-design)).
Reuse generated Pandera checks and existing ontology/domain predicates; express relational
duplicate/conflict groups and active review views as described dbt models with data tests. Keep
immutable review-event writes in typed SQLAlchemy transactions.
Reuse the ontology-stage geotemporal validators for interval, timezone, CRS/axis and uncertainty
semantics; no duplicate interpretation in extraction, SQL or graph. Pin rule/ontology snapshots in
review events and invalidate affected views on evolution while retaining historical replay.
- Acceptance gates: Synthetic and gold contradictions are found with measured precision; every
active status derives from an audit event; rejected/superseded facts retain evidence; rules are
versioned and replayable. Domain/range fixtures accept subclass instances and reject disjoint types.
Test open/partial/inverted time, unknown/invalid coordinates, conflicting location evidence and
role/revision boundary cases; as-of results distinguish source-valid from recorded time.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

#### prove-knowledge-extraction-on-provided-archive

Run fact extraction and validation on the supplied archive through an explicit integration test.

- Serves: `knowledge-extraction` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-fact-validation-conflict-and-review-overlays`;
`prove-russian-nlp-on-provided-archive`; [Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md).
- Human review handoff:
[approve-fact-review-and-publication-policy](#approve-fact-review-and-publication-policy)
final measured type thresholds, evidence and review-cost packet.
Packet: `$RUNS_DIR/<run-id>/review/facts/`.
Ready after this proof passes.
Blocked consumer:
`prove-domain-investigation-artifacts-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: choose auto-accepted/proposed/review-required fact types and conflict treatment.
- User-visible outcome: Proposed design, commercial, and general facts from supplied files are
inspectable with exact evidence, validation findings, conflicts, and extractor/model provenance.
- Scope boundary: Exercise only forecast-approved deterministic and local-model lanes; do not
auto-accept facts or claim correctness for unreviewed domain assertions.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/facts/`, knowledge tables, and test logs below
`$DATA_DIR/integration/knowledge-extraction/`.
- Execution path: Forecast; run configured fact lanes and validators; reconcile input/output/failure
counts; sample evidence-span resolution and conflict grouping; rerun unchanged and capture rule/model
cache decisions.
- Acceptance gates: Every emitted fact passes shape and evidence validation or remains a typed
failure; conflicts and review states are preserved; present-type metrics and coverage are reported;
unchanged rerun does not invoke heavy extraction; ordinary artifact manifests and checksums validate.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

### Concept graph -- `concept-graph`

#### build-concept-extraction-and-canonicalization

Operators cannot browse or constrain the corpus by the subject matter it actually discusses, because
methods, requirements, standards and failure modes are neither named entities nor topic labels.

- Serves: `concept-graph` --
[Concept extraction and canonicalization](../design/spec.md#concept-extraction-and-canonicalization)
- Agent status: RUN NEEDED
- Dependencies: `build-russian-language-morphology-and-terminology-lane`;
`implement-probabilistic-entity-resolution`;
`implement-ontology-snapshots-and-geotemporal-contracts`;
[Normalization, dedupe and chunking](records/0062-corpus-implement-normalization-dedupe-and-chunking.md);
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md).
- User-visible outcome: Inflected, abbreviated, transliterated and mixed-language mentions of one
subject term resolve to one canonical concept that carries its aliases, an extractive definition or
an explicit undefined state, counts, evidence and snapshot identities.
- Scope boundary: Produce an instance-level concept lexicon under the pinned vocabulary. Propose
unmapped terms and aliases for review; never publish an ontology class, predicate or shape, and
never add a second merging mechanism beside the identity overlay.
- Data and artifact paths: `src/arxiv_int/concepts/`, mirrored tests,
`$RESULTS_DIR/normalized/concepts/`, `kg.object`, `kg.alias`, `kg.mention`,
`configs/concepts/`, additive Alembic revisions where required, and
`$RUNS_DIR/<run-id>/concepts/`.
- Execution path: Register the `concepts` stage. Take candidates from the terminology and morphology
views first, then dictionary and designation patterns, then bounded local structured extraction over
chunks a declared selection policy admits. Build lemma-normalized head-phrase keys with e/yo and
homoglyph folding on the key only; expand versioned abbreviations and standard designations as
evidenced aliases; detect multiword expressions; language-tag Russian, Ukrainian and English surface
forms. Block and compare candidates through the existing Splink seam and cluster-version overlay
with concept-specific keys and features. Assemble definitions only from cited spans. Validate
batches with contract-derived Pandera checks and express relational concept and alias projections as
dbt models with grain, stable-key and relationship tests.
- Acceptance gates: Fixtures prove one canonical concept for inflected, abbreviated, transliterated
and mixed-script variants; separate concepts for same-string different-domain terms,
Russian/Ukrainian homographs and near-synonyms with disjoint ontology types; an undefined state
instead of an invented gloss; refusal of candidates with no resolvable evidence span; original
surface forms and offsets unchanged; automatic merges only under the approved precision policy with
uncertain pairs left separate; split restores the prior view; an unchanged rerun invokes no heavy
extraction or linkage; contract, ontology, model and policy fingerprints are recorded.
- Documentation target: `docs/impl/current/concept-graph.md`
- Review checkpoint: `review-concept-layer-integrity`.

#### extract-and-weight-concept-relations

Concepts without typed, evidence-backed relations cannot constrain retrieval, ordering, or any later
graph analysis.

- Serves: `concept-graph` -- [Concept relations](../design/spec.md#concept-relations)
- Agent status: RUN NEEDED
- Dependencies: `build-concept-extraction-and-canonicalization`;
`implement-provenance-bearing-fact-extraction`;
`implement-fact-validation-conflict-and-review-overlays`.
- User-visible outcome: Typed, directed concept-to-concept claims carry evidence spans on both
sides, a reproducible declared weight, review state, and the same citation drill-down as any other
fact.
- Scope boundary: Assert only published predicates through the existing fact store and validators.
No parallel relation table, weight store, validator or review queue, and no ontology change.
- Data and artifact paths: `src/arxiv_int/concepts/relations/`, mirrored tests, `kg.fact`,
`kg.fact_evidence`, `configs/concepts/relations/`, `$RESULTS_DIR/normalized/concept-relations/`,
and `$RUNS_DIR/<run-id>/concepts/relations/`.
- Execution path: Register the `concept-relations` stage writing into the fact contracts. Derive
candidates from pattern and structure signals first, then bounded local structured extraction with
schema-validated output. Require an evidence span from each side. Compute weight from a declared
versioned formula over calibrated confidence, independent evidence count and predicate class,
persisting the formula id with every edge. Route every claim through `validate-facts` unchanged.
- Acceptance gates: Per-predicate precision, recall and direction correctness are reported against
reviewed fixture pairs; identical inputs reproduce identical weights and the formula id is stored; a
claim without a resolvable evidence span cannot reach an accepted state; writes whose types are
disjoint from the declared domain and range are refused; bounded fixtures prove that co-occurrence,
lexical or embedding similarity, a shared abbreviation, a shared topic and a shared community each
fail to create a relation, an ordering or a prerequisite claim; a model self-reported score never
appears as the published weight.
- Documentation target: `docs/impl/current/concept-graph.md`
- Review checkpoint: `review-concept-layer-integrity`.

#### prove-concept-graph-on-provided-archive

Run concept extraction and concept relations on the supplied archive through an explicit integration
test.

- Serves: `concept-graph` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `extract-and-weight-concept-relations`;
`prove-knowledge-extraction-on-provided-archive`;
`prove-russian-nlp-on-provided-archive`.
- Human review handoff:
[approve-concept-lexicon-and-relation-policy](#approve-concept-lexicon-and-relation-policy)
sealed concept operating-point, alias, definition and relation-weight review packet.
Packet: `$RUNS_DIR/<run-id>/review/concepts/`.
Ready after this proof and its named producer inputs pass.
Blocked consumer:
`prove-graph-analytics-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept or revise the concept merge thresholds, alias and definition policy, admitted
predicates and weight formula, or retain the branch unselected.
- User-visible outcome: Supplied-archive concepts, aliases, definitions, unmapped proposals and
typed relations are inspectable with evidence, review state and measured per-predicate summaries.
- Scope boundary: Prove the configured concept profiles on available archive languages and types. Do
not treat unreviewed concepts or relations as accepted, publish an ontology change, or infer quality
for strata the archive does not contain.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/{concepts,concept-relations}/`, concept and fact tables, and test logs
below `$DATA_DIR/integration/concept-graph/`.
- Execution path: Forecast the closure; run `concepts` and `concept-relations`; validate schemas,
evidence resolution, alias and definition states, unmapped counts, per-predicate summaries, weight
reproducibility and model fingerprints; rerun unchanged and record extraction and linkage cache
hits; assemble the human review packet with positive, negative and ambiguous samples.
- Acceptance gates: Every published concept and relation resolves to a source span; undefined and
unmapped states are counted rather than filled; declared metrics are reported by present stratum;
the identical rerun performs no heavy extraction, adjudication or linkage; incomplete evidence keeps
the task open. Only ordinary pipeline artifacts stay under configured roots; nothing source-derived
is committed or staged for commit. Record the run id, artifact roots, manifests, and checksums
checked in place.
- Documentation target: `docs/impl/current/concept-graph.md`
- Review checkpoint: `review-concept-layer-integrity`.

#### review-concept-layer-integrity

Review the concept layer before any graph analysis consumes it.

- Serves: `concept-graph` --
[Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `extract-and-weight-concept-relations`;
`prove-concept-graph-on-provided-archive`.
- User-visible outcome: An evidence-based checkpoint decides proceed,
proceed-with-nonblocking-notes, or blocked for the named consumers; no-refactoring-needed is a valid
result.
- Scope boundary: Review the named producers, their cross-module invariants and routed notes only.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this stage
is in scope; concluding that existing tests already cover them is valid. No speculative rewrite,
model upgrade, ontology change or numeric coverage floor.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state
pages, existing test and run artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read the full task snapshots and source changes. Verify that concepts are
instances and never ontology axioms, that merging goes through the single identity overlay, that
concept relations use the shared fact contracts and validators, that morphological key folding never
alters stored surface forms or offsets, that definitions stay extractive, that declared weights are
reproducible, and that the non-implication fixtures hold. Replay representative existing tests and
validators; add tests for important stabilized cases the stage still misses; reconcile every routed
note with evidence, severity, affected consumers and one disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition; the
listed invariants are verified and `make ci` passes. Any blocking finding gets a focused
prerequisite repair task and keeps this checkpoint open until it passes; valid negative results and
nonblocking follow-ups are recorded without claiming a wider audit.
- Documentation target: `docs/impl/current/concept-graph.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task
ids.

### Graph analytics -- `graph-analytics`

#### implement-two-pass-distant-link-refinder

A chunk-local extractor never proposes relations whose two halves sit in different silos, so a large
corpus loses exactly the long-range structure an investigation needs.

- Serves: `graph-analytics` --
[Two-pass distant-link discovery](../design/spec.md#two-pass-distant-link-discovery)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `review-concept-layer-integrity`;
[ParadeDB lexical load and query path](records/0070-lexical-build-paradedb-lexical-load-and-query-path.md);
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md).
Use `implement-selective-embedding-pipeline` only when the semantic branch is selected; the lexical
and alias candidate generator is the unconditional baseline.
- User-visible outcome: Concept pairs that no single chunk states are proposed, adjudicated with
evidence from both sides, and either recorded as proposed relations with their candidate provenance
or retained as explicit no-relation and abstention verdicts.
- Scope boundary: Register the `refinder` stage over existing retrieval projections. Add no vector
service, no second index store and no accepted edge. Do not exceed the declared budgets or judge a
pair twice.
- Data and artifact paths: `src/arxiv_int/graph_analytics/refinder/`, mirrored tests,
`configs/graph-analytics/refinder/`, `kg.fact`, `kg.fact_evidence`,
`$RESULTS_DIR/normalized/refinder/`, and `$RUNS_DIR/<run-id>/graph-analytics/refinder/`.
- Execution path: Select the concept tier from importance, bridge candidacy, cross-partition spread
and under-connection. Run the forward pass through the declared candidate generator, then the
backward pass that confirms reciprocal membership, adjudicating reciprocal candidates first and
one-directional candidates only inside the residual budget. Adjudicate with bounded schema-validated
local inference that must cite a span from each side and may return a published predicate,
no-relation or abstention. Write accepted verdicts as proposed relations carrying the extractor
identity, generator id, both ranks and both spans, through the shared fact validators. Persist every
verdict, the deterministic candidate order and resumable budget counters. Build the planted-link and
distractor fixtures and the forward-only ablation.
- Acceptance gates: Planted long-range links whose surface forms differ by inflection, abbreviation,
transliteration and language are recovered at the declared budget; judged-edge precision and the
distractor false-link rate meet their predeclared thresholds; withheld evidence produces abstention
rather than a relation; an identical rerun re-judges nothing and reproduces the identical verdict
set; an interrupted run resumes without exceeding the declared per-concept and corpus budgets and an
exhausted budget reports its coverage denominator; the two-pass and forward-only ablations are
compared; prompt-injection fixtures prove document text cannot direct the adjudicator; refinder
edges remain separable from other edges. A predeclared adopt, retain-baseline or inconclusive rule
is applied to the held-out link-recall gate, and retaining the baseline is a valid recorded result.
- Documentation target: `docs/impl/current/graph-analytics.md`
- Review checkpoint: `review-graph-analytics-integrity`.

#### implement-graph-community-detection

A concept graph of any useful size is unreadable without thematic modules and without knowing which
concepts hold those modules together.

- Serves: `graph-analytics` -- [Communities and bridges](../design/spec.md#communities-and-bridges)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `review-concept-layer-integrity`;
[Rebuildable search and graph projections](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
Include `implement-two-pass-distant-link-refinder` edges only when that branch is selected.
- User-visible outcome: The concept graph exposes a versioned partition with its algorithm,
resolution, seed, modularity, multi-seed agreement, bridge concepts, and an explicit unstable or
low-confidence verdict when the structure does not hold.
- Scope boundary: Register the `graph-communities` stage as a rebuildable CPU projection over
contracted edge tables. Communities are not ontology classes and not topics, and they never merge
with or rename topic ids. No graph-algorithm execution inside AGE and no new database extension.
- Data and artifact paths: `src/arxiv_int/graph_analytics/communities/`, mirrored tests,
`configs/graph-analytics/communities/`, `ctl.projection`, community projection tables, additive
Alembic revisions where required, `$RESULTS_DIR/normalized/communities/`, and
`$RUNS_DIR/<run-id>/graph-analytics/communities/`.
- Execution path: Export contracted edges with declared weights, run the Louvain baseline behind a
narrow adapter with a fixed seed and deterministic node order, and compare the Leiden candidate on
the same inputs. Repeat across declared seeds and orders and compute agreement. Compute bridge
concepts from participation across communities and bounded betweenness on the reduced graph. Publish
modularity, the resolution sweep, proposed and refinder edge shares, singleton and giant-component
shares, and the stability verdict. Switch the active community pointer only after validation.
Express relational community and bridge projections as dbt models with grain and relationship tests.
- Acceptance gates: Planted-partition fixtures with known ground truth meet the declared agreement
floor; identical inputs, seed and node order reproduce an identical partition; input row order
changes nothing; an empty graph, an edgeless graph, one clique, a star hub, disconnected components,
self-loops and duplicate edges each produce an explicit recorded result rather than a failure; a
partition below the agreement threshold publishes as unstable with its disagreement evidence; an
edge set dominated by proposed edges publishes as low-confidence; the resolution limit and sweep are
reported; a failed build leaves the prior community version active; a predeclared Louvain-versus-Leiden
adopt, retain or inconclusive rule is applied.
- Documentation target: `docs/impl/current/graph-analytics.md`
- Review checkpoint: `review-graph-analytics-integrity`.

#### implement-graph-topology-and-effort-metrics

Operators and later stages have no declared way to order what to read first or which concepts carry
the deepest prerequisite chains.

- Serves: `graph-analytics` --
[Topology and effort metrics](../design/spec.md#topology-and-effort-metrics)
- Agent status: CLEAR
- Dependencies: `implement-graph-community-detection`.
- User-visible outcome: Each concept exposes a weighted importance rank with its stability, a
dependency depth measured on the condensed prerequisite graph, an effort score with its published
formula and sensitivity, and every prerequisite cycle as a named data-quality finding.
- Scope boundary: Register the `graph-metrics` stage as a rebuildable projection. Metrics order
browsing and select work tiers only; they never rank analyst findings, establish that a claim is
true, or mix accepted and proposed edge variants in one number.
- Data and artifact paths: `src/arxiv_int/graph_analytics/metrics/`, mirrored tests,
`configs/graph-analytics/metrics/`, metric projection tables, additive Alembic revisions where
required, `$RESULTS_DIR/normalized/graph-metrics/`, and
`$RUNS_DIR/<run-id>/graph-analytics/metrics/`.
- Execution path: Compute weighted importance with declared damping, weight normalization,
convergence tolerance and dangling-node policy over accepted edges, and publish the proposed-edge
variant under its own label. Extract the prerequisite subgraph, condense strongly connected
components, measure depth on the condensation, and emit every cycle with its member concepts and
evidence. Compute the declared effort composite and its sensitivity report. Persist the metric
profile id, formula ids and consumed snapshot ids, and bind them into reuse keys.
- Acceptance gates: Closed-form fixtures match a reference importance implementation on small
graphs; depth fixtures cover hand-built acyclic graphs, cycles, self-loops, disconnected components
and sink and dangling nodes; every planted cycle is reported as a finding and no depth is claimed
across an unreported cycle; ranks are deterministic for identical inputs and rank stability under
the declared perturbation is published; a formula or damping change creates a new metric profile id
rather than changing published values in place; a metrics run refuses to activate against a
mismatched community, identity, fact or ontology snapshot; report fixtures prove metrics cannot
reorder findings.
- Documentation target: `docs/impl/current/graph-analytics.md`
- Review checkpoint: `review-graph-analytics-integrity`.

#### prove-graph-analytics-on-provided-archive

Run distant-link discovery, community detection and topology metrics on the supplied archive through
an explicit integration test.

- Serves: `graph-analytics` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-graph-topology-and-effort-metrics`;
`prove-concept-graph-on-provided-archive`;
`prove-identity-ontology-graph-on-provided-archive`;
`approve-concept-lexicon-and-relation-policy`.
- Human review handoff:
[approve-graph-analytics-operating-points](#approve-graph-analytics-operating-points)
sealed refinder budget and gate result, community stability and resolution evidence, and metric
formula packet.
Packet: `$RUNS_DIR/<run-id>/review/graph-analytics/`.
Ready after this proof and its named producer inputs pass.
Blocked consumer:
`prove-graph-constrained-agents-on-provided-archive`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept or revise the refinder budgets and adjudication policy, the community algorithm and
resolution, and the metric and effort formulas, or retain a measured not-selected verdict.
- User-visible outcome: Real archive long-range candidates, verdicts, partitions, stability figures,
bridge concepts, ranks, depths, cycles and costs are inspectable with their snapshot identities, or
the not-selected verdict names the working baseline.
- Scope boundary: Use only forecast-approved budgets and configured local models. Do not judge the
whole pair space, publish an unstable partition as thematic structure, or treat a failed or
unavailable branch as successful proof.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/{refinder,communities,graph-metrics}/`, projection manifests, and test logs
below `$DATA_DIR/integration/graph-analytics/`.
- Execution path: Forecast adjudication and computation resources; run the selected refinder,
community and metric profiles; validate verdict and partition identities, counts, evidence
resolution for every sampled edge, agreement and sensitivity figures, cycle findings, and with- and
without-refinder comparisons; rerun unchanged and record that adjudication and partition computation
are reused; assemble the human review packet.
- Acceptance gates: Every sampled proposed edge resolves to spans on both sides; the partition
publishes its agreement, resolution sweep and proposed-edge share; metrics name their consumed
snapshots; the identical rerun performs no adjudication and no partition recomputation; declared
budgets are never exceeded and an exhausted budget reports its denominator; a not-selected verdict is
valid only with the declared measured negative result and a verified baseline without these edges;
other failures keep the task open. Only ordinary pipeline artifacts stay under configured roots;
nothing source-derived is committed or staged for commit. Record the run id, artifact roots,
manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/graph-analytics.md`
- Review checkpoint: `review-graph-analytics-integrity`.

#### review-graph-analytics-integrity

Review the graph analysis milestone before a context builder or diagnostic consumes it.

- Serves: `graph-analytics` --
[Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `implement-graph-topology-and-effort-metrics`;
`prove-graph-analytics-on-provided-archive`.
- User-visible outcome: An evidence-based checkpoint decides proceed,
proceed-with-nonblocking-notes, or blocked for the named consumers; no-refactoring-needed is a valid
result.
- Scope boundary: Review the named producers, their cross-module invariants and routed notes only.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this stage
is in scope; concluding that existing tests already cover them is valid. No speculative rewrite,
algorithm swap outside the declared comparison, or numeric coverage floor.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state
pages, existing test and run artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read the full task snapshots and source changes. Verify that no refinder edge is
written as accepted, that budgets and candidate ordering are deterministic and resumable, that
partitions are seeded and reproducible with a published stability verdict, that communities never
merge with topic ids or become graph labels, that depth is only claimed on a condensed acyclic graph
with cycles reported, that accepted and proposed metric variants stay separate, and that no metric
reorders findings. Replay representative existing tests and validators; add tests for important
stabilized cases the stage still misses; reconcile every routed note with evidence, severity,
affected consumers and one disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition; the
listed invariants are verified and `make ci` passes. Any blocking finding gets a focused
prerequisite repair task and keeps this checkpoint open until it passes; valid negative results and
nonblocking follow-ups are recorded without claiming a wider audit.
- Documentation target: `docs/impl/current/graph-analytics.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task
ids.

### Domain investigation artifacts -- `domain-investigation-artifacts`

#### build-party-and-transaction-artifacts

Project party relationships and financial events into cited relationship and invoice/payment tables
and bounded graphs.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: [Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
`implement-fact-validation-conflict-and-review-overlays`; `implement-probabilistic-entity-resolution`.
`review-knowledge-and-identity-integrity`.
- Human review handoff:
[approve-domain-artifact-semantics-and-inclusion](#approve-domain-artifact-semantics-and-inclusion)
family semantics, graph/table reconciliation, valid-empty/conflict and inclusion examples.
Packet: `$RUNS_DIR/<run-id>/review/domain-artifacts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve per-family semantics/inclusion, or retain partial/review-only/disabled families.
- User-visible outcome: Analysts can trace directed legal-entity/person roles, financial events,
invoice balances
and payment allocation candidates to their source evidence.
- Scope boundary: Generate bounded derived views from selected review states; do not silently
promote proposed facts, reconcile currencies without a sourced rate, or claim completeness beyond
reported evidence coverage.
- Data and artifact paths: `$RESULTS_DIR/normalized/domain-artifacts/`,
`src/arxiv_int/domain_artifacts/`, `$RUNS_DIR/<run-id>/artifacts/`, reviewed domain fixtures, and
snapshot/render tests.
- Execution path: Project canonical participants/roles relationally; calculate decimal invoice
totals and
many-to-many allocations with currency, tolerance, credit/reversal and time constraints; distinguish
matched, partial, overallocated, disputed, duplicate and unmatched states; render bounded graphs
from the same tables without requiring AGE.
Put reconciliation joins, allocations, balances and party views in named dbt models with grain,
decimal/currency definitions, source/ref dependencies and domain data tests; use typed Polars for
local export preparation and shared quality checks before publishing.
- Acceptance gates: Frozen positive/negative fixtures prove party direction, no inferred ownership
from payment,
no over-allocation silently accepted, partial/reversed/multi-invoice payments, source arithmetic,
uncertainty, exact evidence and graph/table parity. Empty requires processed eligible inputs;
unsupported or failed extraction remains partial/failed. Archive proof is separate from fixtures.
Party roles use asserted validity and the pinned ontology/identity snapshot; shared addresses,
nearby dates and equal amounts cannot establish identity, delivery or settlement without evidence.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### build-product-bom-and-supply-chain-artifacts

Build revision-aware BOM hierarchies and evidence-scoped supply-chain analysis from product facts.

- Serves: `domain-investigation-artifacts` -- [Product, BOM, and supply-chain semantics](../design/spec.md#product-bom-and-supply-chain-semantics)
- Agent status: RUN NEEDED
- Dependencies: `implement-fact-validation-conflict-and-review-overlays`;
[Domain investigation contracts](records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
`implement-probabilistic-entity-resolution`.
`review-knowledge-and-identity-integrity`.
- Human review handoff:
[approve-domain-artifact-semantics-and-inclusion](#approve-domain-artifact-semantics-and-inclusion)
family semantics, graph/table reconciliation, valid-empty/conflict and inclusion examples.
Packet: `$RUNS_DIR/<run-id>/review/domain-artifacts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve per-family semantics/inclusion, or retain partial/review-only/disabled families.
- User-visible outcome: An analyst can inspect assemblies, cumulative component requirements when justified,
supplier/customer paths and concentration within a stated product/time scope.
- Scope boundary: Use only explicit component and commercial-stage evidence; do not complete
missing BOMs
or infer actual shipment from a catalog or quote. AGE is not required.
- Data and artifact paths: `src/arxiv_int/domain_artifacts/products/`, BOM/supply fixtures,
`$RESULTS_DIR/normalized/domain-artifacts/`, and `$RUNS_DIR/<run-id>/artifacts/`.
- Execution path: Build typed part-of edges and parent quantities; detect cycles and separate
alternatives and
revision/effectivity; derive rollups only with compatible units and retain operands; project quoted,
ordered, invoiced, shipped, received and paid stages; calculate concentration with denominators.
Use described dbt models for relational BOM/supply projections and aggregation, with explicit
unit/revision grain and cycle/rollup tests. Keep traversal algorithms in focused typed Python where
needed; validate export batches through Pandera and reuse existing domain rules.
- Acceptance gates: Fixtures cover repeated components, multi-level rollups, cycles, unknown
quantities, mixed
units, alternatives, conflicting revisions and incomplete supplier coverage; tables/graphs match,
derivations resolve, outputs are bounded and repeatable; marketing-only descriptions allow empty BOM.
Pin ontology, identity and revision/effectivity scope; cross-revision components and temporally
incompatible supplier roles remain conflicts/unknown. Mention, co-location and marketing similarity
never imply assembly membership or actual supply.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### register-and-expose-domain-artifacts

Publish all domain artifacts through an atomic per-run registry and expose discovery links without
creating another source of truth.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: CLEAR
- Dependencies: `build-party-and-transaction-artifacts`;
`build-product-bom-and-supply-chain-artifacts`; [Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md).
- Human review handoff:
[approve-domain-artifact-semantics-and-inclusion](#approve-domain-artifact-semantics-and-inclusion)
family semantics, graph/table reconciliation, valid-empty/conflict and inclusion examples.
Packet: `$RUNS_DIR/<run-id>/review/domain-artifacts/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve per-family semantics/inclusion, or retain partial/review-only/disabled families.
- User-visible outcome: Every run reaching the domain-artifact stage lists which special artifacts
were produced, partial, empty, or failed and provides a verified local path plus evidence/coverage
summary for each.
- Scope boundary: Register immutable outputs and read-only links; do not mark failed output
successful, embed unrestricted source text, or let dashboards become the canonical registry.
- Data and artifact paths: `ctl.artifact`, additive `src/arxiv_int/migrations/versions/`,
`$RUNS_DIR/<run-id>/artifacts/registry.{json,parquet}`, `src/arxiv_int/reporting/artifacts/`, CLI/API
responses, and registry contract tests.
- Execution path: Generate and apply additive artifact-registry Alembic Python revisions; assign
stable artifact ids; capture type/schema/generator/input/policy fingerprints, paths, media types,
checksums, counts, evidence coverage, status, and failure reason; validate output before one atomic registry
publication; add `run artifacts` listing and report links.
Use contract-derived Alembic Python revisions and typed SQLAlchemy registry transactions; bind
model lineage and shared quality evidence to each artifact fingerprint before publication.
- Acceptance gates: Contract fixtures cover produced/partial/empty/failed states; every successful
row resolves to checksum-valid files and source evidence; missing or corrupt output prevents
publication; unchanged reruns reuse ids; CLI/API and manifest/SQL registries agree.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### prove-domain-investigation-artifacts-on-provided-archive

Generate every applicable relationship, BOM, supply-chain, and invoice/payment artifact family from
the supplied archive through an explicit integration test.

- Serves: `domain-investigation-artifacts` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `register-and-expose-domain-artifacts`;
`prove-identity-ontology-graph-on-provided-archive`.
`review-domain-artifact-and-triage-boundaries`; `approve-entity-merge-and-ontology-policy`;
`approve-fact-review-and-publication-policy`.
- Human review handoff:
[approve-domain-artifact-semantics-and-inclusion](#approve-domain-artifact-semantics-and-inclusion)
sealed per-family metrics and decision packet.
Packet: `$RUNS_DIR/<run-id>/review/domain-artifacts/`.
Ready after this proof and its required fact/ontology decisions pass.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: approve per-family semantics/inclusion, or retain partial/review-only/disabled families.
- User-visible outcome: The run artifact registry exposes each applicable supplied-archive domain
view, its table/graph files, evidence coverage, conflicts, review policy, and production status.
- Scope boundary: Generate only evidence-supported bounded views; accept contract-valid `empty` or
`partial` families and never manufacture relations to make a graphical artifact non-empty.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/domain-artifacts/`, and test logs below
`$DATA_DIR/integration/domain-investigation-artifacts/`.
- Execution path: Forecast; build all configured artifact families; validate arithmetic,
table-to-graph parity, source links, renders, registry rows, and checksums; rerun unchanged and record
projection/render cache hits.
- Acceptance gates: Every configured family is honestly `produced`, `partial`, or `empty` with a
valid reason; no failed output is registered as successful; evidence and policy resolve for every
element; identical rerun performs no heavy extraction, projection, or rendering.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Anomaly analysis -- `anomaly-analysis`

#### implement-explainable-anomaly-detectors

Create deterministic constraint and bounded statistical detectors with evidence and cohort guards.

- Serves: `anomaly-analysis` -- [Anomaly detection and triage](../design/spec.md#anomaly-detection-and-triage)
- Agent status: CLEAR
- Dependencies: `register-and-expose-domain-artifacts`; [Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
- Human review handoff:
[approve-anomaly-triage-policy](#approve-anomaly-triage-policy)
detector coverage, hard negatives, review replay and proposed budgets.
Packet: `$RUNS_DIR/<run-id>/review/anomalies/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: enable, retain constraints only, revise or disable each detector and its review budget.
- User-visible outcome: Analysts receive explainable data, financial, relationship/supply-chain
and BOM findings
with observed versus expected values and coverage limits.
- Scope boundary: No fraud verdicts, hidden identity merges, source edits or ML training;
unsupported cohorts
produce insufficient-evidence and a detector may yield no useful findings.
- Data and artifact paths: `src/arxiv_int/analytics/`, `configs/anomalies/`, finding contracts,
`$RESULTS_DIR/normalized/anomalies/`, and deterministic positive/negative fixtures.
- Execution path: Generate finding schemas and register anomalies; implement constraints, comparable-currency
amount cohorts, duplicate/unmatched candidates, graph concentration/cycles and BOM consistency;
retain rule/version, operands, source ids, denominator, time window, sample floor and rank rationale.
Define relational cohorts and deterministic aggregate rules in described dbt models; use
Polars expressions for local batch calculations. Reuse Pandera/domain checks for input validity,
and distinguish expected detector findings from data-quality failures.
- Acceptance gates: Fixtures prove exact expected flags and hard negatives, decimal/unit
correctness, minimum
cohort and temporal-leakage guards, source/derivation validity, deterministic grouping, and bounded
memory; per-detector accuracy and review-budget metrics use predeclared thresholds.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### implement-anomaly-review-and-triage-exports

Publish findings, reversible review events and bounded explanation views for analyst triage.

- Serves: `anomaly-analysis` -- [Anomaly detection and triage](../design/spec.md#anomaly-detection-and-triage)
- Agent status: CLEAR
- Dependencies: `implement-explainable-anomaly-detectors`;
[Incremental reconciliation and stale pruning](records/0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md).
- Human review handoff:
[approve-anomaly-triage-policy](#approve-anomaly-triage-policy)
detector coverage, hard negatives, review replay and proposed budgets.
Packet: `$RUNS_DIR/<run-id>/review/anomalies/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: enable, retain constraints only, revise or disable each detector and its review budget.
- User-visible outcome: Analysts can filter and inspect flags, see why each ranked, and record explained/dismissed
outcomes without changing evidence.
- Scope boundary: Reuse canonical review/artifact interfaces; no new truth store, autonomous accusations,
implicit feedback training, or unrestricted graph queries.
- Data and artifact paths: `src/arxiv_int/analytics/`, `kg.review_event`, registry contracts,
`$RUNS_DIR/<run-id>/artifacts/anomalies/`, and review/export fixtures.
- Execution path: Expose anomalies list/show and explicit review operations; publish JSON/Parquet, comparison
tables and bounded subgraphs; preserve stable finding groups and review reasons across reruns;
invalidate computations after source, identity, policy or cohort changes.
Keep triage projections in tested dbt models, review writes in typed SQLAlchemy transactions,
and export batch validation in the shared Pandera adapter.
- Acceptance gates: Review replay and undo retain source facts; stale findings are labelled and recomputed;
rank/filter definitions and skipped/insufficient counts are present; empty outputs validate; exports
and canonical counts agree; changed evidence cannot inherit a misleading resolved state.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: `review-domain-artifact-and-triage-boundaries`.

#### review-domain-artifact-and-triage-boundaries

Review domain semantics, registry publication and triage accounting before report integration.

- Serves: `anomaly-analysis` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `review-knowledge-and-identity-integrity`; `register-and-expose-domain-artifacts`;
`implement-explainable-anomaly-detectors`; `implement-anomaly-review-and-triage-exports`.
- User-visible outcome:
Reports and human packets inherit consistent evidenced domain relations and honest anomaly states.
- Scope boundary:
Review fixtures and existing producer evidence; do not accept domain policies, certify financial
truth, or require nonempty anomaly findings. Archive proofs and human judgments remain separate.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace party/account roles, product model/revision/instance, BOM alternatives/units/effectivity,
invoice arithmetic and payment allocation against exact fact evidence. Check pinned ontology and
geotemporal joins, registry/graph/table parity, triage denominators and review replay after changes.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
No mention or similarity becomes part-of/supplier/paid; wrong revision/time joins fail; empty,
partial and conflicted outputs retain meaning. Missing evidence or failed validation blocks
publication; no unsupported anomaly allegation appears. Candidate review packets reconcile to data.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: none; this is the bounded checkpoint.

#### prove-anomaly-analysis-on-provided-archive

Run configured detectors on the provided archive and publish honest quality and review-cost evidence.

- Serves: `anomaly-analysis` -- [Anomaly detection and triage](../design/spec.md#anomaly-detection-and-triage)
- Agent status: RUN NEEDED
- Dependencies: `implement-anomaly-review-and-triage-exports`;
`prove-domain-investigation-artifacts-on-provided-archive`;
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md).
`review-domain-artifact-and-triage-boundaries`.
- Human review handoff:
[approve-anomaly-triage-policy](#approve-anomaly-triage-policy)
sealed enable/constraints-only/revise/disable packet.
Packet: `$RUNS_DIR/<run-id>/review/anomalies/`.
Ready after this proof passes.
Blocked consumer:
`accept-operator-discovery-workflows`
and `publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: enable, retain constraints only, revise or disable each detector and its review budget.
- User-visible outcome: The archive has cited anomaly candidates, or an explicit no-findings/insufficient-data
result, with per-detector coverage and an interpretable review workload.
- Scope boundary: No claims of wrongdoing or anomaly-free data; only bounded authorized source
scope and
predeclared final evaluation, without tuning on the final split.
- Data and artifact paths: Frozen detector profiles, review labels, normal finding artifacts, and
test logs below `$DATA_DIR/integration/anomaly-analysis/`.
- Execution path: Forecast; run constraints and eligible cohort detectors; verify citations and input
snapshots; score per-detector precision/recall and precision at review budget; rerun unchanged
and capture cache hits, time and memory; report retain-constraints or not-selected where justified.
- Acceptance gates: Every detector has evaluated/skipped/insufficient counts and a replayable
verdict; hard
negatives, cohort leakage and review burden are reported; findings/empty outputs validate; no
heavy work on the identical rerun and no private source content in repository summaries.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Discovery and visualization -- `discovery-visualization`

#### implement-scalable-topic-discovery

Build CPU-first topic discovery and drift tracking with an optional bounded embedding-based lane.

- Serves: `discovery-visualization` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: [Normalization, dedupe and chunking](records/0062-corpus-implement-normalization-dedupe-and-chunking.md);
`build-russian-language-morphology-and-terminology-lane`; optional
`implement-selective-embedding-pipeline` for the embedding lane.
- User-visible outcome: The archive exposes stable topics, representative documents, terms,
hierarchy candidates, and change across partitions/time.
- Scope boundary: Topic labels are proposals and sampling is explicit; do not run BERTopic/HDBSCAN
over all chunks without a bounded design.
- Data and artifact paths: `$RESULTS_DIR/normalized/topics/`, `search.topic`, `search.topic_assignment`,
`configs/topics/`, and `$RUNS_DIR/<run-id>/evaluation/topics/`.
- Execution path: Compare TF-IDF/NMF and MiniBatchKMeans on stratified samples or document
centroids; optionally compare embedding clustering; persist centroids/terms/representatives; align
versions and measure drift/stability.
- Acceptance gates: Stability, coherence proxy, coverage, outlier rate, runtime, and expert sample
review are reported; repeated seeded run is reproducible within tolerance; topic ids are
versioned.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### build-company-product-and-person-catalogs

Produce the three required entity catalogs and related equipment/supplier views from pinned snapshots.

- Serves: `discovery-visualization` -- [Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: CLEAR
- Dependencies: `implement-probabilistic-entity-resolution`; `implement-fact-validation-conflict-and-review-overlays`;
`implement-scalable-topic-discovery`.
- User-visible outcome: Company, product and person lists expose identifiers, aliases, roles,
evidence counts,
unresolved identities and time-qualified relation drill-down.
- Scope boundary: Catalog views do not create new identities or infer legal form, ownership
or actual supply.
Keep organization/person, product/model/revision, and equipment instances distinct.
- Data and artifact paths: `src/arxiv_int/query/catalogs/`, catalog contracts, `$RESULTS_DIR/normalized/catalogs/`,
and `$RUNS_DIR/<run-id>/artifacts/catalogs/`.
- Execution path: Register catalogs and catalog company/product/person; implement filtered/paginated
CSV/Parquet/JSON exports and bounded relation/evidence views; publish one registry entry per required
catalog including empty states, snapshot fingerprints, coverage and review inclusion policy.
Build catalog relations as named dbt models with documented grain, source/ref, inclusion policy,
stable keys and relationship/count tests. Typed query adapters handle pagination and export;
Pandera validates exported batches against the same contracts.
- Acceptance gates: Fixtures prove role versus entity distinctions, same-name nonmatches,
aliases and identifiers,
source/identity merge-split/removal updates, counts against canonical views, complete citations,
empty categories and bounded query/export behavior.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### build-search-graph-and-report-interfaces

Expose bounded lexical/semantic/hybrid search, object/fact lookup, Cypher or SQL traversal, and
company/product/person catalogs and the analyst entry report through CLI and a small local API.

- Serves: `discovery-visualization` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: [Russian lexical calibration second opinion](records/0072-lexical-review-and-deepen-russian-lexical-calibration.md);
`build-and-validate-age-projection`;
`register-and-expose-domain-artifacts`; `build-company-product-and-person-catalogs`;
`implement-anomaly-review-and-triage-exports`;
[Investigation profile and output manifest](records/0045-pipeline-implement-investigation-profile-and-output-manifest.md).
[Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md).
`review-domain-artifact-and-triage-boundaries`.
- Human review handoff:
[accept-operator-discovery-workflows](#accept-operator-discovery-workflows)
scenario instructions, entry points and evidence/state drill-down examples.
Packet: `$RUNS_DIR/<run-id>/acceptance/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept the cited investigation scenarios or record blocking usability/domain failures.
- User-visible outcome: An operator can find evidence, inspect objects and facts, traverse
relations, open the portable `reports/index.html`, see important supported findings and coverage, and
drill through catalogs, anomalies, BOM, supply-chain, invoice/payment and relation graphs to source
cells/pages without writing SQL or running viewer services.
- Scope boundary: Read-only query/report boundary with limits; no public multi-user web product and
no hidden acceptance of proposed facts.
- Data and artifact paths: `src/arxiv_int/query/`, `src/arxiv_int/reporting/`,
`$RUNS_DIR/<run-id>/reports/`, and API/query tests.
- Execution path: Add typed query objects, pagination, filters, review-state controls, evidence
expansion, escaped source snippets, deterministic summary/rank definitions, no-evidence/partial
report sections, per-document content overviews with extractive snippets and section/table pointers,
CSV/Parquet/HTML exports, and explain modes; register the `report`
stage body behind `arxiv-int report build RUN_ID` and `search lexical|semantic|hybrid`; constrain
text/depth/result/time.
Consume dbt-tested report/catalog marts and retained quality/lineage artifacts; use bound
SQLAlchemy query expressions for filters and pagination, reviewed SQL/Cypher assets for engine
queries, and Polars/PyArrow with Pandera for bounded exports. No report business transformations
are embedded in Python strings or dashboard query text.
- Acceptance gates: Scenario fixtures return complete citations and declared inclusion rules; SQL
injection and path tests pass; large/unbounded requests are refused; exports conform to generated
contracts; report manifest and pinned canonical snapshots agree; source snippets cannot execute
HTML/scripts or direct model/tool actions; portable report works without Grafana/AGE Viewer.
Time/place filters expose uncertainty and source-valid versus recorded scope; ontology/identity
snapshots are visible. Domain labels and same-name entities remain distinct across catalogs,
graphs, tables and source drill-down.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### provision-local-dashboards-and-age-viewer

Provision Grafana dashboards and the optional AGE Viewer profile without adding another canonical
store.

- Serves: `discovery-visualization` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Dependencies: `build-search-graph-and-report-interfaces`; Compose profiles documented in
[Portable runtime](current/portable-runtime.md).
- Human review handoff:
[accept-operator-discovery-workflows](#accept-operator-discovery-workflows)
scenario instructions, entry points and evidence/state drill-down examples.
Packet: `$RUNS_DIR/<run-id>/acceptance/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept the cited investigation scenarios or record blocking usability/domain failures.
- User-visible outcome: Local dashboards show pipeline progress, topics, entities, facts, conflicts,
and bounded graph views; AGE Viewer supports exploratory Cypher when enabled.
- Scope boundary: Provision read-only local tools; no internet exposure, corpus-bearing telemetry
export, or tool-owned source of truth.
- Data and artifact paths: `docker/grafana/`, `docker/age-viewer/`, Compose profiles, read-only
database role migrations, `$SERVICE_STATE_DIR/<service>/` for mutable service state, and
screenshot/query smoke fixtures.
- Execution path: Provision PostgreSQL datasource and dashboards as code from the repository, keep
only mutable service state under `SERVICE_STATE_DIR`; create read-only views; configure AGE Viewer;
document loopback URLs and lifecycle; add health and bounded-query smoke tests.
Read described dbt marts through bounded parameterized dashboard queries; keep metric
transformations in dbt models and provision role changes through Alembic Python revisions.
- Acceptance gates: Fresh profile start needs no manual datasource setup; read-only roles cannot
mutate canonical rows; dashboards load fixture data; deleting `SERVICE_STATE_DIR` loses no
provisioned definition; graph profile absence degrades cleanly.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### prove-discovery-and-visualization-on-provided-archive

Run topic discovery, search/report scenarios, exports, and configured local views against supplied
archive artifacts through an explicit integration test.

- Serves: `discovery-visualization` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `build-search-graph-and-report-interfaces`;
`prove-domain-investigation-artifacts-on-provided-archive`;
`prove-anomaly-analysis-on-provided-archive`;
[Lexical retrieval provided-archive integration](records/0073-lexical-prove-lexical-retrieval-on-provided-archive.md).
Viewer smoke is conditional on selecting that profile.
- Human review handoff:
[accept-operator-discovery-workflows](#accept-operator-discovery-workflows)
executable scenario packet, results and issue ledger.
Packet: `$RUNS_DIR/<run-id>/acceptance/`.
Ready after this proof and the listed policy decisions; name any still pending.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept the cited investigation scenarios or record blocking usability/domain failures.
- User-visible outcome: Operators can navigate supplied-archive topics, searches, objects, facts,
graphs, and domain reports through bounded interfaces whose displayed evidence can be verified.
- Scope boundary: Prove local read-only scenarios and available profiles; do not expose services
publicly, require an optional UI/AGE profile with a valid fallback, or claim usability acceptance for
scenarios not executed.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
topic/query/report/export artifacts, and test logs below
`$DATA_DIR/integration/discovery-visualization/`.
- Execution path: Forecast; run topics, company/product/person catalogs, anomaly views and
entry report generation; execute scripted lexical and available
hybrid, object/fact, graph, BOM, supply-chain, and invoice/payment scenarios; validate citations,
limits, exports, dashboards/views, and unchanged-rerun cache decisions.
- Acceptance gates: Every executed scenario resolves to bounded, policy-labelled source evidence;
exports and configured views validate; unavailable optional profiles have working fallbacks;
unchanged rerun avoids heavy topic/report recomputation; unresolved failures keep the task open.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

#### review-investigation-and-report-integrity

Review the integrated milestone before provided-archive end-to-end proof and scale pilots.

- Serves: `discovery-visualization` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `build-search-graph-and-report-interfaces`;
`implement-directory-to-knowledge-base-acceptance`; `implement-anomaly-review-and-triage-exports`;
`provision-local-dashboards-and-age-viewer`.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
Use deterministic integration evidence and inspect provided-archive runs when available;
this verdict permits fixture implementation, not real-data or CUDA promotion.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/run artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace company/product/person catalogs,
invoice allocations, BOM units/revisions, supply roles,
anomaly cohorts/ranks, graph-table parity, one-generation reports and source drill-down;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

#### add-cited-local-question-answering (optional)

Provide bounded local questions and generative summary refinement only when citation quality
justifies it.

- Serves: `discovery-visualization` -- [Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: RUN NEEDED
- Dependencies: `build-search-graph-and-report-interfaces`;
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md).
Lexical retrieval suffices; selected vectors are conditional.
- User-visible outcome: Analysts may ask questions over selected evidence and receive cited
answers or explicit
abstention without leaving the host.
- Scope boundary: Optional refinement; deterministic reports remain sufficient. No unrestricted SQL,
filesystem access, source edits, unsupported claims, or acceptance of instructions from documents.
- Data and artifact paths: `src/arxiv_int/query/answers/`, answer evaluation profiles, and
`$RUNS_DIR/<run-id>/evaluation/answers/`.
- Execution path: Retrieve bounded lexical evidence with optional selected hybrid inputs; generate schema-valid
answers with source-span references; validate citations and abstain on missing/conflicting evidence;
measure supported claims, refusal and cost on held-out questions.
- Acceptance gates: Fixtures and held-out questions cover hallucination, conflicting evidence,
prompt injection
and no-answer cases; local resource budget and citation validity pass or retain deterministic
reports with a recorded negative verdict.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Evaluation and evidence -- `evaluation-evidence`

#### implement-published-evidence-freshness-checks

Implement replayable lineage/freshness validation for measured claims published by reports and
current-state evidence references.

- Serves: `evaluation-evidence` --
[Implementation boundaries](../design/spec.md#implementation-boundaries)
- Agent status: CLEAR
- Dependencies:
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md);
[Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md).
- User-visible outcome: A stale run cannot continue to support a changed published claim.
- Scope boundary: Build ongoing evidence validation; routine review of each change remains part of that
change, not a deferred audit. Do not invent missing benchmarks.
- Data and artifact paths: `ctl.artifact`, run manifests, current-state measurements, and the docs
claim registry.
- Execution path: Link published metrics to run fields and content pins; list invalidations caused
by contract, model, profile, classification, or artifact changes.
Include Alembic revision identity, dbt model/input hashes and required Pandera/dbt rule outcomes
in freshness checks; a missing, stale or skipped validation report cannot certify an artifact.
- Acceptance gates: Every published number resolves to one immutable artifact field; implementation
boundaries remain explicit; orphan or stale claims fail CI.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

#### implement-directory-to-knowledge-base-acceptance

Exercise the complete investigation command on a mixed deterministic fixture and validate its entry report.

- Serves: `evaluation-evidence` -- [End-to-end run and output contract](../design/spec.md#end-to-end-run-and-output-contract)
- Agent status: CLEAR
- Dependencies: `build-search-graph-and-report-interfaces`;
[Hierarchical file classification](records/0079-archive-cls-implement-hierarchical-file-classification.md);
[Investigation profile and output manifest](records/0045-pipeline-implement-investigation-profile-and-output-manifest.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
- User-visible outcome: One directory-to-report command proves every required family is wired
through real baseline
stage adapters, independent of optional vectors, viewers and archive organization.
- Scope boundary: Network-free bounded integration acceptance; mocked inference error cases do not prove
real CUDA model fit or archive quality. External host proof is a separate task.
- Data and artifact paths: `tests/integration/pipeline/`, mixed source fixtures, `configs/pipeline/`,
Make integration
target, and disposable configured runtime roots.
- Execution path: Use a text/document, financial table, product assembly, ambiguous parties,
malformed source
and cross-file relation; configure their roots in `.env`, run bare `make pipeline`, validate
manifest/report and every source anchor, then compare with the documented atomic chain on isolated
equivalent inputs. Rerun unchanged and test a source change/removal plus an interrupted publication.
- Acceptance gates: Required catalog/domain/anomaly entries, expected relations/amounts/BOM and valid-empty
cases match frozen expectations; exit/state semantics, bounded resources, no source writes,
cache reuse, coherent generation updates and source-level report drill-down all pass. No shell
activation, exports, separate forecast or post-run report/validation command is needed; aggregate
and atomic results agree logically. README availability changes only after the corresponding gates.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

#### publish-provided-archive-end-to-end-proof

Run evaluation and reporting over the supplied archive through one end-to-end integration test
covering every usable pipeline stage and artifact family.

- Serves: `evaluation-evidence` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-directory-to-knowledge-base-acceptance`;
`prove-archive-classification-on-provided-archive`; `prove-discovery-and-visualization-on-provided-archive`;
`prove-anomaly-analysis-on-provided-archive`;
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
Semantic proof is required only for a selected vector branch.
`review-investigation-and-report-integrity`.
- Audit inputs: [AUD-repair-retrieval-and-classification-identity-and-evidence-3](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md#audit-handoff).
`approve-classification-operating-point`; `approve-entity-merge-and-ontology-policy`;
`approve-fact-review-and-publication-policy`; `approve-domain-artifact-semantics-and-inclusion`;
`approve-anomaly-triage-policy`; `accept-operator-discovery-workflows`.
- User-visible outcome: One command/report shows which pipeline stages have current proof on the
supplied file silos, which artifacts they produced, which optional branches were not selected, and
how every result resolves to evidence.
- Scope boundary: Evaluate and index bounded proof outputs; do not substitute this test archive for
representative-scale authorization or conceal failed, stale, blocked, or absent stages.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, ordinary evaluation/report
outputs, and test logs below `$DATA_DIR/integration/evaluation-evidence/`.
- Execution path: Set the authorized bounded archive scope and selected local inference lane in
`.env`; run `make setup` with edits/retries until ready, then bare `make pipeline` on one CUDA host.
Retain the automatic preflight/forecast and setup evidence; verify required
outputs, entry report and exact source anchors; capture actual device/model resources; inspect the
ordinary stage manifests for quality context, rerun unchanged, and validate the coverage/provenance
matrix.
- Acceptance gates: Every required usable stage has a current `passed` or valid-empty result and
checksum-valid artifacts; every required output resolves through one knowledge-base generation;
optional disabled
branches cite selection reasons and fallbacks (measured verdicts for comparative claims); the end-to-end
report exposes all failures/coverage gaps; unchanged evaluation/report work is reused; private paths
and corpus content are absent from repository documentation.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

#### run-representative-scale-pilots

Measure storage amplification, throughput, memory, WAL/temp growth, retrieval quality, resume, and
rebuild on two progressively larger corpus slices.

- Serves: `evaluation-evidence` --
[Performance and scalability assumptions](../design/spec.md#performance-and-scalability-assumptions)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `publish-provided-archive-end-to-end-proof`; [Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md);
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md);
`implement-backup-restore-and-rebuild-runbook`;
`test-failure-and-capacity-boundaries`. Optional branches participate only when selected.
`review-recovery-before-scale-pilots`.
- Human review handoff:
[authorize-full-corpus-run](#authorize-full-corpus-run)
pilot ranges, pins, scope, stop conditions and proposed decision.
Packet: `$RUNS_DIR/<run-id>/authorization/`.
Packet prepared here; approval remains pending `review-production-readiness-and-recovery` and human prerequisites.
Blocked consumer:
full-corpus execution (not another implicit agent implementation task).
Report readiness using the human-handoff workflow; never self-approve.
Decision: authorize-next, resize/reconfigure, subset-only or stop for the exact pins and budget.
- User-visible outcome: A capacity plan predicts normalized, classification, registered domain
artifact, heap, lexical, vector, graph, WAL, temp, backup, wall-time, and operator-review costs
before the full archive runs.
- Scope boundary: Run only approved representative slices; do not authorize the full corpus or
extrapolate without uncertainty and format mix.
- Data and artifact paths: Approved `$ARCHIVE_DIR` slices, `$RESULTS_DIR`, `$PGDATA_DIR`,
`$RUNS_DIR/<run-id>/pilot/`, and generated capacity report.
- Execution path: Run 0.1-1% or 50-200 GB pilot, tune bounded parameters, then a larger partition;
inject interruption; measure extraction yield, classification coverage, dedupe, chunks, indexes,
updates, reindex, vector tiers, domain artifacts, graph, and recovery. Archive reorganization stays
a separately authorized drill and is not implied by the pilot.
- Acceptance gates: Both runs remain within declared resource safety margins; estimates include
uncertainty and concurrent-rebuild space; every failure and excluded format is counted; report
ends in authorize-next, resize/reconfigure, retain-subset, or stop.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

### Operational recovery -- `operational-recovery`

#### harden-local-security-and-no-egress-mode

Enforce read-only input, loopback services, least-privilege roles, secret redaction, bounded paths,
container mounts, and a network-denied run mode.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: RUN NEEDED
- Dependencies: Compose profiles documented in [Portable runtime](current/portable-runtime.md);
[Canonical relational schema](records/0021-store-create-canonical-relational-schema.md);
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
`build-search-graph-and-report-interfaces`. Organizer hardening is accepted in its own capability.
- Human review handoff:
[accept-recovery-and-security-posture](#accept-recovery-and-security-posture)
access/retention checklist, restore inventory, reproduction commands and residual risks.
Packet: `$RUNS_DIR/<run-id>/review/recovery/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`review-recovery-before-scale-pilots`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: witness restore and accept/reject the exact posture and residual risks.
- User-visible outcome: The local stack can process prepared inputs without unintended network
access or writable archive access, with bounded read-only evidence and report queries.

- Scope boundary: Host-local hardening and verification; not a formal third-party penetration test
or multi-user internet deployment.
- Data and artifact paths: Compose security settings, database role migrations, `.env.example`,
`src/arxiv_int/security/`, and security integration fixtures.
- Execution path: Apply non-root/read-only mounts where supported, localhost ports, role separation,
URL/path allowlists, secret filters, image/model pin checks, and network-denied integration
profile.
- Acceptance gates: Prepared smoke succeeds with egress denied; pipeline archive writes fail;
document instructions cannot trigger tools, source writes, unbounded queries or external requests;
UI role mutations fail; secrets/corpus snippets
do not appear in logs; dependency/image scan findings are triaged without suppressing gates.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: `review-recovery-before-scale-pilots`.

#### implement-backup-restore-and-rebuild-runbook

Create and exercise backups for contracts/config, normalized artifacts, PostgreSQL, and projection
rebuild metadata.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: RUN NEEDED
- Dependencies: [0025](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
`harden-local-security-and-no-egress-mode`; `register-and-expose-domain-artifacts`.
Run the initial restore on disposable fixture/small-proof data before scale pilots.
- Human review handoff:
[accept-recovery-and-security-posture](#accept-recovery-and-security-posture)
access/retention checklist, restore inventory, reproduction commands and residual risks.
Packet: `$RUNS_DIR/<run-id>/review/recovery/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`review-recovery-before-scale-pilots`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: witness restore and accept/reject the exact posture and residual risks.
- User-visible outcome: A documented command sequence restores canonical state, classifications,
move/source lookup, and artifact registries, then validates or rebuilds search and graph projections
on a clean target path.
- Scope boundary: Single-host backup/restore and removable-disk workflow; no HA or enterprise
replica claim.
- Data and artifact paths: `scripts/backup/`, `scripts/restore/`, `Makefile` for `make backup` and
`make restore-check`, backup manifests outside `$PGDATA_DIR`, `$RUNS_DIR/<run-id>/recovery/`, and
`docs/guide/recovery.md`.
- Execution path: Capture extension/image/model ids, migrations and logical/physical backup covering
`PGDATA_DIR` with any configured WAL and tablespace roots as one unit, normalized/classification
manifests, review/identity/anomaly dispositions, configured policies, path-event ledgers, artifact
registries, checksums, and free-space requirements; restore
into a new directory, run contract/live-store/source-lookup checks, and rebuild disposable
projections.
Capture Alembic heads and immutable revisions, contract/model/rule versions, and sanitized dbt
lineage/quality reports. Verify the restored live catalog without blind stamping; rebuild dbt
derived generations and run shared quality tests before activating restored projections.
- Acceptance gates: Clean-target restore reproduces canonical counts/checksums and sampled queries;
a backup missing a configured WAL or tablespace root fails as incomplete rather than restoring a
partial cluster; missing/corrupt backup parts fail before mutation; recovery time/space are recorded;
original data remains untouched.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: `review-recovery-before-scale-pilots`.

#### test-failure-and-capacity-boundaries

Exercise disk pressure, database restart, worker death, corrupt artifacts, model timeout, invalid
index, and stale lease behavior before full-corpus authorization.

- Serves: `operational-recovery` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: RUN NEEDED
- Dependencies: `implement-backup-restore-and-rebuild-runbook`;
[Progress logging and resource telemetry](records/0043-pipeline-add-progress-logging-and-resource-telemetry.md);
[Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md);
[Incremental reconciliation and stale pruning](records/0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md).
Organizer failure injection is separate.
- Audit inputs: [AUD-review-corpus-and-control-integrity-4](records/0063-corpus-review-corpus-and-control-integrity.md#audit-handoff);
[AUD-review-corpus-and-control-integrity-5](records/0063-corpus-review-corpus-and-control-integrity.md#audit-handoff);
[AUD-review-retrieval-and-classification-boundaries-5](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff).
- Human review handoff:
[accept-recovery-and-security-posture](#accept-recovery-and-security-posture)
seal
`$RUNS_DIR/<run-id>/review/recovery/` with restore/failure evidence and residual-risk decisions.
Ready after this task and its security/restore prerequisites pass;
blocks `review-recovery-before-scale-pilots`.
Also contributes capacity/stop-condition evidence to [authorize-full-corpus-run](#authorize-full-corpus-run);
that decision remains pending pilots and the production checkpoint. Print both states.
Decision: witness restore and accept/reject the exact posture and residual risks.
- User-visible outcome: Known failures stop safely, preserve evidence, and provide a tested
resume/rebuild action instead of corrupting state.
- Scope boundary: Controlled disposable fixtures and pilot paths only; no destructive testing
against the real archive or sole backup.
- Data and artifact paths: Disposable test volumes under `$RESULTS_DIR/test/`,
`$RUNS_DIR/<run-id>/failure-tests/`, and recovery fixtures.
- Execution path: Inject bounded failures at artifact write, COPY, index
build, AGE projection, model call, and shutdown boundaries; verify alerts, state transitions,
cleanup plans, source lookup, and recovery.
- Acceptance gates: No accepted partial artifact or duplicate canonical row results; retries are
bounded; invalid indexes/projections never become active; forecast and each large-stage recheck
refuse before the configured safety margin is consumed; stale cleanup never removes protected data.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: `review-recovery-before-scale-pilots`.

#### review-recovery-before-scale-pilots

Review recovery and refusal behavior before pilot scale increases exposure and resource cost.

- Serves: `operational-recovery` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `harden-local-security-and-no-egress-mode`; `implement-backup-restore-and-rebuild-runbook`;
`test-failure-and-capacity-boundaries`; `publish-provided-archive-end-to-end-proof`;
`accept-recovery-and-security-posture`.
- User-visible outcome:
Pilot runs start with a verified restore boundary, current limits and a recorded human posture decision.
- Scope boundary:
Use completed disposable/small-proof recovery and failure evidence. This precedes scale pilots;
the later production checkpoint evaluates their measured results and cannot be replaced here.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace backup inventory versus rebuildable projections, ontology/identity/review snapshots,
source lookup, clean-target restore, power/process failure claims, no-egress and space/WAL reserves.
Verify the human acceptance names the exact evidence and residual risks; changed pins invalidate it.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
Restored facts, policy/ontology versions and historical geotemporal answers reconcile; cancellation
and low-space refusal preserve active data. Missing/stale restore evidence or human acceptance
blocks scale pilots; no full-corpus authorization follows from this checkpoint.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: none; this is the bounded checkpoint.

#### review-production-readiness-and-recovery

Review the integrated milestone before full-corpus authorization.

- Serves: `operational-recovery` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `run-representative-scale-pilots`; `test-failure-and-capacity-boundaries`;
`implement-backup-restore-and-rebuild-runbook`; `implement-published-evidence-freshness-checks`.
`review-recovery-before-scale-pilots`.
- Human review handoff:
[authorize-full-corpus-run](#authorize-full-corpus-run)
reviewed pilot/recovery verdict and exact decision packet.
Packet: `$RUNS_DIR/<run-id>/authorization/`.
After this checkpoint, report ready or list remaining policy decisions; never authorize automatically.
Blocked consumer:
full-corpus execution (not another implicit agent implementation task).
Report readiness using the human-handoff workflow; never self-approve.
Decision: authorize-next, resize/reconfigure, subset-only or stop for the exact pins and budget.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/run artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace one-CUDA-host model/resource
evidence, no-egress boundaries, backup completeness, decision
retention, source lookup, restore parity, cancellation and disk/WAL/rebuild headroom;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

### Semantic retrieval -- `semantic-retrieval`

#### implement-selective-embedding-pipeline

Add policy-driven embedding tiers, provider-neutral batching, versioned artifacts, and pgvector load
without embedding the entire archive by default.

- Serves: `semantic-retrieval` --
[Search and vector projections](../design/spec.md#search-and-vector-projections)
- Agent status: RUN NEEDED
- Dependencies: [Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md);
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md);
[ParadeDB lexical load and query path](records/0070-lexical-build-paradedb-lexical-load-and-query-path.md).
- User-visible outcome: Operators can embed a bounded, explainable corpus slice and resume batches
while preserving model/profile identity.
- Scope boundary: Implement tier selection and stable pgvector baseline; do not promote a
model/index before comparison.
- Data and artifact paths: `$RESULTS_DIR/normalized/embeddings/`, `search.embedding_profile`,
`search.chunk_embedding`, `src/arxiv_int/retrieval/embedding/`, and model configs.
- Execution path: Select unique/high-value/evaluation/miss-driven chunks; batch through Ollama,
vLLM, or local encoder; validate dimensions and normalization; write Parquet then binary COPY;
create no cross-profile index.
Use PyArrow/Polars batches with contract-derived Pandera profile/dimension checks before COPY;
manage selected vector schema/index changes through reviewed Alembic operations.
- Acceptance gates: Interrupted batch resumes; input/model/config changes create new ids;
selected-tier reason is recorded; embedding output is deterministic within declared tolerance; 16
GB VRAM stays within budget.
- Documentation target: `docs/impl/current/semantic-retrieval.md`
- Review checkpoint: `review-semantic-branch-integrity`.

#### compare-pgvector-paradedb-native-and-fallback-seam

Benchmark pgvector HNSW/IVFFlat/quantized candidates and ParadeDB native vector/hybrid search on the
same selected tier; exercise the Qdrant escape-hatch interface without deploying it by default.

- Serves: `semantic-retrieval` --
[Promotion and fallback gates](../design/spec.md#promotion-and-fallback-gates)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: `implement-selective-embedding-pipeline`; [Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
- User-visible outcome: The project has a measured vector/hybrid choice or an explicit lexical-only
decision, plus a bounded fallback if Postgres cannot meet requirements.
- Scope boundary: Compare recall, filtering, fusion, lifecycle, and cost; do not add Qdrant unless
both Postgres candidates fail a declared mandatory gate.
- Data and artifact paths: `configs/retrieval/vector/`, `$RUNS_DIR/<run-id>/evaluation/vector/`,
projection manifests, and optional adapter tests.
- Execution path: Hold chunks/embeddings/queries constant; sweep index/search parameters and RRF;
record build time, WAL/temp, disk, RAM, p95 latency, recall, updates, vacuum/rebuild, and restore;
run paired answer-side check for promoted candidates.
- Acceptance gates: A predeclared adopt/retain/inconclusive rule is applied; native beta status is
visible; fallback addition requires a failed mandatory gate and its own integration plan.
- Documentation target: `docs/impl/current/semantic-retrieval.md`
- Review checkpoint: `review-semantic-branch-integrity`.

#### prove-semantic-retrieval-on-provided-archive

Run the selected semantic/hybrid branch on a bounded supplied-archive tier through an integration
test, or retain a measured not-selected verdict.

- Serves: `semantic-retrieval` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `compare-pgvector-paradedb-native-and-fallback-seam`;
[Lexical retrieval provided-archive integration](records/0073-lexical-prove-lexical-retrieval-on-provided-archive.md);
[Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md).
- User-visible outcome: Operators can inspect actual archive embeddings, vector/hybrid results,
resource cost, and citations, or see why the branch remains disabled with lexical fallback working.
- Scope boundary: Use only the forecast-approved selected tier and configured local models; do not
embed the complete supplied archive or treat an unavailable/failed branch as successful proof.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, embedding/vector
artifacts, and test logs below `$DATA_DIR/integration/semantic-retrieval/`.
- Execution path: Forecast model and index resources; run selected embedding/load/query profiles;
validate vector identities, counts, paired retrieval evidence, and fallback; rerun unchanged and
record that model inference and index build are reused.
- Acceptance gates: A usable branch has checksum-valid vectors/indexes, cited queries, measured
quality/cost verdict, and no heavy work on identical rerun. `not-selected` is valid only with the
declared measured negative result and verified lexical fallback; other failures keep the task open.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/semantic-retrieval.md`
- Review checkpoint: `review-semantic-branch-integrity`.

#### review-semantic-branch-integrity

Review the integrated milestone before promotion of the selected semantic branch.

- Serves: `semantic-retrieval` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `prove-semantic-retrieval-on-provided-archive`;
[Model resource scheduler](records/0032-inference-implement-model-resource-scheduler.md).
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/run artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace vector/profile isolation,
conditional model loading, no default all-corpus embeddings,
paired relevance evidence, resource lifecycle, citation validity and lexical fallback;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/semantic-retrieval.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

### Graph-constrained agents -- `graph-constrained-agents`

#### implement-graph-constrained-context-assembly

Corpus text reaches a local model today only through ad hoc retrieval slices, so nothing guarantees
that a prompt fits the model's declared context or that its evidence stayed whole and cited.

- Serves: `graph-constrained-agents` --
[Context assembly contract](../design/spec.md#context-assembly-contract)
- Agent status: CLEAR
- Dependencies: `review-graph-analytics-integrity`;
`build-search-graph-and-report-interfaces`;
[Local inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md).
- User-visible outcome: Any model-facing request over corpus content returns a reproducible context
pack of graph nodes, accepted edges and whole cited evidence spans within the selected model
profile's token budget, with everything it dropped and why stated.
- Scope boundary: Build the budgeted assembly and pack identity only. No new answer product, no
unbounded query, no filesystem path handed to a model, and no character-count token estimate.
- Data and artifact paths: `src/arxiv_int/agents/context/`, mirrored tests,
`configs/agents/context/`, `$RUNS_DIR/<run-id>/agents/context/`, and context-pack fixtures.
- Execution path: Take pinned ontology, identity, fact, community and metric snapshots plus an entry
set. Reserve instruction and output allowances, then fill the evidence budget by the declared
deterministic traversal order under depth, fan-out, per-node and per-pack caps. Count tokens through
the model profile's own tokenizer via the existing inference seam. Drop only whole cited items and
record the cap that dropped each one with its coverage denominator. Refuse when the reserved
allowances exceed the context length or no complete cited item fits. Identify each pack by snapshot
ids, entry set, policy fingerprint, model profile and tokenizer revision.
- Acceptance gates: Identical inputs produce an identical pack; a pack never exceeds the declared
budget and never splits an evidence span or separates it from its citation; drops are reported with
their cap and denominator; impossible requests are refused rather than silently truncated; an
unknown or changed snapshot id refuses assembly; no pack carries a filesystem path or an executable
instruction from source text; escaped snippet fixtures pass.
- Documentation target: `docs/impl/current/graph-constrained-agents.md`
- Review checkpoint: `review-agent-guardrail-integrity`.

#### implement-methodologist-probe-generation

Nothing currently produces reproducible, graph-anchored probes that exercise whether the published
knowledge is actually reachable, so blind spots are found only by accident.

- Serves: `graph-constrained-agents` --
[Role-separated agent diagnostics](../design/spec.md#role-separated-agent-diagnostics)
- Agent status: RUN NEEDED
- Dependencies: `implement-graph-constrained-context-assembly`.
- User-visible outcome: A bounded set of analytical probes names its target graph region, its
required and bonus concepts by canonical id, and the evidence it expects, and regenerates
identically from the same snapshot and seed.
- Scope boundary: Generate diagnostic stress inputs over a pinned snapshot. A probe is never a gold
label, never enters an evaluation gate as truth, and never introduces a concept or predicate absent
from the snapshot.
- Data and artifact paths: `src/arxiv_int/agents/methodologist/`, mirrored tests,
`configs/agents/probes/`, `$RESULTS_DIR/normalized/agent-probes/`, and
`$RUNS_DIR/<run-id>/agents/probes/`.
- Execution path: Select a bounded region by community, bridge concept, importance and dependency
depth. Generate probes with bounded schema-validated local inference over context packs, requiring
every named concept to resolve to a snapshot id. Persist the region selection, seed, model
fingerprint, probe schema version and the required and bonus concept sets.
- Acceptance gates: Every probe's concepts resolve in the pinned snapshot and a hallucinated id is
rejected rather than stored; identical snapshot, region, seed and model profile reproduce the
identical probe set; probes stay inside the declared region and count limits; probe artifacts are
labelled as diagnostic inputs and no gate in the specification consumes them as gold.
- Documentation target: `docs/impl/current/graph-constrained-agents.md`
- Review checkpoint: `review-agent-guardrail-integrity`.

#### implement-constrained-analyst-sessions

Without a session boundary that forces citation and abstention, a model asked to investigate the
corpus produces confident unsupported prose that is indistinguishable from a finding.

- Serves: `graph-constrained-agents` --
[Role-separated agent diagnostics](../design/spec.md#role-separated-agent-diagnostics)
- Agent status: RUN NEEDED
- Dependencies: `implement-methodologist-probe-generation`.
Reuse `add-cited-local-question-answering` only when that optional branch is selected.
- User-visible outcome: Each probe attempt produces a session log of every context pack, query,
budget outcome, cited claim and abstention, replayable from its recorded identities.
- Scope boundary: Attempt probes through context packs and the bounded read-only query surface only.
No accepted fact, no threshold change, no unbounded SQL, no filesystem access and no source edit.
- Data and artifact paths: `src/arxiv_int/agents/analyst/`, mirrored tests,
`configs/agents/analyst/`, `$RESULTS_DIR/normalized/agent-sessions/`, and
`$RUNS_DIR/<run-id>/agents/sessions/`.
- Execution path: Run each probe under declared step, pack, query and time caps. Require a source
span citation for every claim through the ordinary evidence lookup, and require abstention when the
packs contain no supporting evidence. Persist the full session log with pack ids, budget outcomes,
model fingerprints and schema versions.
- Acceptance gates: A claim without a resolvable citation is recorded as unsupported rather than
published; withheld evidence produces abstention rather than an answer; step, pack, query and time
caps are enforced and an exhausted cap ends the session with its state recorded; prompt-injection
fixtures in probe text, document text and session history cannot grant an unbounded query, a
filesystem path or any write; identical inputs, seeds and model profile reproduce the identical
session log.
- Documentation target: `docs/impl/current/graph-constrained-agents.md`
- Review checkpoint: `review-agent-guardrail-integrity`.

#### implement-concept-coverage-and-blind-spot-evaluator

Operators have no report of which published concepts are unreachable, uncited or unusable through
the real retrieval path, so coverage gaps stay invisible until an investigation fails.

- Serves: `graph-constrained-agents` --
[Role-separated agent diagnostics](../design/spec.md#role-separated-agent-diagnostics)
- Agent status: CLEAR
- Dependencies: `implement-constrained-analyst-sessions`.
- User-visible outcome: Each session yields a coded score of required and bonus concept use, valid
and invalid citations, unsupported claims, concepts unreachable inside the budget and concepts
reachable but missed, aggregated into a graph and corpus coverage report.
- Scope boundary: Score sessions and publish coverage in code. A local model may add clearly
non-authoritative commentary. The evaluator may steer only which region the methodologist probes
next; it may not change the ontology, a fact state, a threshold or a prompt policy, and its output
feeds no acceptance gate.
- Data and artifact paths: `src/arxiv_int/agents/evaluator/`, mirrored tests,
`configs/agents/coverage/`, `$RESULTS_DIR/normalized/agent-coverage/`, and
`$RUNS_DIR/<run-id>/agents/coverage/`.
- Execution path: Register the `agent-diagnostics` stage covering probe, session and scoring
artifacts. Resolve every citation through the ordinary source lookup; classify each required and
bonus concept as used, missed or unreachable with the cap that blocked it; aggregate concepts with
no retrievable evidence, communities unreachable inside the budget, predicates whose evidence never
validates, and unattempted probes. Publish the report with its snapshot, policy and model
fingerprints and an explicit statement of what it does not measure.
- Acceptance gates: Scoring is produced by code and identical inputs reproduce an identical report;
a fabricated or unresolvable citation scores as unsupported; unreachable and missed concepts are
distinguished with the responsible cap; model commentary is separable and marked non-authoritative;
fixtures prove the evaluator cannot write an ontology term, a fact state, a threshold or a prompt
policy and that no specification gate consumes its output; the report states that it measures
reachability and coverage, not archive truth or quality.
- Documentation target: `docs/impl/current/graph-constrained-agents.md`
- Review checkpoint: `review-agent-guardrail-integrity`.

#### prove-graph-constrained-agents-on-provided-archive

Run context assembly, probe generation, constrained sessions and coverage scoring on the supplied
archive through an explicit integration test.

- Serves: `graph-constrained-agents` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies: `implement-concept-coverage-and-blind-spot-evaluator`;
`prove-graph-analytics-on-provided-archive`;
`prove-discovery-and-visualization-on-provided-archive`;
`approve-graph-analytics-operating-points`.
- Human review handoff:
[accept-agent-diagnostic-scope](#accept-agent-diagnostic-scope)
sealed context-budget, probe, session and coverage packet with the declared non-measurement
statement.
Packet: `$RUNS_DIR/<run-id>/review/agents/`.
Ready after this proof and its named producer inputs pass.
Blocked consumer:
operator use of the diagnostic branch in a full-corpus run; no agent successor task depends on it.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept the diagnostic scope, budgets and reporting language, or retain the branch
unselected.
- User-visible outcome: Real archive context packs, probes, sessions, abstentions and the coverage
report are inspectable with their budgets, drops, citations and snapshot identities, or the
not-selected verdict names the working baseline.
- Scope boundary: Prove the configured diagnostic profiles on one pinned generation. Do not present
the report as archive quality evidence, feed it into any acceptance gate, or let a session change
published data.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/{agent-probes,agent-sessions,agent-coverage}/`, and test logs below
`$DATA_DIR/integration/graph-constrained-agents/`.
- Execution path: Forecast inference resources; assemble packs against the configured model profile;
generate probes, run sessions and score coverage; validate pack budgets and drop accounting,
citation resolution, abstention behavior, probe id resolution and report determinism; rerun
unchanged and record inference cache hits; assemble the human review packet with positive, negative
and ambiguous samples.
- Acceptance gates: Every sampled pack respects the declared budget and reports its drops; every
sampled cited claim resolves to a source span and every unresolvable one is scored unsupported;
injection samples from real documents change no boundary; the identical rerun performs no new
inference and reproduces the identical report; published data is unchanged by the run; a
not-selected verdict is valid only with a declared measured negative result; other failures keep the
task open. Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is
committed or staged for commit. Record the run id, artifact roots, manifests, and checksums checked
in place.
- Documentation target: `docs/impl/current/graph-constrained-agents.md`
- Review checkpoint: `review-agent-guardrail-integrity`.

#### review-agent-guardrail-integrity

Review the agent guardrails before the diagnostic branch is offered to an operator.

- Serves: `graph-constrained-agents` --
[Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: `implement-concept-coverage-and-blind-spot-evaluator`;
`prove-graph-constrained-agents-on-provided-archive`.
- User-visible outcome: An evidence-based checkpoint decides proceed,
proceed-with-nonblocking-notes, or blocked for the named consumers; no-refactoring-needed is a valid
result.
- Scope boundary: Review the named producers, their cross-module invariants and routed notes only.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this stage
is in scope; concluding that existing tests already cover them is valid. No speculative rewrite, new
agent role, or numeric coverage floor.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state
pages, existing test and run artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read the full task snapshots and source changes. Trace that every model-facing
byte of corpus text arrives through a budgeted pack, that tokenization uses the profile tokenizer,
that drops and refusals are accounted for, that probes cannot name absent concepts, that sessions
cannot widen their surface under injection, that scoring is coded rather than model-judged, and that
the feedback loop reaches nothing but probe-region selection. Confirm no specification gate consumes
diagnostic output. Replay representative existing tests and validators; add tests for important
stabilized cases the stage still misses; reconcile every routed note with evidence, severity,
affected consumers and one disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition; the
listed invariants are verified and `make ci` passes. Any blocking finding gets a focused
prerequisite repair task and keeps this checkpoint open until it passes; valid negative results and
nonblocking follow-ups are recorded without claiming a wider audit.
- Documentation target: `docs/impl/current/graph-constrained-agents.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task
ids.

### Separate archive organization -- `archive-organization`

#### implement-audited-archive-reorganization

Implement dry-run, apply, resume, rollback, and locate commands for classification-based archive
organization in both copy-to-target and in-place move modes.

- Serves: `archive-organization` --
[Separate archive organization utility](../design/spec.md#separate-archive-organization-utility)
- Agent status: CLEAR
- Dependencies:
[Hierarchical file classification](records/0079-archive-cls-implement-hierarchical-file-classification.md);
[Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
`implement-backup-restore-and-rebuild-runbook`
for move recovery semantics; use disposable roots for acceptance.
[Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md).

- Human review handoff:
[approve-archive-organization-plan](#approve-archive-organization-plan)
dry-run plan/diff, source lookup, rollback and mode instructions.
Packet: `$RUNS_DIR/<run-id>/archive-reorganization/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`execute-authorized-archive-reorganization`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: apply, mapping-only, revise or stop for the exact plan, mode and scope.
- User-visible outcome: An authorized operator can build a classified tree of short meaningful ASCII
class directories -- copied to a target disk by default, or moved in place when that is the intent --
and still resolve every knowledge source to its initial and current path.
- Scope boundary: Default to dry-run and to `copy` mode, which reads one silo root read-only and
writes only under the declared target; `move` mode uses per-file atomic renames on one filesystem
beneath one
explicitly writable silo root per plan. Never overwrite, silently recategorize, cross silos, follow
escaping links, write into the results or database roots, or run from the ordinary read-only
pipeline/Compose path.
- Data and artifact paths: `src/arxiv_int/archive/`, `corpus.document_path_event`, additive
`src/arxiv_int/migrations/versions/`,
`$RUNS_DIR/<run-id>/archive-reorganization/{plan.json,ledger.parquet,journal/}`,
CLI and path-limit fixtures, the declared copy target, and the selected silo root only after
`--apply` in `move` mode.
- Execution path: Build ancestor directories from reversible class tokens and bounded ASCII slugs;
route safely placeable special outcomes to `_unclassified` and `_unreadable`; preflight
component/full-path limits, available hashes, links, devices, target overlap, target free space,
collisions, backup for `move`, and complete path accounting; use independent verified copies on
either same or different filesystems; exclude hardlinks;
consume sealed exports without live database/model services; reuse the reviewed
`document-path-events` contract and Alembic `0001` `corpus.document_path_event` table;
record unplaceable entries as blocked; enforce a silo placement lease, stable duplicate-name
suffixes, filesystem identity checks, and idempotent path-ledger import; seal
the ledger before journaling renames or verified copies; expose resume and verified rollback;
reuse the shared read-only
`archive locate` resolver.
Do not mint a second path-event schema. Use typed Polars/Arrow
ledger operations and shared Pandera checks on sealed inputs and output ledgers. The placement
executor remains independent of live dbt/database services.
- Acceptance gates: Dry-run is byte-for-byte reproducible; apply requires the exact accepted plan and
mode; fixtures prove no overwrite, byte-identical content in both modes, hash verification of every
copied file, one-to-one placed/blocked path accounting, collision and stale-hash refusal,
interruption/resume, reverse-order rollback that removes only ledger-proven and still-hash-matching
target files,
refusal to overwrite subsequent edits, journal/directory durability, offline artifact-only operation,
path-limit
compliance, unchanged source bytes after a `copy` run, and knowledge-source lookup. No production
archive is mutated by automated tests.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: `review-archive-organization-integrity`.

#### prove-archive-organization-on-provided-artifacts

Prove the organizer consumes pipeline exports independently and produces safe reviewable plans.

- Serves: `archive-organization` -- [Separate archive organization utility](../design/spec.md#separate-archive-organization-utility)
- Agent status: RUN NEEDED
- Dependencies: `implement-audited-archive-reorganization`; `prove-archive-classification-on-provided-archive`.
- Human review handoff:
[approve-archive-organization-plan](#approve-archive-organization-plan)
provide
`$RUNS_DIR/<run-id>/archive-reorganization/` plan/diff, fingerprints, source lookup and recovery drill.
After the proof, checkpoint and classification decision pass, report ready for apply/mapping-only/revise/stop.
Also prepare the exact command, target/mode/backup checks and rollback instructions for
[execute-authorized-archive-reorganization](#execute-authorized-archive-reorganization).
Execution remains blocked by the human plan decision; never interpret a draft packet as authorization.
Decision: apply, mapping-only, revise or stop for the exact plan, mode and scope.
- User-visible outcome: The operator can inspect copy and move plans and resolve source paths
without starting
model, search, or graph services.
- Scope boundary: Dry-run only on the provided archive; execute/resume/rollback solely on
disposable copies.
No acceptance of this utility is a prerequisite for the pipeline.
- Data and artifact paths: Classification/source manifests, ordinary organization plans below
`$RUNS_DIR/<run-id>/archive-reorganization/`, and test logs below
`$DATA_DIR/integration/archive-organization/`.
- Execution path: Validate exported fingerprints offline; generate both mode plans; test verified independent
copies, same-filesystem moves, journal recovery and idempotent ledger import on disposable roots;
edit a placed file and prove rollback refuses to remove it.
- Acceptance gates: Plans are deterministic with placed/blocked accounting, safe names and
collision handling;
no provided source changes; no model/database dependency; source hashes, lookup, and recovery
match the contract; missing backup blocks move application without blocking copy planning.
Only ordinary utility artifacts stay under configured roots; nothing source-derived is committed or
staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: `review-archive-organization-integrity`.

#### review-archive-organization-integrity

Review the integrated milestone before any real copy/move plan authorization.

- Serves: `archive-organization` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Audit inputs: [AUD-safe-runtime-root-boundaries-1](records/0005-runtime-refactor-safe-runtime-root-boundaries.md#audit-handoff).
- Dependencies: `prove-archive-organization-on-provided-artifacts`;
[Safe runtime root boundaries](records/0005-runtime-refactor-safe-runtime-root-boundaries.md).
- Human review handoff:
[approve-archive-organization-plan](#approve-archive-organization-plan)
provide
`$RUNS_DIR/<run-id>/archive-reorganization/` plan/diff, fingerprints, source lookup and recovery drill.
After the proof, checkpoint and classification decision pass, report ready for apply/mapping-only/revise/stop.
Also prepare the exact command, target/mode/backup checks and rollback instructions for
[execute-authorized-archive-reorganization](#execute-authorized-archive-reorganization).
Execution remains blocked by the human plan decision; never interpret a draft packet as authorization.
Decision: apply, mapping-only, revise or stop for the exact plan, mode and scope.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/run artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace artifact-only execution,
complete classification accounting, source/destination identity,
independent copies, protected roots, durable move journal, edited-target rollback refusal and lookup;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

## Human-Assisted Tasks

### Archive classification -- `archive-classification`

#### approve-classification-operating-point

Accept the classifier operating point on the approved subject taxonomy without authorizing any file
placement.

- Serves: `archive-classification` -- [Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: HUMAN-GATED
- Dependencies: `prove-archive-classification-on-provided-archive`;
[Classification taxonomy approval](records/0078-archive-cls-approve-classification-policy.md).
- User-visible outcome: The owner accepts the thresholds, calibration, exceptional-outcome handling
and coverage limits used for archive browsing and future organization plans.
- Scope boundary: Approve one versioned operating point on the approved taxonomy only; the taxonomy
itself was accepted separately. This neither chooses a destination nor authorizes copying or moving
files.
- Data and artifact paths: `configs/policy/classification.yaml`, classifier profile, scheme
manifest, and `$RUNS_DIR/<run-id>/review/classification/`.
- Execution path: Present hierarchical errors, ancestor metrics, ambiguous/exception samples,
thresholds, calibration and review effort; confirm the Russian and Ukrainian captions; record accept,
revise, or retain-unclassified.
- Acceptance gates: The exact scheme/profile/policy fingerprints and decision are recorded;
low-confidence files remain exceptional; no filesystem mutation is requested.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Identity, ontology, and graph -- `identity-ontology-graph`

#### approve-entity-merge-and-ontology-policy

Review entity-resolution operating points and ontology terms/constraints that can change graph and
report meaning.

- Serves: `identity-ontology-graph` --
[Ontology design](../design/spec.md#ontology-design)
- Agent status: HUMAN-GATED
- Dependencies: `prove-identity-ontology-graph-on-provided-archive`; held-out linkage curves from
`implement-probabilistic-entity-resolution`; ontology review package from
[Versioned ontology assets](records/0013-contract-gov-establish-versioned-ontology-assets.md).
`implement-ontology-snapshots-and-geotemporal-contracts`.
- User-visible outcome: Auto-merge thresholds and ontology semantics reflect the owner's precision
tolerance and domain meaning.
- Scope boundary: Approve bounded policies and terms; no manual editing of source mentions or
one-off hidden merges.
- Data and artifact paths: `configs/policy/identity.yaml`, versioned ontology assets, review
ledgers, and evaluation bundles.
- Execution path: Present pair/cluster errors, threshold curves, ambiguous aliases, term
definitions, domain/range, and constraint examples; record decisions as versioned configuration
and ontology commits.
Review terms against domain meaning, hidden helpers, the rule of three, additive extension, and
producer/consumer typing.
Review draft/published term differences, compatibility/deprecation mappings, geotemporal type and
uncertainty examples, source-valid versus recorded scope, and cross-version answer changes.
Acceptance publishes a new pinned interpretation; rejection leaves candidate terms unpublished.
- Acceptance gates: Auto-merge precision floor and review band are explicit; disputed terms remain
draft; every accepted change has rollback/deprecation behavior. New terms meet the rule of three
or a required specification type; helper/non-semantic objects are not published as classes.
- Documentation target: `docs/impl/current/identity-ontology-graph.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

### Knowledge extraction -- `knowledge-extraction`

#### approve-fact-review-and-publication-policy

Choose which fact types may be auto-accepted, remain proposed, or always require review, including
how conflicts affect equipment and supplier reports.

- Serves: `knowledge-extraction` --
[Canonical object and fact model](../design/spec.md#canonical-object-and-fact-model)
- Agent status: HUMAN-GATED
- Dependencies: `prove-knowledge-extraction-on-provided-archive`; per-type final metrics from
`implement-provenance-bearing-fact-extraction` and conflict examples from
`implement-fact-validation-conflict-and-review-overlays`.
- User-visible outcome: Reports clearly distinguish evidence-backed accepted claims, uncertain
proposals, conflicts, and exclusions according to an owner-approved risk policy.
- Scope boundary: Human policy decision over measured types and thresholds; it does not alter source
evidence or waive provenance requirements.
- Data and artifact paths: `configs/policy/facts.yaml`, reviewed metric bundle, local decision
ledger, and report policy documentation.
- Execution path: Present per-type precision/recall, false-positive examples, coverage, and review
cost; record policy with version, rationale, effective scope, and rollback.
- Acceptance gates: Every high-impact type has an explicit state/threshold; conflicts and unreviewed
facts have explicit report treatment; policy version is included in query/report provenance.
- Documentation target: `docs/impl/current/knowledge-extraction.md`
- Review checkpoint: `review-knowledge-and-identity-integrity`.

### Concept graph -- `concept-graph`

#### approve-concept-lexicon-and-relation-policy

Decide the concept merge thresholds, alias and definition policy, admitted predicates, and relation
weight formula that shape every later graph view.

- Serves: `concept-graph` --
[Concept layer and semantic graph construction](../design/spec.md#concept-layer-and-semantic-graph-construction)
- Agent status: HUMAN-GATED
- Dependencies: `prove-concept-graph-on-provided-archive`;
`approve-entity-merge-and-ontology-policy`;
`approve-fact-review-and-publication-policy`.
- User-visible outcome: The concept lexicon reflects the owner's domain meaning and precision
tolerance, and unmapped proposals stay out of published vocabulary until separately reviewed.
- Scope boundary: Approve one versioned concept operating point, alias and definition policy,
admitted predicate set and weight formula. This publishes no ontology term and authorizes no
distant-link adjudication spending.
- Data and artifact paths: `configs/concepts/`, `configs/concepts/relations/`, concept and relation
profile fingerprints, and `$RUNS_DIR/<run-id>/review/concepts/`.
- Execution path: Inspect canonical concepts against their variant clusters, ambiguous and
homograph samples, undefined and unmapped states, per-predicate samples with both evidence spans,
and the weight formula with its inputs; confirm the Russian, Ukrainian and English labels; record
accept, revise, or retain the branch unselected.
- Acceptance gates: The exact concept, relation, model, ontology and policy fingerprints and the
decision are recorded; uncertain merges stay unmerged; unmapped terms stay proposed; no ontology
change is requested through this decision.
- Documentation target: `docs/impl/current/concept-graph.md`
- Review checkpoint: `review-concept-layer-integrity`.

### Graph analytics -- `graph-analytics`

#### approve-graph-analytics-operating-points

Decide the distant-link adjudication budgets, the community algorithm and resolution, and the metric
and effort formulas, including whether any of them is worth running.

- Serves: `graph-analytics` --
[Distant-link discovery, communities, and topology metrics](../design/spec.md#distant-link-discovery-communities-and-topology-metrics)
- Agent status: HUMAN-GATED
- Dependencies: `prove-graph-analytics-on-provided-archive`;
`approve-concept-lexicon-and-relation-policy`.
- User-visible outcome: The published partition, bridge concepts, ranks, depths and effort scores
rest on operating points the owner accepted, with the adjudication cost and false-link tolerance
stated.
- Scope boundary: Approve budgets, algorithm and resolution selection, stability thresholds and
metric formulas. This accepts no individual proposed edge and authorizes no full-corpus spending.
- Data and artifact paths: `configs/graph-analytics/`, refinder, community and metric profile
fingerprints, and `$RUNS_DIR/<run-id>/review/graph-analytics/`.
- Execution path: Inspect the planted-link and archive refinder results with their precision,
false-link and abstention figures and adjudication cost; the partition with its agreement,
resolution sweep and proposed-edge share; sampled bridge concepts; the metric formulas, rank
stability and prerequisite cycle findings; record accept, revise, or retain each branch unselected
with the baseline named.
- Acceptance gates: The exact profile, budget, seed, formula and snapshot fingerprints and the
decision are recorded; an unstable partition is not approved as thematic structure; refinder edges
stay proposed; a not-selected verdict names the working baseline.
- Documentation target: `docs/impl/current/graph-analytics.md`
- Review checkpoint: `review-graph-analytics-integrity`.

### Domain investigation artifacts -- `domain-investigation-artifacts`

#### approve-domain-artifact-semantics-and-inclusion

Review domain meanings and inclusion policies for relationship, BOM, supply-chain, invoice, and
payment artifacts before they are presented as accepted investigation results.

- Serves: `domain-investigation-artifacts` --
[Domain investigation artifacts](../design/spec.md#domain-investigation-artifacts)
- Agent status: HUMAN-GATED
- Dependencies: `prove-domain-investigation-artifacts-on-provided-archive`;
`approve-fact-review-and-publication-policy`; `approve-entity-merge-and-ontology-policy`.
- User-visible outcome: Operators can distinguish evidence-backed `part-of`, supplier, invoiced,
paid, partial, disputed, and unmatched states using domain-approved meanings.
- Scope boundary: Approve measured semantics, inclusion states, and display language; do not repair
source records, waive evidence requirements, or certify engineering, accounting, or legal truth.
- Data and artifact paths: `configs/policy/domain-artifacts.yaml`, reviewed examples and metric
bundles, `$RUNS_DIR/<run-id>/review/domain-artifacts/`, and local decision ledger.
- Execution path: Present false relation examples, BOM quantity/unit conflicts, ambiguous party
roles, invoice arithmetic, payment allocation candidates, coverage gaps, empty results, and graph
labels; record per-family thresholds, allowed review states, warnings, and rollback.
- Acceptance gates: Every enabled family has approved semantics and inclusion rules; weak families
remain partial, review-only, or disabled; conflicts/unresolved links stay visible; policy version is
present in each registry row and render.
Revision/effectivity and time-bounded party/location roles are explicit; domain distinctions and
non-implication examples are reviewed against the exact ontology snapshot.
- Documentation target: `docs/impl/current/domain-investigation-artifacts.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Anomaly analysis -- `anomaly-analysis`

#### approve-anomaly-triage-policy

Choose measured thresholds, rank policy and review budget for source-evidenced anomaly triage.

- Serves: `anomaly-analysis` -- [Anomaly detection and triage](../design/spec.md#anomaly-detection-and-triage)
- Agent status: HUMAN-GATED
- Dependencies: `prove-anomaly-analysis-on-provided-archive`.
- User-visible outcome: The analyst sees only explicitly enabled detectors with understood
false-positive burden,
coverage limits and neutral labels.
- Scope boundary: Approve triage policy, not allegations or financial/legal conclusions; statistical
detectors may remain disabled while deterministic constraints stay available.
- Data and artifact paths: `configs/policy/anomalies.yaml`, reviewed metric bundle and
`$RUNS_DIR/<run-id>/review/anomalies/`.
- Execution path: Present hard negatives, precision at budget, missed cases, cohort sufficiency, rank
explanations and review cost; record enable, constraints-only, revise, or disable per detector.
- Acceptance gates: Each selected detector names its threshold, population, review budget
and policy version;
zero useful statistical detectors is valid; review dispositions preserve provenance.
- Documentation target: `docs/impl/current/anomaly-analysis.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Discovery and visualization -- `discovery-visualization`

#### accept-operator-discovery-workflows

Validate that a domain operator can complete representative topic, search, object/fact, graph,
company, product, person, equipment, supplier, BOM, supply-chain, invoice/payment and anomaly
workflows with understandable evidence
and filters.

- Serves: `discovery-visualization` --
[Analysis, graph, and visualization behavior](../design/spec.md#analysis-graph-and-visualization-behavior)
- Agent status: HUMAN-GATED
- Dependencies: `build-search-graph-and-report-interfaces`;
`provision-local-dashboards-and-age-viewer` only for a selected viewer;
`prove-discovery-and-visualization-on-provided-archive`; `approve-fact-review-and-publication-policy`;
`approve-entity-merge-and-ontology-policy`; `approve-domain-artifact-semantics-and-inclusion`;
`approve-anomaly-triage-policy`.
- User-visible outcome: The available interfaces answer the actual investigation questions without
requiring knowledge of internal table layouts.
- Scope boundary: Usability and domain correctness review on bounded tasks; not a public UI
accessibility or multi-user deployment certification.
- Data and artifact paths: Local scenario script, `$RUNS_DIR/<run-id>/acceptance/`,
screenshots/redacted notes, and issue ledger.
- Execution path: Run predeclared scenarios; record task success, time, wrong/missing evidence,
confusing controls, and desired exports; route true capability gaps back to the specification.
- Acceptance gates: Required scenarios reach cited results and expose review state; blockers are
classified as bug, data gap, policy gap, or new capability; no silent workaround is accepted.
- Documentation target: `docs/impl/current/discovery-visualization.md`
- Review checkpoint: `review-investigation-and-report-integrity`.

### Evaluation and evidence -- `evaluation-evidence`

#### authorize-full-corpus-run

Decide whether measured pilot quality, capacity, recovery, and review cost justify running the full
archive and which optional profiles are included.

- Serves: `evaluation-evidence` -- [Required acceptance gates](../design/spec.md#required-acceptance-gates)
- Agent status: HUMAN-GATED
- Dependencies: `run-representative-scale-pilots`; `test-failure-and-capacity-boundaries`;
`accept-recovery-and-security-posture`; `accept-operator-discovery-workflows`;
`approve-classification-operating-point`; `approve-fact-review-and-publication-policy`;
`approve-entity-merge-and-ontology-policy`; `approve-domain-artifact-semantics-and-inclusion`;
`approve-anomaly-triage-policy`; `review-production-readiness-and-recovery`.
`review-semantic-branch-integrity` only if the semantic branch is selected.
Archive placement authorization is independent.
- User-visible outcome: The multi-terabyte run begins with an explicit disk/time/risk budget and
selected lexical/vector/graph/model profiles, or is intentionally limited.
- Scope boundary: Authorization only; it does not weaken safety margins or imply cloud/HA scope.
- Data and artifact paths: Pilot capacity report, immutable profile ids, backup location,
`$RUNS_DIR/<run-id>/authorization/decision.yaml`.
- Execution path: Review forecast ranges, free space, expected duration, classification exceptions,
unsupported bytes, domain-artifact coverage, energy/review costs, recovery time, and negative-result
alternatives; record authorize-next, resize/reconfigure, subset-only, or stop.
- Acceptance gates: Decision names exact profile/contract/code pins, paths, minimum free-space
margin, stop conditions, backup, and responsible operator; an unapproved or stale pilot cannot
launch full scope.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

### Operational recovery -- `operational-recovery`

#### accept-recovery-and-security-posture

Witness a clean-target restore and review local access, secret, network, retention, and
removable-disk procedures before treating the system as the archive's working knowledge platform.

- Serves: `operational-recovery` --
[Operations, backup, and security](../design/spec.md#operations-backup-and-security)
- Agent status: HUMAN-GATED
- Dependencies: `harden-local-security-and-no-egress-mode`;
`implement-backup-restore-and-rebuild-runbook`; `test-failure-and-capacity-boundaries`.
- User-visible outcome: The owner knows what is backed up, what is rebuildable, how source
locations and review decisions are
restored, how long recovery takes, and which local risks remain accepted.
- Scope boundary: Owner acceptance of the documented single-host posture; not a certification of
high availability, enterprise support, or physical security.
- Data and artifact paths: Recovery report, security checklist, backup inventory, retention policy,
and local acceptance decision.
- Execution path: Observe restore, source lookup, artifact registry, and sampled query parity;
review ports, roles, mounts, source access, secrets, model/image provenance, backup
separation, retention, and emergency stop/restart commands; record residual risks.
- Acceptance gates: Restore evidence and residual-risk list are signed off or rejected; rejected
items return to the owning capability; Community ParadeDB HA limitations remain explicit.
- Documentation target: `docs/impl/current/operations.md`
- Review checkpoint: `review-production-readiness-and-recovery`.

### Graph-constrained agents -- `graph-constrained-agents`

#### accept-agent-diagnostic-scope

Decide whether the graph-constrained diagnostic is worth offering, and fix the language that keeps
its report from being read as archive quality evidence.

- Serves: `graph-constrained-agents` --
[Graph-constrained context and agent diagnostics](../design/spec.md#graph-constrained-context-and-agent-diagnostics)
- Agent status: HUMAN-GATED
- Dependencies: `prove-graph-constrained-agents-on-provided-archive`;
`approve-graph-analytics-operating-points`;
`accept-operator-discovery-workflows`.
- User-visible outcome: The owner accepts the diagnostic scope, budgets and reporting language, or
records that the branch stays unselected, with no ambiguity about what the coverage report measures.
- Scope boundary: Approve the diagnostic scope and its stated limits. This accepts no probe as a
gold question, no session claim as a fact, and no coverage figure as archive quality evidence.
- Data and artifact paths: `configs/agents/`, context, probe, session and coverage profile
fingerprints, and `$RUNS_DIR/<run-id>/review/agents/`.
- Execution path: Inspect sampled context packs with their budgets and drops, probes against the
snapshot, sessions with cited and abstained answers, injection samples, and the coverage report with
its non-measurement statement; judge whether the report is useful and unmistakable; record accept,
revise, or retain unselected.
- Acceptance gates: The exact profile, budget, model and snapshot fingerprints and the decision are
recorded; the accepted report language states what it does not measure; no acceptance gate in the
specification is allowed to consume the diagnostic output.
- Documentation target: `docs/impl/current/graph-constrained-agents.md`
- Review checkpoint: `review-agent-guardrail-integrity`.

### Separate archive organization -- `archive-organization`

#### approve-archive-organization-plan

Review the subject taxonomy, classification operating point, directory vocabulary, placement
mode, and one complete dry-run before any real archive reorganization.

- Serves: `archive-organization` --
[Separate archive organization utility](../design/spec.md#separate-archive-organization-utility)
- Agent status: HUMAN-GATED
- Dependencies: `prove-archive-organization-on-provided-artifacts`;
`approve-classification-operating-point`; verified move backup from
`implement-backup-restore-and-rebuild-runbook` only when move mode is selected.
`review-archive-organization-integrity`.
- User-visible outcome: The owner explicitly accepts which assignments may determine paths, chooses
between a copy into a target tree and an in-place move, and can `apply`, revise thresholds/slugs,
keep the mapping without placement, or stop.
- Scope boundary: Approve one versioned policy, mode, and plan; no automatic approval from
confidence, no licence waiver, and no mutation of the archive during review.
- Data and artifact paths: `configs/policy/classification.yaml`, vocabulary/licence manifest,
classification evaluation, `$RUNS_DIR/<run-id>/archive-reorganization/plan.json`, dry-run diff,
backup reference, and local decision ledger.
- Execution path: Present class and ancestor errors, `unclassified`/`unreadable` samples, coverage,
calibration, proposed ASCII paths, collisions/path lengths, placement counts/bytes, target free space
for `copy` against archive rewrite risk for `move`, source lookup, rollback drill, and taxonomy
licence; record the exact accepted fingerprints, mode, and decision.
- Acceptance gates: Decision is `apply`, `mapping-only`, `revise`, or `stop`; `apply` names the exact
classification and plan ids, mode, silo root and device, copy target or verified backup, stop
conditions, and responsible operator; stale or unapproved plans remain non-writable.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: `review-archive-organization-integrity`.

#### execute-authorized-archive-reorganization

Execute one authorized placement plan -- a copy into the target tree or an in-place move -- and prove
that every knowledge source still resolves afterwards.

- Serves: `archive-organization` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: HUMAN-GATED
- Dependencies: `approve-archive-organization-plan` for the recorded `apply` decision
and mode; `prove-archive-organization-on-provided-artifacts`;
`implement-backup-restore-and-rebuild-runbook` for the verified backup a `move` decision requires.
- User-visible outcome: The authorized silo is organized by its primary class hierarchy -- in a target
tree or in place -- and every document, fact, and report still resolves from its original path to its
current path.
- Scope boundary: Run only the exact accepted classification id, plan id, and mode, on the one silo
the decision names, into the target it names; never re-plan, widen scope, place blocked entries,
switch modes, or touch a silo the decision does not name. A `move` decision additionally requires its
verified backup. A `mapping-only`, `revise`, or `stop` decision closes this task with that recorded
result and no placement.
- Data and artifact paths: The declared copy target or the authorized writable silo root,
`$RUNS_DIR/<run-id>/archive-reorganization/{plan.json,ledger.parquet,journal/}`,
`corpus.document_path_event`, and the post-placement verification report.
- Execution path: Revalidate the plan fingerprint, mode, source paths, hashes, destinations, device,
and free space; confirm the backup reference for `move`; seal the ledger; apply journaled renames or
hash-verified copies; reconcile placed, blocked, and skipped counts against the plan; re-resolve a
sampled set of documents, facts, search citations, and registered artifacts through `archive locate`;
record timing, failures, and the rollback command that remains available.
- Acceptance gates: Placed and blocked entries account for the plan exactly with no overwrite and no
byte change; a `copy` run leaves every source byte and path intact; path events record initial and
current locations for every placed file; sampled knowledge sources resolve afterwards; an
interruption resumes or reverses only from the sealed ledger; a failed precondition refuses before
the first rename or copy.
- Documentation target: `docs/impl/current/archive-organization.md`
- Review checkpoint: `review-archive-organization-integrity`.
