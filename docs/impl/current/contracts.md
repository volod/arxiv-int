# Contracts

Product ODCS `3.1.0` contracts under `src/arxiv_int/resources/contracts/` are the reviewable schema
source of truth for pipeline entities. `arxiv_int.contracts` loads, fingerprints, lints, generates
physical schemas, and enforces evolution policy from that packaged tree through rooted references,
typed loaders, and schema-qualified baselines. Checkout overlays named `contracts/` win when a
caller passes a temporary project root.

## Product registry

`src/arxiv_int/resources/contracts/registry.yaml` binds each dataset id to an ODCS file, a
physical-to-canonical mapping,
a canonical entity, and a reviewed semantic metadata hash. Shipped datasets cover documents, spans,
chunks, objects, aliases, mentions, facts, topics, ontology terms, embeddings, source occurrences,
document path events,
transactions, catalogs, anomaly findings, evaluation items, classification scheme classes, file
classifications, and domain investigation artifact families (relationship map, BOM, supply chain, invoice/payment,
registry).

`make contracts` syncs the `contracts` extra and runs `arxiv-int contracts lint`, which:

1. validates every `datasets/*.odcs.yaml` against the vendored official ODCS JSON Schema at
   `src/arxiv_int/resources/contracts/odcs/odcs-json-schema-v3.1.0.json` (Bitol pin `f5bfbb8`);
2. checks unique ids/versions, rooted references, canonical bindings, relationship targets, and
   required primary-key identities;
3. runs Data Contract CLI lint with the same official schema via `uv tool run` when available.

## Project extension

Generation and binding hints live under ODCS `customProperties` with property name `x-arxiv-int`.
Field bindings nest at `x-arxiv-int.canonicalBinding` (`binding`, `semanticTerm`, plus unknown
keys). Dataset-level `x-arxiv-int` carries postgres `schema`/`table` (and optional `partitionKey`),
plus optional `search`, `vector`, and `graph` generation hints. Legacy top-level `canonicalBinding`
properties remain accepted for fixtures.

## Deterministic generation

`src/arxiv_int/contracts/generate/` exports Avro, JSON Schema, and Pydantic models through Data
Contract CLI, then focused adapters for Parquet/Arrow descriptors, partition templates, ParadeDB
search DDL, pgvector dimensions, AGE projection stubs, and provenance sidecars. PostgreSQL DDL is no
longer a generic CLI export: `src/arxiv_int/contracts/catalog/normalize.py` normalizes ODCS into typed
`NormalizedTable`/`NormalizedColumn` definitions. `src/arxiv_int/contracts/sqlalchemy/` builds one
schema-qualified SQLAlchemy Core `MetaData` from that model with a shared naming convention, and
compiles review DDL with the PostgreSQL dialect.
Per-contract files land at `src/arxiv_int/resources/contracts/generated/postgres/<id>.sql` and the
ordered owned-schema
script at `src/arxiv_int/resources/contracts/generated/postgres/baseline.sql`, beside a
`manifest.json` of fingerprints.

Types, decimal precision/scale, nullability, primary keys, declared relationships, unique
constraints, and descriptions survive into the metadata; descriptions are emitted as `COMMENT ON`
statements. A declared `x-arxiv-int.partitionKey` becomes an explicit column instead of a separate
`ALTER TABLE`. Unsupported metadata -- an unknown `logicalType`, unknown property or
`logicalTypeOptions` keys, a non-`foreignKey` relationship, a target outside the registry, a missing
primary key, duplicate key positions, a duplicate schema identity, or a duplicate physical binding --
raises `UnsupportedContractMappingError` rather than being dropped.

Operator commands:

- `make contracts-gen` / `arxiv-int contracts generate` -- wipe and regenerate the committed tree
- `make contracts-check` / `arxiv-int contracts check` -- regenerate into a temp directory and fail
  on drift (also part of `make ci`)

Generation is byte-stable. Avro schemas parse and round-trip with `fastavro`. Compiled DDL parses
with `sqlglot`. Ordered `baseline.sql` apply on a disposable Postgres 16 container is
`make contracts-evolution-live` / `arxiv-int contracts evolution` (not part of `make ci`).
Extension SQL for BM25/AGE is committed for review but is not applied on stock Postgres.
Provenance sidecars retain ODCS id/version, semantic hash, and every `x-arxiv-int` key so source
metadata is not silently dropped. Some CLI Avro mappings (for example ODCS `number` to Avro
`bytes`) follow the exporter; logical types remain authoritative in ODCS and provenance.

