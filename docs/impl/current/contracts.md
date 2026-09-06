# Contract primitives

`arxiv_int.contracts` owns the dependency-light registry, canonical loader, semantic fingerprint,
and schema-evolution primitives that later ODCS adapters and generators extend. Product contract
trees are not shipped yet; readiness reports that absence as ready. These primitives are the
portable foundation those trees must use.

## Rooted references

`resolve_rooted_reference()` is the single containment check for file references under a declared
contract root. Both `FileRegistry` and `load_canonical_model()` resolve ODCS and mapping paths
through it. References must be non-empty relative paths. Absolute paths, parent traversal, null
bytes, and symlink targets that resolve outside the root are refused after symlink resolution.
Valid relative children continue to load unchanged.

## Canonical bindings

`load_canonical_model()` reads `model.yaml` and rooted entity contracts. A present
`canonicalBinding` custom property must be a mapping with `binding` and `semanticTerm`. Unknown
keys on that mapping are ignored by the typed field model rather than rejected. Duplicate physical
field names that both carry bindings, and the same binding string reused by multiple fields, fail
closed as ambiguous identity.

## Semantic fingerprints

`semantic_metadata_hash()` hashes normalized contract metadata and field mappings. Unknown metadata
keys remain part of the hash. Known-shaped field mappings without `sourceField`, repeated
`sourceField` values, and repeated binding strings are refused. Cosmetic `metadata.domain` stays
excluded. Existing fixture hashes are unchanged for previously valid documents.

## Schema-qualified snapshots

`schema_snapshot()` emits `fieldIdentity: schema-qualified` and keys every field as
`{schemaId}.{fieldName}`. Declared schema `name` values are preferred; unnamed schemas use stable
positional ids such as `#0`. Distinct schemas may share a field name without collapsing. True
duplicate identities, duplicate schema identities, and properties without names are refused.

Legacy baselines that keyed fields by bare name lack `fieldIdentity`. Comparing them to a
schema-qualified snapshot without migration reports every field as removed and re-added, which
`classify_change()` classifies as breaking. `migrate_schema_snapshot(snapshot, schema_id=...)`
upgrades an unambiguous single-schema legacy snapshot; mixed or already-looking-qualified legacy
keys are refused. Stored semantic metadata hashes are not rewritten by this structural upgrade.
Re-freeze or migrate reviewed baselines before compatibility checks.

## Tests and verification

`tests/contracts/` covers rooted parent/absolute/symlink escapes for registry and canonical loaders,
schema-qualified snapshots, true duplicates, legacy migration and unmigrated breaking
consequences, fingerprint unknown-metadata preservation, and duplicate/ambiguous binding refusal.
Evidence for the identity repair:
[contract identity and reference validation](../records/refactor-contract-identity-and-reference-validation.md).
