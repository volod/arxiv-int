# Current Implementation

This index describes behavior available now. For product intent read the
[specification](../design/spec.md); for work that remains read the [forward plan](plan.md).

## Documentation shape

Small areas stay as one page. When an area grows, its page becomes a short orientation and index,
and focused topics move under `current/<area>/`. New pages must be linked from their area in the same
change. Write behavior, modules, commands, tests, and results at the narrowest level.

## Areas

| Area | Owns |
| --- | --- |
| [Developer tooling](current/developer-tooling.md) | Locked setup, Make workflows, CI, quality gates, artifact roots |
| [Project foundation](current/project-foundation.md) | Distribution, import package, CLI identity, and project metadata |
| [Contracts](current/contracts.md) | Product ODCS registry, generation, ontology assets, rooted loaders, fingerprints, lint, and dataset quality checks |
| [Portable runtime](current/portable-runtime.md) | Layered configuration, safe roots, retryable `make setup`, and runtime layout |
| [Canonical store](current/canonical-store.md) | Pinned ParadeDB + AGE image, HASH-partitioned canonical schemas, roles, staging load, live adoption, local dbt transforms, and rebuildable search/graph projections |
| [Local inference](current/local-inference.md) | Provider-neutral Ollama/vLLM client and host-wide GPU lease, footprint fit, and resource telemetry |
| [Evaluation](current/evaluation.md) | Operator-designated `ARCHIVE_DIR` slice; frozen fixture metrics and proof dispatcher exist; provided-archive proofs and scale pilots remain planned |
| [Evaluation foundation](current/evaluation-foundation.md) | Immutable run bundles, Git-bound identity export, frozen fixtures, paired metrics, evaluate stage, and proof dispatcher |
| [Governance](current/governance.md) | Agent adapters, capability registry, plan lanes, integrity checks, specification/codebase audits and durable task records |
