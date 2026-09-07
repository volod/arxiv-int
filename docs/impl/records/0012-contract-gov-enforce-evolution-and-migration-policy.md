# Task Record

## Task and scope

- Id / capability / checkpoint: `enforce-evolution-and-migration-policy` /
  `contract-governance` / `review-foundation-and-store-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `enforce-evolution-and-migration-policy`; code revision
  `11b2305` with accepted deterministic schema generation present.
- Initial count: 84 tasks (73 agent, 11 human).
- Accepted task:

```markdown
#### enforce-evolution-and-migration-policy

Add reviewed schema/semantic baselines, compatibility classification, ordered SQL migrations, and
live-store conformance checks.

- Serves: `contract-governance` -- [Evolution and migrations](../design/spec.md#evolution-and-migrations)
- Agent status: CLEAR
- Dependencies: [Deterministic schema generation](records/0011-contract-gov-implement-deterministic-schema-generation.md).
- User-visible outcome: Breaking, reindexing, and graph-rebuild consequences are reported before a
schema change can reach data.
- Scope boundary: Detect, classify, and prepare migrations; never auto-approve destructive or
table-rewriting changes.
- Data and artifact paths: `contracts/evolution/`, `db/migrations/`, `db/schema.sql`,
`src/arxiv_int/contracts/evolution.py`, and `tests/contracts/evolution/`.
- Execution path: Extend the existing adjacent-history and semantic-fingerprint primitives; invoke
Avro reader/writer compatibility and Data Contract CLI breaking checks; integrate dbmate; compare
generated baseline, migration dump, and live information schema.
- Acceptance gates: Fixtures prove identical, additive, breaking, tokenizer/reindex,
vector-dimension, semantic-retarget, and graph-projection cases; version rules fail closed;
out-of-order migrations and drift fail CI.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Converted `contracts/evolution` into a package: core field snapshots/version policy, projection and
semantic consequence classification, reviewed baselines under `contracts/evolution/*.json`, Avro
reader/writer self-compatibility, Data Contract CLI `breaking` wrapper, dbmate-shaped migration
ordering with destructive-approval markers, `db/schema.sql` dump coverage, and disposable Postgres
CREATE TABLE apply. Operator entrypoints: `arxiv-int contracts evolution` and
`make contracts-evolution` (also in `make ci`). Initial migration
`db/migrations/20260906120000_baseline_contract_tables.sql` mirrors generated baseline tables.
Fixtures under `tests/contracts/evolution/` cover every required consequence class. Current-state:
[Contracts](../current/contracts.md).

## Acceptance evidence

Commands use `DATA_DIR=/tmp/arxiv-int-evolution`. Evidence is under
`$DATA_DIR/regression/20260906/`.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Identical/additive/breaking/reindex/vector/semantic/graph fixtures | `tests/contracts/evolution/test_policy_fixtures.py` | Pass; all seven classes + fail-closed version bumps |
| Version rules fail closed | fixture version-policy parametrization | Pass |
| Out-of-order / destructive migrations | `test_migrations_and_product.py` | Pass; duplicate timestamps and DROP without approval refused |
| Product baselines + Avro + migration dump | `make contracts-evolution`; product tests | Pass; 15 contracts identical to baselines |
| Disposable live SQL apply | `contracts evolution` without `--skip-live-sql` | Pass when Docker available |
| Data Contract CLI breaking (identical) | `test_datacontract_breaking_identical_files` | Pass when CLI on PATH |
| Formatting and required CI | `make format`; `make ci DATA_DIR=/tmp/arxiv-int-evolution`; `ci.txt` | Pass; 377+ tests, contracts-check + contracts-evolution |
| Full quality | `UV_OFFLINE=1 make quality DATA_DIR=/tmp/arxiv-int-evolution`; `quality.txt` | Pass; 387 tests, 90.30% coverage, Markdown, typing, complexity, shell, links, plan, build |

Fixtures and disposable Docker prove policy correctness, not real-archive quality or CUDA fit.
dbmate binary is optional; ordering/approval/dump checks run in Python; `dbmate status` runs when
installed with `DATABASE_URL`.

## Audit handoff

none identified

## Close or resume

Accepted. Remaining open contract-governance work starts at `establish-versioned-ontology-assets`.
Final count after plan removal: 83 tasks (72 agent, 11 human).
