# Contracts

Product ODCS `3.1.0` contracts under `contracts/` are the reviewable schema source of truth for
pipeline entities. `arxiv_int.contracts` loads, fingerprints, and lints that tree through rooted
references, typed loaders, and schema-qualified evolution primitives.

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
keys). Dataset-level `x-arxiv-int` carries postgres `schema`/`table` (and optional `partitionKey`).
Legacy top-level `canonicalBinding` properties remain accepted for fixtures.

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
registry integrity, typed loader unknown-metadata retention, canonical `x-arxiv-int` bindings, and
Data Contract CLI lint when the CLI is available. Evidence:
[canonical contract registry](../records/establish-canonical-contract-registry.md);
[contract identity and reference validation](../records/refactor-contract-identity-and-reference-validation.md).
