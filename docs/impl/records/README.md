# Task Records

Copy the [template](template.md) at task start to `NNNN-<group>-<task-id>.md` using the
[record naming rules](../../guide/planning-workflow.md#record-file-naming), then index it here.
Records preserve full scope and evidence after [plan](../plan.md) removal; [current state](../current.md)
links them. See [record rules](../../guide/planning-workflow.md#durable-task-records) for amendments
and legacy work. Record results remain understandable without private runtime artifacts; unavailable
evidence is explicit.

Next unused sequence: assign `max(NNNN) + 1` from this directory (currently `0038` after the rows
below).

| Record | Scope | Result |
| --- | --- | --- |
| [0001 Codebase and workflow audit](0001-govern-codebase-and-workflow-audit.md) | Read-only implementation review, future refactoring/checkpoints, handoff rules and README | Review/docs present; the baseline CI block is resolved; the other identified code repairs remain open |
| [0002 Compact agent instructions](0002-govern-compact-agent-instructions.md) | Reduce repeated rules and required context; retain gates and handoffs | Documentation review; verification in record |
| [0003 Quality baseline repair](0003-foundation-restore-quality-gate-baseline.md) | Repair runtime import formatting and split the Compose topology test at invariant boundaries | Accepted; `make ci` and `make quality` pass with all invariants retained |
| [0004 Record and checkpoint integrity](0004-foundation-enforce-task-record-and-checkpoint-integrity.md) | Preserve full task fields, resolve dependencies against open tasks and accepted records, and validate records, notes and checkpoints | Accepted; `make ci` and `make quality` pass and the gate reports each defect class |
| [0005 Safe runtime root boundaries](0005-runtime-refactor-safe-runtime-root-boundaries.md) | Unify protected-root containment before any reset deletion or readiness-report write | Accepted; regressions cover reset containment, report destinations, derived aliasing and symlink swaps |
| [0006 Runtime configuration parity](0006-runtime-refactor-runtime-configuration-parity.md) | Resolve one configuration through Make, direct CLI and readiness without precedence drift | Accepted; `make ci` and `make quality` pass with paired shell/Python fixtures for precedence, references, invalid input and cache placement |
| [0007 Profile-aware service planning](0007-runtime-refactor-profile-aware-service-planning.md) | Shared service selection, pure commands and selected layout/readiness checks | Accepted; profile matrix regressions, `make ci` and offline `make quality` pass |
| [0008 Readiness probe safety](0008-runtime-refactor-readiness-probe-safety.md) | Secret-free commands, installed extensions and bounded local HTTP | Accepted; 304 tests, CI and full quality pass |
| [0009 Contract identity and reference validation](0009-contract-gov-refactor-contract-identity-and-reference-validation.md) | Rooted contract references and schema-qualified snapshot field identity | Accepted; regressions cover escapes, duplicates, migration and `make ci` / `make quality` |
| [0010 Canonical contract registry](0010-contract-gov-establish-canonical-contract-registry.md) | ODCS 3.1 registry, mappings, canonical model, loaders and lint | Accepted; official schema and Data Contract CLI lint pass with `make ci` / `make quality` |
| [0011 Deterministic schema generation](0011-contract-gov-implement-deterministic-schema-generation.md) | ODCS-to-Avro/SQL/Parquet/JSON/graph generation with drift check | Accepted; committed `contracts/generated`, `make contracts-check`, Avro/SQL gates pass |
| [0012 Evolution and migration policy](0012-contract-gov-enforce-evolution-and-migration-policy.md) | Reviewed baselines, consequence classes, dbmate migrations, live SQL apply | Accepted; fixtures and `make contracts-evolution` / CI pass |
| [0013 Versioned ontology assets](0013-contract-gov-establish-versioned-ontology-assets.md) | Controlled vocabulary, RDF/SHACL, bindings, ontology evolution | Accepted; `make ontology-check` / CI pass |
| [0014 Domain investigation contracts](0014-contract-gov-define-domain-investigation-contracts-and-ontology.md) | Domain artifact ODCS, ontology predicates, fixtures | Accepted; contracts/ontology CI pass |
| [0015 Data engineering tooling review](0015-govern-review-data-engineering-tooling.md) | Schema/migration implementation review; SQLAlchemy/Alembic, dbt, Polars/Pandera design and prerequisite task routing | Accepted review; 432 tests and documentation gates pass; dbt foundation resolved by 0024 |
| [0016 Simple operator entrypoints](0016-govern-design-simple-operator-entrypoints.md) | Retryable setup and one default pipeline command, separate atomic-command runbook, shared handlers and remaining implementation owners | Accepted design; runtime targets remain planned |
| [0017 Contract schema and migration tooling](0017-contract-gov-refactor-contract-schema-and-migration-tooling.md) | Contract-derived SQLAlchemy metadata, review DDL, immutable Alembic revisions, live catalog comparison and refusal-first legacy adoption | Accepted; offline gates pass; live upgrade remains with the canonical schema task |
| [0018 Build pinned ParadeDB + AGE image](0018-store-build-pinned-paradedb-age-image.md) | Project-owned ParadeDB/pgvector/AGE image, coexistence probes, graph AGE gate, host-UID bind mounts | Accepted; clean-cache build and disposable probes pass; AGE enabled; `make ci` 530/1 |
| [0019 Contract data-quality checks](0019-contract-gov-implement-contract-data-quality-checks.md) | Contract-derived Pandera/Polars batch checks, generated dbt YAML, typed results that cannot pass when required checks are missing or unexecuted | Accepted; fixture gates, `make ci`, and `make quality` pass; whole-relation dbt execution is in 0024 |
| [0020 Retire duplicate dbmate SQL](0020-contract-gov-retire-duplicate-dbmate-sql.md) | Remove leftover `db/` and SQL-dump inventory so Alembic is the only authored schema history | Accepted; `db/` deleted; dump inventory and parallel-history tests removed |
| [0021 Canonical relational schema](0021-store-create-canonical-relational-schema.md) | Apply Alembic history on the pinned store with partitions, constraints, roles, staging, and adoption | Accepted |
| [0022 Retryable setup command](0022-runtime-implement-retryable-setup-command.md) | One setup/edit/retry coordinator over atomic env, image, model, service and schema commands | Accepted |
| [0023 Representative corpus approval](0023-corpus-approve-representative-corpus-and-gold.md) | Operator-designated legally usable representative slice as `PROOF_ARCHIVE_DIR` | Accepted |
| [0024 dbt transformation foundation](0024-store-implement-dbt-transformation-foundation.md) | Local dbt project, typed runner, isolated derived generations, synthetic fixture DAG | Accepted |
| [0025 Rebuildable search and graph projections](0025-store-implement-rebuildable-search-and-graph-projections.md) | ParadeDB/pgvector/AGE projection lifecycle, dbt inputs, pointer switch, fixture checks | Accepted |
| [0026 Behavior-first test policy](0026-foundation-adopt-behavior-first-test-policy.md) | Replace numeric coverage floor with integrity/correctness/business-logic tests; checkpoint deepening | Accepted |
| [0027 Foundation and store boundary review](0027-store-review-foundation-and-store-boundaries.md) | Integrated runtime, contracts, canonical store, dbt and projection checkpoint | Accepted; proceed with one routed nonblocking note |
| [0028 Foundation store acceptance repair](0028-store-refactor-foundation-store-acceptance-boundaries.md) | Verified prerequisite, catalog and publication refusal gaps from 0027 | Accepted; single initial revision and verified publication boundaries |
| [0029 Retire separate proof-archive root](0029-runtime-retire-separate-proof-archive-root.md) | Remove `PROOF_ARCHIVE_DIR`; proof runs use `ARCHIVE_DIR` and ordinary commands | Accepted |
| [0030 Pandera Polars concat pin](0030-contract-gov-upgrade-pandera-polars-concat-compat.md) | Pin Pandera 0.33.1 so staging null checks do not emit Polars concat deprecation | Accepted |
| [0031 Local inference adapters](0031-inference-implement-local-inference-adapters.md) | Provider-neutral Ollama/vLLM client for chat, structured output, embeddings, health, identity, timeout, and cancel | Accepted |
| [0032 Model resource scheduler](0032-inference-implement-model-resource-scheduler.md) | Host-wide GPU lease, footprint fit, Ollama unload, requested vLLM control, and resource telemetry | Accepted |
| [0033 Evaluation bundle validation](0033-eval-found-refactor-evaluation-bundle-validation.md) | Immutable local evidence-bundle layout, identity, concurrent no-replace publish, streamed verify | Accepted |
| [0034 Checkpoints and human proof handoffs](0034-foundation-strengthen-checkpoints-and-human-proof-handoffs.md) | Timely reviews, Git-only identity obfuscation, ontology/geotemporal semantics and human review packets | Accepted |
| [0035 Committed proof identity obfuscation](0035-eval-found-implement-committed-proof-identity-obfuscation.md) | Deterministic Git-bound identity export from verified proof bundles | Accepted |
| [0036 Evaluation fixtures and metrics](0036-eval-found-create-evaluation-fixtures-and-metrics.md) | Frozen fixtures, paired metrics, evaluate stage, and proof dispatcher | Accepted |
| [0037 Grafana first-boot health](0037-runtime-allow-grafana-first-boot-health.md) | Grafana healthcheck start period, SQLite WAL, and disabled plugin preinstall | Accepted |
