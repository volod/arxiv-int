# Task Records

Copy the [template](template.md) at task start to `NNNN-<group>-<task-id>.md` using the
[record naming rules](../../guide/planning-workflow.md#record-file-naming), then index it here.
Records preserve full scope and evidence after [plan](../plan.md) removal; [current state](../current.md)
links them. See [record rules](../../guide/planning-workflow.md#durable-task-records) for amendments
and legacy work. Record results remain understandable without private runtime artifacts; unavailable
evidence is explicit.

Next unused sequence: assign `max(NNNN) + 1` from this directory (currently `0014` after the rows
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
