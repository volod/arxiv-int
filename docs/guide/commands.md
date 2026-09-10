# Command Reference

`make help` lists every Make target with its one-line purpose, grouped by area. This page explains
the CLI surface behind those targets, what each group is for, and which parts are available today.

Make targets are the supported entry points; they load `.env`, resolve roots, and call the same
handlers as the CLI. Use `.venv/bin/arxiv-int` directly when a target does not expose an option, or
when the executable is not on the shell's path. Every command prints `--help`.

The [operator workflow](operator-workflow.md) gives the ordered chain for a real run.
The [development guide](development.md) covers quality gates and contributor workflows.

## Availability

| Marker | Meaning |
| --- | --- |
| available | Implemented and covered by tests in this repository. |
| planned | Specified in [the specification](../design/spec.md); the command is not registered yet. |

Availability below tracks [current implementation](../impl/current.md). A planned command is absent
from `--help` rather than silently doing nothing.

## Environment, configuration and services

| Command | Availability | Purpose |
| --- | --- | --- |
| `arxiv-int info` | available | Packaging and executable-path smoke test. |
| `arxiv-int features [--stage STAGE]` | available | Optional dependency groups, install status, install commands, distribution licences and expected system dependencies. |
| `arxiv-int config show --redact` | available | Resolve and validate runtime configuration without printing secrets. |
| `arxiv-int readiness [--profiles P] [--timeout S]` | available | Audit configuration, storage, tools, services, models and system readiness. |
| `arxiv-int setup [--phase PHASE]` | available | Retryable environment, model, service and schema preparation; reuses verified work. |
| `arxiv-int services --help` | available | Start, stop, inspect and reset the validated local service project. |

## Contracts, schema and transformations

| Command | Availability | Purpose |
| --- | --- | --- |
| `arxiv-int contracts --help` | available | Lint product ODCS contracts and regenerate committed physical schemas. |
| `arxiv-int db --help` | available | Author, check and apply owned canonical schema revisions. Empty databases apply one initial revision; see [canonical store](../impl/current/canonical-store.md). |
| `arxiv-int ontology --help` | available | Parse RDF/SHACL assets, verify generated bindings and check ontology evolution. |
| `arxiv-int store projections-build\|status\|cleanup --run-id RUN_ID` | available | Build, switch and clean ParadeDB/pgvector/AGE projections without making them canonical. A failed build cannot replace an active pointer. |
| `arxiv-int data-quality check DATASET --run-id RUN_ID --input PATH` | available | Validate one contract dataset and write secret-free evidence. A missing or unexecuted required check cannot look publishable. |
| `arxiv-int transform parse\|compile\|build\|test --run-id RUN_ID` | available | Parse, compile, build or test isolated derived dbt models. A failed or unexecuted required live check cannot look like a pass. |

## Runs and pipeline stages

| Command | Availability | Purpose |
| --- | --- | --- |
| `arxiv-int run create` | available | Allocate a `run-<hex>` id and freeze secret-free configuration. Never accepts Make's developer `RUN_ID=local` fallback. |
| `arxiv-int run status\|resume\|finalize\|artifacts RUN_ID` | available | Inspect progress, resume an interrupted generation, seal `knowledge-base.json`, or summarize published artifacts. |
| `arxiv-int pipeline forecast --run-id RUN_ID` | available | Read-only time and storage forecast with device free-space refusal; exit 3 when the requested scope is blocked. |
| `arxiv-int pipeline run` | available | Walk the selected profile DAG. It refuses explicitly while required later stages are unregistered. |
| `arxiv-int pipeline update\|rebuild\|invalidate` | available | Reconcile a changed archive into a new generation, rebuild in isolation, or mark reuse keys stale. |
| `arxiv-int stage STAGE --run-id RUN_ID` | available | Run one registered stage. `preflight`, `inventory`, `extract`, `normalize`, `dedupe`, `chunk`, and `load-lexical` are shipped runners; other stages fail as unregistered. |
| `arxiv-int inspect DATASET\|RUN\|latest [--limit N] [--json]` | available | Summarize published artifacts, quality, lineage, anchors, quarantines and failures without recomputing them. |
| `arxiv-int artifacts prune --stale` | available | Plan derived-artifact maintenance. `--apply --plan PLAN_ID` is a separate confirmation and refuses to delete a sole recovery copy. |
| `arxiv-int inference --help` | available | Call the configured local Ollama or vLLM endpoint. |

The ordered chain, the stage dependency closure and the remaining planned stages are in the
[operator workflow](operator-workflow.md#pipeline-atomic-chain).

## Source lookup and archive organization

| Command | Availability | Purpose |
| --- | --- | --- |
| `arxiv-int archive locate DOCUMENT_ID` | available | Resolve a content, fact or report citation to original and current source locations from sealed manifests. |
| `arxiv-int archive import-ledger PATH` | available | Import a portable organizer path-event ledger idempotently. |
| `arxiv-int archive reorganize ...` | planned | Physical placement from an accepted classification map; see [archive organization](archive-organization.md). |

## Analyst commands

These arrive as their specified capabilities are implemented; see the
[forward plan](../impl/plan.md).

| Command | Availability | Purpose |
| --- | --- | --- |
| `arxiv-int search lexical QUERY [--mode identifier] [--language L] [--document-id D] [--facet F] [--citations] [--explain] [--json]` | available | Query the active ParadeDB projection: Russian-aware BM25 ranking or literal identifier lookup, with filters, snippets, facets, resolved source spans and plan diagnostics. Exit 2 when no projection is active; see [lexical retrieval](../impl/current/lexical-retrieval.md). |
| `arxiv-int search semantic\|hybrid QUERY` | planned | Vector and fused retrieval over the same evidence. |
| `arxiv-int catalog company\|product\|person [--run RUN_ID]` | planned | Inspect roles, aliases, identities and evidence in the three catalogs. |
| `arxiv-int anomalies list\|show [--run RUN_ID]` | planned | Review detector, baseline, severity and supporting or contradicting evidence. |
| `arxiv-int graph rebuild\|check\|query` | planned | Rebuild and query the derived graph projection. |
| `arxiv-int report build RUN_ID` | planned | Render the specified analyst report. Today `run finalize` writes only a diagnostic `reports/index.html`. |
