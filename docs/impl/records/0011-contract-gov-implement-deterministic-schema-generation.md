# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-deterministic-schema-generation` /
  `contract-governance` / `review-foundation-and-store-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `implement-deterministic-schema-generation`; code revision
  `5236d4a` with accepted canonical registry present.
- Initial count: 85 tasks (74 agent, 11 human).
- Accepted task:

```markdown
#### implement-deterministic-schema-generation

Generate physical schemas and model boundaries from ODCS while minimizing custom generator code.

- Serves: `contract-governance` -- [Generation](../design/spec.md#generation)
- Agent status: CLEAR
- Dependencies: [Canonical contract registry](records/establish-canonical-contract-registry.md).
- User-visible outcome: One contract change reproducibly updates Avro, Arrow/Parquet, PostgreSQL
baseline, search, graph, and structured-output schemas.
- Scope boundary: Generate baseline artifacts and extension DDL; do not apply migrations to an
existing database.
- Data and artifact paths: `contracts/generated/{avro,parquet,postgres,jsonschema,graph}/`,
`src/arxiv_int/contracts/generate/`, and `tests/contracts/golden/`.
- Execution path: Use Data Contract CLI exporters first; add focused adapters for partitions,
ParadeDB tokenizers/indexes, vector dimensions, AGE projections, provenance metadata, and
Pydantic/JSON Schema; normalize ordering and fingerprints.
- Acceptance gates: Generation is byte-stable; `make contracts-gen` and drift check pass; Avro
parses and round-trips; generated SQL parses against a disposable database; no source contract
metadata is silently lost.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Replaced the placeholder generator module with `src/arxiv_int/contracts/generate/`: Data Contract
CLI exporters (Avro, PostgreSQL DDL, JSON Schema, Pydantic), focused adapters (Parquet descriptors,
partition stubs, ParadeDB search, pgvector, AGE stubs, provenance), normalize/fingerprint helpers,
and disposable SQL validation. Dataset-level `x-arxiv-int` hints cover search (documents/chunks),
vector (embeddings), and graph (objects/facts).

Committed `contracts/generated/` (111 files plus `manifest.json`) for all 15 registered contracts.
Operator entrypoints: `arxiv-int contracts generate|check`, `make contracts-gen` /
`make contracts-check` (also in `make ci`). The `contracts` extra adds `fastavro` and `sqlglot`.
Golden fingerprints live under `tests/contracts/golden/`. Current-state page:
[Contracts](../current/contracts.md).

## Acceptance evidence

Commands use `DATA_DIR=/tmp/arxiv-int-contracts-gen`. Evidence is under
`$DATA_DIR/regression/20260906/`. Data Contract CLI `1.1.3` was on PATH for export and drift
checks.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Byte-stable generation | two regenerations compared; `make contracts-check`; `stability.txt` | Pass; 0 mismatches |
| `make contracts-gen` / drift | `contracts-check.txt`; `test_generation_drift_check_passes_for_committed_tree` | Pass; committed tree matches regen |
| Avro parse and round-trip | `test_committed_avro_schemas_parse_and_round_trip`; `avro-roundtrip.txt` | Pass; all 15 `.avsc` schemas |
| SQL parse / disposable DB | `test_baseline_postgres_sql_*`; `sql-validate.txt` | Pass; sqlglot + Docker `postgres:16-alpine` |
| No silent metadata loss | provenance sidecars; `test_provenance_retains_source_contract_metadata` | Pass; ODCS id/version/extension keys retained |
| Formatting and required CI | `make format`; `make ci DATA_DIR=/tmp/arxiv-int-contracts-gen`; `ci.txt` | Pass; 338 tests |
| Full quality | `UV_OFFLINE=1 make quality DATA_DIR=/tmp/arxiv-int-contracts-gen`; `quality.txt` | Pass; 338 tests, 90.71% coverage, Markdown, typing, complexity, shell, links, plan, build |

Fixtures and disposable Docker prove generator correctness, not real-archive or CUDA fit. BM25/AGE
extension SQL is committed for review and is not applied on stock Postgres.

## Audit handoff

none identified

## Close or resume

Accepted. Remaining open work starts at `enforce-evolution-and-migration-policy`. Final count after
plan removal: 84 tasks (73 agent, 11 human).
