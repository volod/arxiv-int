# Task Record

## Task and scope

- Id / capability / checkpoint: `refactor-contract-identity-and-reference-validation` /
  `contract-governance` / `review-foundation-and-store-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `refactor-contract-identity-and-reference-validation`; code
  revision `9160244` with a clean working tree at task start.
- Initial count: 87 tasks (76 agent, 11 human).
- Accepted task:

```markdown
#### refactor-contract-identity-and-reference-validation

Prevent escaped canonical references and ambiguous field identities in existing contract primitives.

- Serves: `contract-governance` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-codebase-06, AUD-codebase-07](records/codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Quality baseline repair](records/restore-quality-gate-baseline.md); existing
[Contract primitives](current/project-foundation.md#contract-primitives).
- User-visible outcome: Every canonical file reference stays within its declared contract root, and distinct
schema-qualified fields cannot overwrite each other in compatibility snapshots.
- Scope boundary: Refactor current loaders/snapshots only; full ODCS adapters and schema generation remain
their existing tasks. Do not introduce a second semantic model or silently change stored hashes.
- Data and artifact paths: `src/arxiv_int/contracts/{canonical,registry,evolution,fingerprint}.py`,
`tests/contracts/`, and synthetic ODCS fixtures.
- Execution path: Reuse rooted reference validation for registry and canonical loaders; reject duplicate
or
ambiguous bindings and malformed known fields while preserving unknown metadata; define explicit
schema-qualified identity and reviewed migration behavior for existing snapshot fingerprints.
- Acceptance gates: Failing regressions cover parent/absolute/symlink escapes, repeated field names
in different
schemas, true duplicates, unknown metadata, deterministic snapshots and explicit compatibility
consequences; existing valid fixtures remain supported or receive a documented migration.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

`src/arxiv_int/contracts/paths.py` owns `resolve_rooted_reference()`. `FileRegistry` and
`load_canonical_model()` both resolve ODCS/mapping references through it. Absolute paths, empty
values, null bytes, parent traversal, and symlink targets outside the resolved root are refused.

`schema_snapshot()` now emits `fieldIdentity: schema-qualified` and keys fields as
`{schemaId}.{fieldName}`. Named schemas keep their names; unnamed schemas use stable `#N`
positional ids. Distinct schemas may share a field name. True duplicate field or schema identities
and nameless properties fail closed. `migrate_schema_snapshot()` upgrades an unambiguous
single-schema legacy bare-field baseline; comparing an unmigrated legacy snapshot to a qualified
snapshot is explicitly breaking. Stored semantic metadata hashes are unchanged for previously valid
documents.

Canonical bindings require `binding` and `semanticTerm` when present; unknown binding keys are not
rejected. Duplicate bound physical fields and reused binding strings fail closed. Fingerprints keep
unknown metadata in the hash, reject malformed known-shaped mappings, duplicate `sourceField`
values, and ambiguous repeated bindings.

Current-state behavior:
[Contracts](../current/contracts.md). Project foundation links that page from its contract
primitives section. No second semantic model and no ODCS product registry were introduced.

## Acceptance evidence

Commands use `DATA_DIR=/tmp/arxiv-int-contract-id`. Evidence is retained under
`$DATA_DIR/regression/20260906/`. Offline quality reused
`UV_CACHE_DIR=/tmp/arxiv-int-service-planning/cache/uv`.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| AUD-06/07 baseline before repair | `.venv/bin/python` reproduction; `baseline.txt` | Valid-negative: parent/absolute/symlink accepted; multi-schema `id` fields collapsed |
| Parent/absolute/symlink escapes | `tests/contracts/test_paths.py`, `test_canonical.py`, `test_registry.py` | All escape classes refused after symlink resolution |
| Distinct schema fields and duplicates | `tests/contracts/test_evolution.py` | `alpha.id` and `beta.id` retained; true duplicates refused |
| Legacy migration consequences | `test_legacy_snapshot_migration_and_unmigrated_breaking_consequence` | Migrated single-schema baseline is identical; unmigrated compare is breaking |
| Unknown metadata and bindings | `tests/contracts/test_fingerprint.py`, `test_rejects_duplicate_and_malformed_bindings` | Unknown keys preserved in hash; duplicates/malformed known fields refused; fixture hash unchanged |
| Existing valid fixtures | `tests/contracts/` | Registry/canonical/fingerprint happy paths still pass |
| Formatting and required CI | `make format`; `make ci DATA_DIR=/tmp/arxiv-int-contract-id`; `ci.txt` | Pass; 315 deterministic tests and all CI checks |
| Full quality | `UV_OFFLINE=1 UV_CACHE_DIR=/tmp/arxiv-int-service-planning/cache/uv make quality DATA_DIR=/tmp/arxiv-int-contract-id`; `quality.txt` | Pass; 315 tests, 92.45% coverage, Markdown, typing, complexity, shell, links, plan and wheel/sdist build |
| Doc/plan integrity | `make lint-doc-links`; `make lint-spec-plan` | Pass after plan removal and dependency retargeting |

Complexity on `_entity_fields` was split into `_schema_property_maps` and `_bound_field` without
weakening the gate. Fixtures are network-free and prove loader/snapshot behavior, not real-archive
or CUDA fit.

## Audit handoff

AUD-codebase-06 is resolved by shared rooted reference validation and escape regressions.
AUD-codebase-07 is resolved by schema-qualified snapshots, duplicate refusal, and documented
migration/breaking consequences.

Self-review covered loader containment, snapshot identity, hash stability, public exports,
documentation links and evidence-to-gate mapping. `none identified` beyond the documented legacy
migration requirement for existing bare-field baselines. No service, model job, port or external
resource was started.

## Close or resume

Accepted. Plan task removed; dependents now link this record. Counts moved from 87 to 86 tasks
(76 to 75 agent; 11 human unchanged). `contract-governance` gained rooted/identity guarantees; no
capability shipment status changed. Next agent work follows `make plan-status`.