## Evolution and migrations

Reviewed baselines under `src/arxiv_int/resources/contracts/evolution/<contract-id>.json` capture
schema-qualified fields,
semantic fingerprints, generator/artifact hashes, and search/vector/graph projections. Policy
classification covers identical, additive, breaking, tokenizer reindex, vector-dimension,
semantic-retarget, and graph-projection consequences. Version rules fail closed (minor for additive/
reindex/graph; major for breaking/vector/semantic). Destructive SQL is never auto-approved.

Alembic owns the revision graph, applied version state, and upgrade/downgrade execution.
`src/arxiv_int/migrations/` holds the environment and immutable Python revisions;
`revision_manifest.json` pins each revision file checksum and `head_state.json` records the owned
schema state the history produces. `src/arxiv_int/contracts/migrations/` implements the workflow:

- `arxiv-int db revision --message ...` / `make db-revision MESSAGE=...` diffs contract metadata
  against the frozen head state and writes a candidate revision with literal `op.*` operations,
  `CONTRACT_FINGERPRINTS`, and `REVIEW_NOTES`. Nothing is written when nothing changed.
- `arxiv-int db check` / `make db-check` (part of `make ci`) checks parents, cycles, a single head,
  revision-file checksums, head-state agreement, and any contract change lacking a revision.
- `arxiv-int db status|upgrade|downgrade` / `make db-status|db-upgrade|db-downgrade` act only on the
  database named by `ARXIV_INT_MIGRATION_DATABASE_URL`. Credentials are redacted in every message.
- `arxiv-int db upgrade --sql` writes offline review SQL under `$DATA_DIR/migrations/<run-id>/`.
- `arxiv-int db adopt` / `make db-adopt` live-adopts when that URL is set: relocates leftover
  `public` tables into owned schemas when destinations are missing, refuses partial or drifted
  catalogs, and stamps `0001` when the overlay matches the current initial revision. Without a URL
  it reports why stamping stays refused. A proved current overlay stamps the reviewed head.

Generated revisions are deterministic and frozen: a historical revision never imports today's
contracts, and editing one after review fails the checksum gate. A revision that drops an owned table
or column renders an irreversible `downgrade()` naming the recovery path and carries review notes
that a removal is not an inferred rename. `arxiv_int.contracts.sqlalchemy.catalog` compares a live
catalog to contract metadata by compiled column definitions, keys, references, checks, defaults and
declared indexes, restricted to owned tables; previously owned names are retained so deletions are
not hidden by that exclusion.
Autogeneration against a live database uses the same owned-object filter through the Alembic
environment.

Before any deployment or public release, the operator authorized consolidation into the single
`0001_initial_store.py` revision. It freezes the complete current store; generated catalog JSON is
retained only as per-run evidence under `DATA_DIR`, not as a second committed schema authority.
The [boundary repair](../records/0028-store-refactor-foundation-store-acceptance-boundaries.md)
and [prerelease consolidation](../records/0052-store-refactor-prerelease-migration-consolidation.md)
record the amendment. Historical task snapshots describe their original implementation; their
superseded revision numbers are not upgrade requirements for this unreleased baseline. Head
is `0003`: additive revision `0002` creates `corpus.classification_classes`, and reviewed additive
revision `0003` creates the partitioned `corpus.file_classification` mapping and classification
staging tables. Overlay tables
briefly authored as development-era revisions now live in the initial revision, as documented in
[Canonical store](canonical-store.md).

