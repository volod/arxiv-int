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
| [Contracts](current/contracts.md) | Product ODCS registry, generation, ontology assets, rooted loaders, fingerprints, and lint |
| [Portable runtime](current/portable-runtime.md) | Layered configuration, safe roots, storage evidence, and runtime layout |
| [Canonical store](current/canonical-store.md) | Pinned ParadeDB + AGE image, extension coexistence gate, and operator build/probe entrypoints |
| [Governance](current/governance.md) | Agent adapters, capability registry, plan lanes, integrity checks, specification/codebase audits and durable task records |
