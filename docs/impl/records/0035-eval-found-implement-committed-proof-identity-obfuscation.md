# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-committed-proof-identity-obfuscation` /
  `evaluation-foundation` / `review-inference-and-evaluation-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `implement-committed-proof-identity-obfuscation`; code revision
  `029aeb6` with a clean working tree at task start. Initial count: 80 tasks (70 agent, 10 human).
- Amendments: none.

```markdown
#### implement-committed-proof-identity-obfuscation

Prepare repeatable identity-obfuscated copies of proof artifacts intended for Git.

- Serves: `evaluation-foundation` -- [Committed proof identities](../design/spec.md#identity-obfuscation-for-committed-proof-artifacts)
- Agent status: CLEAR
- Dependencies: [Bundle validation](records/0033-eval-found-refactor-evaluation-bundle-validation.md);
[Contract data-quality checks](records/0019-contract-gov-implement-contract-data-quality-checks.md).
- User-visible outcome: Reviewable proof fixtures can enter Git without original person, company,
product, address, contact or account identities; the same inputs reproduce the same export.
- Scope boundary: Explicit Git-bound export copies only, including newly prepared untracked files.
Do not mutate archive silos, local proofs, canonical records, human-review packets or Git history.
No commit, strong cryptography, key management or external identity service is part of this task.
- Data and artifact paths: `src/arxiv_int/evaluation/`, `configs/evaluation/`, `tests/evaluation/`,
explicit repository export destinations, and `$DATA_DIR/proof-export/<run-id>/` diagnostics.
- Execution path: Reuse the immutable bundle verifier and shared artifact/contract validation.
Implement versioned SHA-256 namespaces and normalization, stable entity/field substitutions,
format-preserving phone/address/account rendering, collision refusal and a complete reference map.
Rewrite selected text/metadata/labels/queries and anchors together; regenerate checksums/manifests.
Keep raw maps local; render binary exports from transformed data or refuse unsupported formats.
Expose the exporter through the normal CLI with explicit source bundle and Git-bound file list.
- Acceptance gates: Repeated runs from different roots/orderings are identical; same-name entities
remain distinct; aliases, shared contacts, graph references and spans remain consistent; field
formats/check digits validate; collisions and residual source identities refuse export. Original
bytes remain unchanged and local-only artifacts are untouched. Geotemporal/domain fixture meaning
and expected answers remain consistent; transformed metrics are not labelled raw-archive results.
- Documentation target: `docs/impl/current/evaluation-foundation.md`
- Review checkpoint: `review-inference-and-evaluation-boundaries`.
```

## Implementation

`export_proof_bundle()` verifies a source run bundle, loads optional `identities.json`, and writes
explicit Git-bound copies. Policy `arxiv-int.proof-identity.v1` hashes NFKC-normalized values under
public namespace `arxiv-int/proof-identity/v1`. Entity labels use stable ids; shared emails, phones,
addresses and accounts use typed field values. Phone punctuation and prefixes are preserved; Luhn,
IBAN and INN check digits are recomputed. Same-name entities stay distinct via spans or JSON
`entity_id`/`id` binding. The source tree, local-only artifacts and human packets are not rewritten.
`identities.json` and unsupported binaries cannot be exported. Exported manifests record
`data_class=transformed`. The complete map stays under `$DATA_DIR/proof-export/<run-id>/`.

CLI: `arxiv-int evaluation export-proof` and `identity-policy generate|check`. Make:
`proof-export` and `identity-policy-check` (the latter is part of `make ci`). Committed policy:
`configs/evaluation/proof-identity-policy.json`.

Current state: [Evaluation foundation](../current/evaluation-foundation.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Cross-root/order determinism | `tests/evaluation/test_exporter.py::test_repeated_exports_from_different_roots_and_orderings_match` | pass |
| Same-name, joins, formats, geotemporal | `test_export_preserves_joins_formats_and_geotemporal_meaning`; `test_export_rewrite.py`; `test_export_render.py` | pass; dates/coords/qty kept; Luhn/IBAN/INN valid |
| Collision and leak refusal | `test_substitution_collision_is_refused`; `test_residual_identities_and_identity_catalog_export_are_refused` | pass |
| Original bytes and local-only | `test_original_bundle_and_local_only_artifacts_stay_untouched`; destination-inside-source refusal | pass |
| Binary refusal | `test_unsupported_binary_is_refused` | pass; PNG not copied |
| CLI and policy drift | `test_cli_export_and_policy_commands`; `make identity-policy-check` | pass |
| Synthetic DATA_DIR run | `$DATA_DIR/proof-export/0035/summary.json` | pass; export fingerprint `288cc9f609b3186723517a94c629b93ea4d1ebab86ebb95d878f1e28952de8d2` replayed from a second root; source fingerprint `e2450041f828583b8cf159eca65a88a55f0e509d8c580ddbfaccd91719162ebe`. Fixture tree, not a provided-archive proof |
| Required CI | `make ci` | pass; 875 passed, 20 skipped; format, lint, typing, complexity, doc-links, spec-plan, contracts, ontology, inference schemas, identity-policy check |

## Audit handoff

none identified. Scope stayed on Git-bound export copies. Ontology/geotemporal contract
implementation remains with `implement-ontology-snapshots-and-geotemporal-contracts`. Fixture
publication remains with `create-evaluation-fixtures-and-metrics`. The inference/evaluation
checkpoint owns cross-module export integration.

## Close or resume

All required gates passed: deterministic export regressions, synthetic
`$DATA_DIR/proof-export/0035/` evidence, documentation, `make lint-doc-links`,
`make lint-spec-plan`, and `make ci` (875 passed, 20 skipped). No gate is outstanding.
Next action: none for this task. Plan counts: 80 tasks before, 79 after (agent lane 70 to 69;
human 10 unchanged). Capabilities changed: none added or removed; `evaluation-foundation` remains
planned. Dependents now link this record. Next agent work:
`create-evaluation-fixtures-and-metrics`. No commit or push was made.