Live initial schema, HASH partitions, roles, staging COPY, and disposable apply evidence are
documented in [Canonical store](canonical-store.md). Offline evolution checks still do not stamp an
operator database by themselves. Missing live evidence is reported as `not-run`, never as a pass.
Whole-relation dbt execution is recorded in
[Canonical store](canonical-store.md#relational-transformations).

`make contracts-evolution` (part of `make ci`) checks baselines against current contracts, Avro
self-compatibility, and the migration report, and skips disposable Postgres. `make
contracts-evolution-live` / `arxiv-int contracts evolution` also applies `baseline.sql`. The pytest
case for that apply is marked `heavy`. Fixtures under `tests/contracts/evolution/` prove each
consequence class.

The [data engineering review](../records/0015-govern-review-data-engineering-tooling.md) records the
selected design; the
[migration refactor record](../records/0017-contract-gov-refactor-contract-schema-and-migration-tooling.md)
records SQLAlchemy/Alembic ownership; the
[data-quality record](../records/0019-contract-gov-implement-contract-data-quality-checks.md)
records dataset checks; the
[Pandera concat pin](../records/0030-contract-gov-upgrade-pandera-polars-concat-compat.md)
keeps those batch checks warning-free on current Polars; the
[duplicate SQL retirement](../records/0020-contract-gov-retire-duplicate-dbmate-sql.md)
removes the leftover `db/` tree and SQL-dump inventory; the
[canonical relational schema record](../records/0021-store-create-canonical-relational-schema.md)
records live overlay apply and adoption on the pinned store; the
[dbt transformation foundation](../records/0024-store-implement-dbt-transformation-foundation.md)
records local model build/test and isolated derived generations.

## Dataset quality checks

`src/arxiv_int/data_quality/` compiles the same normalized ODCS fields used for SQLAlchemy into a
stable rule catalog. Generation writes
`src/arxiv_int/resources/contracts/generated/quality/<id>.rules.json` and
`src/arxiv_int/resources/contracts/generated/dbt/{<id>.yml,sources.yml}` beside other physical
artifacts; fingerprints
enter provenance sidecars and `manifest.json`. `GENERATOR_VERSION` is `2.1.0`. Generated generic
dbt tests nest arguments under `arguments` so dbt Core 1.12 can compile them.

Batch rules (type, nullability, max length, decimal, accepted values, unit companions, and
in-batch uniqueness) run against eager Polars frames through Pandera/Polars. Snapshot uniqueness
and relationships are declared as dbt tests and executed by a disk-backed Polars adapter; skipping
them leaves `not-run` and cannot be publishable. LazyFrame schema-only validation is refused.
Unknown ODCS `quality` types, engines, or rules fail closed at compile time.

`arxiv-int data-quality check DATASET --run-id RUN_ID --input PATH` and `make data-quality`
write secret-free evidence under `$DATA_DIR/data-quality/<run-id>/`. `--publish` copies the same
JSON to `$RUNS_DIR/<run-id>/quality/`. A result is publishable only after required data checks
executed and passed; missing, unexecuted, failed, or schema-only outcomes stay inspectable and
blocked. The `data-quality` extra carries pinned Pandera `0.33.1`; Polars/PyArrow stay in `lake`
with Polars `>=1.20`. CLI and core
paths that do not validate data do not import them. Producers attach ontology/SHACL results;
unattached required semantic checks are explicit `not-run`. Fixture tests make no held-out model
or real-archive quality claim. Whole-relation dbt execution uses the runner in
[Canonical store](canonical-store.md#relational-transformations); this adapter does not invoke dbt.

## Versioned ontology assets

Pinned Turtle and SHACL assets under `src/arxiv_int/resources/ontology/` define the foundation and domain-investigation
vocabulary independently of AGE. `manifest.yaml` pins ontology id/version
`urn:arxiv-int:ontology:1.1.0` / `1.1.0`. `core.ttl` plus additive `domain.ttl` carry classes,
predicates, units, selected disjoint/functional constraints, and English/Russian labels;
`mappings.ttl` / `domain-mappings.ttl` link IRIs to canonical `urn:arxiv-int:term:*` vocabulary;
`shapes.shacl.ttl` / `domain.shacl.ttl` validate instance graphs.

`src/arxiv_int/ontology/` loads the catalog, validates fact assertions in application code, applies
domain investigation rules (`domain_rules.py`), runs pySHACL, and uses owlrl as a second reasoner
for disjointness probes. Deterministic `src/arxiv_int/resources/ontology/generated/ontology.*.json`
bindings plus
`manifest.json` are regenerated by `make ontology-gen` / `arxiv-int ontology generate`.
`make ontology-check` / `arxiv-int ontology check` (also in `make ci`) parses RDF, verifies every
active predicate maps to canonical binding `fact.predicateId`, fails on generation drift, and
requires the reviewed `src/arxiv_int/resources/ontology/evolution/baseline.json`. Positive/negative
fixtures under
`tests/ontology/` prove SHACL and application validation agree for foundation and domain
distinctions. The canonical model records `ontologyRef` / `ontologyVersion` in
`src/arxiv_int/resources/contracts/canonical/model.yaml`.

## Domain investigation contracts

Product ODCS datasets `domain-artifacts-relationship-map`, `domain-artifacts-bom`,
`domain-artifacts-supply-chain`, `domain-artifacts-invoice-payment`, and
`domain-artifacts-registry` define tabular outputs for relationship edges, BOM lines, supply-chain
stages, invoice/payment/allocation rows, and the run artifact registry. Canonical entities
`domain_relationship`, `bom_line`, `supply_chain_edge`, `invoice_payment_row`, and
`domain_artifact_registry` bind fields under `x-arxiv-int`. Ontology predicates distinguish
`part-of` from `references`, explicit from candidate ownership, payment allocation from
amount/date similarity, and same-name association from identity. Creation statuses are
`produced`, `partial`, `empty`, and `failed` (`empty` is the valid negative result). Fixtures under
`tests/ontology/domain_fixtures/` encode those separations.

## Loaders and primitives

Pydantic loaders in `loaders.py` preserve unknown metadata (`extra="allow"`). Rooted reference
validation, schema-qualified snapshots, semantic fingerprints, and binding uniqueness remain as
documented below. Readiness loads the shipped registry and verifies reviewed fingerprints when the
`contracts` feature group is installed.

## Rooted references

`resolve_rooted_reference()` is the single containment check for file references under a declared
contract root. Both `FileRegistry` and `load_canonical_model()` resolve ODCS and mapping paths
through it. References must be non-empty relative paths. Absolute paths, parent traversal, null
bytes, and symlink targets that resolve outside the root are refused after symlink resolution.

## Schema-qualified snapshots

`schema_snapshot()` emits `fieldIdentity: schema-qualified` and keys every field as
`{schemaId}.{fieldName}`. Legacy bare-field baselines migrate through `migrate_schema_snapshot()`;
unmigrated compares classify as breaking. Stored semantic metadata hashes are not rewritten by that
structural upgrade.

## Tests and verification

`tests/contracts/` covers primitive containment and identity, product ODCS schema validation,
registry integrity, typed loader unknown-metadata retention, canonical `x-arxiv-int` bindings,
generation adapters, golden fingerprints, Avro round-trip, SQL parse/apply, drift checking,
evolution fixtures, and Data Contract CLI lint when the CLI is available. Nested suites follow
the production packages: `tests/contracts/catalog/`, `tests/contracts/lint/`,
`tests/contracts/generate/`, `tests/contracts/sqlalchemy/`, `tests/contracts/migrations/`, and
`tests/contracts/evolution/`. `tests/resources/` covers packaged-asset resolution and checkout
overlays.
`tests/contracts/sqlalchemy/` covers normalization refusals, metadata collisions, type coverage,
deterministic DDL, and catalog comparison; `tests/contracts/migrations/` covers frozen state diffs,
deterministic revision rendering, irreversible downgrades, checksum immutability, multiple heads,
cycles, missing parents, missing runner, offline SQL, and adoption refusal.
`tests/ontology/` covers RDF parse, binding coverage, SHACL/application agreement, owlrl
disjointness, ontology evolution classes, and domain investigation fixtures. Evidence:
[domain investigation contracts](../records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
[versioned ontology assets](../records/0013-contract-gov-establish-versioned-ontology-assets.md);
[contract schema and migration tooling](../records/0017-contract-gov-refactor-contract-schema-and-migration-tooling.md);
[evolution and migration policy](../records/0012-contract-gov-enforce-evolution-and-migration-policy.md);
[deterministic schema generation](../records/0011-contract-gov-implement-deterministic-schema-generation.md);
[canonical contract registry](../records/0010-contract-gov-establish-canonical-contract-registry.md);
[contract identity and reference validation](../records/0009-contract-gov-refactor-contract-identity-and-reference-validation.md).
