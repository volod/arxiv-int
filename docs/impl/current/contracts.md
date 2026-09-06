# Contracts

Product ODCS `3.1.0` contracts under `contracts/` are the reviewable schema source of truth for
pipeline entities. `arxiv_int.contracts` loads, fingerprints, lints, generates physical schemas, and
enforces evolution policy from that tree through rooted references, typed loaders, and
schema-qualified baselines.

## Product registry

`contracts/registry.yaml` binds each dataset id to an ODCS file, a physical-to-canonical mapping,
a canonical entity, and a reviewed semantic metadata hash. Shipped datasets cover documents, spans,
chunks, objects, aliases, mentions, facts, topics, ontology terms, embeddings, source occurrences,
transactions, catalogs, anomaly findings, evaluation items, and domain investigation artifact
families (relationship map, BOM, supply chain, invoice/payment, registry).

`make contracts` syncs the `contracts` extra and runs `arxiv-int contracts lint`, which:

1. validates every `datasets/*.odcs.yaml` against the vendored official ODCS JSON Schema at
   `contracts/odcs/odcs-json-schema-v3.1.0.json` (Bitol pin `f5bfbb8`);
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

`src/arxiv_int/contracts/generate/` exports Avro, PostgreSQL baseline DDL, JSON Schema, and Pydantic
models through Data Contract CLI first, then focused adapters for Parquet/Arrow descriptors,
partition stubs, ParadeDB search DDL, pgvector dimensions, AGE projection stubs, and provenance
sidecars. Outputs land under `contracts/generated/` with a `manifest.json` of file fingerprints.

Operator commands:

- `make contracts-gen` / `arxiv-int contracts generate` -- wipe and regenerate the committed tree
- `make contracts-check` / `arxiv-int contracts check` -- regenerate into a temp directory and fail
  on drift (also part of `make ci`)

Generation is byte-stable. Avro schemas parse and round-trip with `fastavro`. Baseline CREATE TABLE
SQL parses with `sqlglot` and applies on a disposable Postgres 16 container when Docker is
available. Extension SQL for BM25/AGE is committed for review but is not applied on stock Postgres.
Provenance sidecars retain ODCS id/version, semantic hash, and every `x-arxiv-int` key so source
metadata is not silently dropped. Some CLI Avro mappings (for example ODCS `number` to Avro
`bytes`) follow the exporter; logical types remain authoritative in ODCS and provenance.

## Evolution and migrations

Reviewed baselines under `contracts/evolution/<contract-id>.json` capture schema-qualified fields,
semantic fingerprints, generator/artifact hashes, and search/vector/graph projections. Policy
classification covers identical, additive, breaking, tokenizer reindex, vector-dimension,
semantic-retarget, and graph-projection consequences. Version rules fail closed (minor for additive/
reindex/graph; major for breaking/vector/semantic). Destructive SQL is never auto-approved.

Legacy SQL files live in `db/migrations/` using dbmate-shaped names; `db/schema.sql` is a
committed SQL snapshot. `make contracts-evolution` / `arxiv-int contracts evolution` checks baselines
against current contracts, Avro self-compatibility, migration order/approvals/dump coverage, optional
`dbmate status` when installed with `DATABASE_URL`, and disposable Postgres apply of baseline
CREATE TABLE SQL. Fixtures under `tests/contracts/evolution/` prove each consequence class.

These checks do not yet execute an owned migration history or compare a migrated live catalog to
contract metadata. Dump coverage checks table-name substrings; the conformance helper compares
unqualified column-name sets and the disposable probe applies baseline SQL only. Missing dbmate
does not fail the current check, and the destructive-statement regex/comment marker is a limited
lint, not proof of safe changes or approval. No SQLAlchemy/Alembic migration runner, dbt project,
Polars transformation layer, or Pandera dataset-validation adapter is implemented yet.

The [data engineering review](../records/0015-govern-review-data-engineering-tooling.md) records
these limits and the selected replacement design. The
[migration refactor](../plan.md#refactor-contract-schema-and-migration-tooling),
[shared data-quality checks](../plan.md#implement-contract-data-quality-checks), and
[dbt foundation](../plan.md#implement-dbt-transformation-foundation) own implementation. Existing
ODCS/JSON Schema/Pydantic, Avro and ontology validation remain available; they do not establish
whole-dataset quality or live migration acceptance.

## Versioned ontology assets

Pinned Turtle and SHACL assets under `ontology/` define the foundation and domain-investigation
vocabulary independently of AGE. `manifest.yaml` pins ontology id/version
`urn:arxiv-int:ontology:1.1.0` / `1.1.0`. `core.ttl` plus additive `domain.ttl` carry classes,
predicates, units, selected disjoint/functional constraints, and English/Russian labels;
`mappings.ttl` / `domain-mappings.ttl` link IRIs to canonical `urn:arxiv-int:term:*` vocabulary;
`shapes.shacl.ttl` / `domain.shacl.ttl` validate instance graphs.

`src/arxiv_int/ontology/` loads the catalog, validates fact assertions in application code, applies
domain investigation rules (`domain_rules.py`), runs pySHACL, and uses owlrl as a second reasoner
for disjointness probes. Deterministic `ontology/generated/ontology.*.json` bindings plus
`manifest.json` are regenerated by `make ontology-gen` / `arxiv-int ontology generate`.
`make ontology-check` / `arxiv-int ontology check` (also in `make ci`) parses RDF, verifies every
active predicate maps to canonical binding `fact.predicateId`, fails on generation drift, and
requires the reviewed `ontology/evolution/baseline.json`. Positive/negative fixtures under
`tests/ontology/` prove SHACL and application validation agree for foundation and domain
distinctions. The canonical model records `ontologyRef` / `ontologyVersion` in
`contracts/canonical/model.yaml`.

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
evolution fixtures/migrations, and Data Contract CLI lint when the CLI is available.
`tests/ontology/` covers RDF parse, binding coverage, SHACL/application agreement, owlrl
disjointness, ontology evolution classes, and domain investigation fixtures. Evidence:
[domain investigation contracts](../records/0014-contract-gov-define-domain-investigation-contracts-and-ontology.md);
[versioned ontology assets](../records/0013-contract-gov-establish-versioned-ontology-assets.md);
[evolution and migration policy](../records/0012-contract-gov-enforce-evolution-and-migration-policy.md);
[deterministic schema generation](../records/0011-contract-gov-implement-deterministic-schema-generation.md);
[canonical contract registry](../records/0010-contract-gov-establish-canonical-contract-registry.md);
[contract identity and reference validation](../records/0009-contract-gov-refactor-contract-identity-and-reference-validation.md).
