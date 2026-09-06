# Contracts

Product ODCS `3.1.0` contracts under `contracts/` are the reviewable schema source of truth for
pipeline entities. `arxiv_int.contracts` loads, fingerprints, lints, and generates physical schemas
from that tree through rooted references, typed loaders, and schema-qualified evolution primitives.

## Product registry

`contracts/registry.yaml` binds each dataset id to an ODCS file, a physical-to-canonical mapping,
a canonical entity, and a reviewed semantic metadata hash. Shipped datasets cover documents, spans,
chunks, objects, aliases, mentions, facts, topics, ontology terms, embeddings, source occurrences,
transactions, catalogs, anomaly findings, and evaluation items.

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
generation adapters, golden fingerprints, Avro round-trip, SQL parse/apply, drift checking, and
Data Contract CLI lint when the CLI is available. Evidence:
[deterministic schema generation](../records/0011-contract-gov-implement-deterministic-schema-generation.md);
[canonical contract registry](../records/0010-contract-gov-establish-canonical-contract-registry.md);
[contract identity and reference validation](../records/0009-contract-gov-refactor-contract-identity-and-reference-validation.md).
