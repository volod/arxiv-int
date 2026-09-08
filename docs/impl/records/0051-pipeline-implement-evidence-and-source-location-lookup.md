# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-evidence-and-source-location-lookup` /
  `pipeline-control` / `review-corpus-and-control-integrity`
- State: accepted
- Source: [plan](../plan.md) task `implement-evidence-and-source-location-lookup`; operator
  selected this id on a CUDA host. Initial `make plan-status`: 68 tasks (58 agent, 10 human);
  next eligible agent remained `implement-streaming-inventory`. Open listed producers
  `implement-streaming-inventory` and `implement-normalization-dedupe-and-chunking` still
  generate live canonical rows; this task implements the specified sealed-manifest / fixture
  resolver so search and report users can resolve locations before those stages exist.
- Amendments: 2026-09-08 operator request that path-event (and catalog document/occurrence)
  fields use the ODCS/Alembic schema as the single source of truth. Hard-coded portable field
  lists parallel to a future SQL relation were refused. Original task text is retained below.
  Full revised scope follows the original block.

```markdown
#### implement-evidence-and-source-location-lookup

Resolve every content, fact and report citation to physical sources and exact member/page/cell anchors.

- Serves: `pipeline-control` -- [Source and evidence identity](../design/spec.md#source-and-evidence-identity)
- Agent status: CLEAR
- Dependencies: `implement-streaming-inventory`; [Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
`implement-normalization-dedupe-and-chunking`.
- User-visible outcome: Search and report users can find original and current source locations,
including duplicate files, container members and renamed sources before any organizer is installed.
- Scope boundary: Read-only resolution and explicit path-event import; no placement executor,
reclassification, arbitrary filesystem opening, or requirement for live model/graph services.
- Data and artifact paths: `src/arxiv_int/query/evidence/`, source/path-event contracts,
`corpus.document_path_event`, portable source manifests, CLI and network-free resolver fixtures.
- Execution path: Expose `archive locate DOCUMENT_ID` and a typed citation resolver using canonical
rows or sealed manifests; map content to all source occurrences and original/normalized anchors;
validate root containment and current hashes; import portable organizer ledgers idempotently.
- Acceptance gates: Fixtures cover duplicate silos, sheet/cell and nested-member anchors, path-only
renames, missing/changed files, ambiguous locations, escaping links and repeated ledger import;
resolution never rewrites original provenance, changes bytes or requires placement services.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

Operator amendment: portable rows must follow registered ODCS columns; `corpus.document_path_event`
is published in this task rather than deferred.

```markdown
#### implement-evidence-and-source-location-lookup

Resolve every content, fact and report citation to physical sources and exact member/page/cell anchors.

- Serves: `pipeline-control` -- [Source and evidence identity](../design/spec.md#source-and-evidence-identity)
- Agent status: CLEAR
- Dependencies: `implement-streaming-inventory`; [Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
`implement-normalization-dedupe-and-chunking`.
- User-visible outcome: Search and report users can find original and current source locations,
including duplicate files, container members and renamed sources before any organizer is installed.
- Scope boundary: Read-only resolution and explicit path-event import; no placement executor,
reclassification, arbitrary filesystem opening, or requirement for live model/graph services.
Portable ledger and catalog rows must be contract columns from registered ODCS; no parallel
hand-written field list. SQL publication of `corpus.document_path_event` is in this task.
- Data and artifact paths: `src/arxiv_int/query/evidence/`, `document-path-events` ODCS/mapping/
canonical entity, `corpus.document_path_event`, Alembic `0005`, portable source manifests, CLI
and network-free resolver fixtures.
- Execution path: Author the path-event contract as schema SSOT; generate physical artifacts and
evolution baseline; freeze Alembic `0005` with HASH partitions and staging; parse/serialize
locate and import rows from normalized ODCS columns; join occurrences to documents by
`content_hash`; expose `archive locate DOCUMENT_ID` and typed citation resolution; validate root
containment and current hashes; import portable organizer ledgers idempotently.
- Acceptance gates: Fixtures cover duplicate silos, sheet/cell and nested-member anchors, path-only
renames, missing/changed files, ambiguous locations, escaping links and repeated ledger import;
unknown keys and missing required contract fields are refused; resolution never rewrites original
provenance, changes bytes or requires placement services; `make db-check` and contract evolution
pass with head `0005`.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Implementation

`src/arxiv_int/query/evidence/` is a read-only citation resolver plus an explicit portable
path-event import. It does not place files, reclassify, open virtual members as independent
files, or require Postgres, models, or graph services.

| Module | Role |
| --- | --- |
| `model.py` | Frozen catalog, citation, location, and import types |
| `schema.py` | ODCS-backed `ContractRow` parse/serialize via `catalog.normalize` |
| `codec.py` / `catalog.py` | Sealed `arxiv-int.evidence-catalog.v1` and ledger JSON using contract columns |
| `overlay.py` | Apply initial/rename/copy/import events without rewriting occurrence rows |
| `validate.py` | Silo-root containment and SHA-256 of the physical file |
| `resolve.py` | Content, fact, and report lookup; occurrences join documents by `content_hash` |
| `ledger.py` | Idempotent `event_id` merge; conflicting payloads refused |
| `render.py` | Console lines plus canonical JSON with path/secret redaction |
| `cli.py` / `commands.py` | `archive locate` and `archive import-ledger` |

Registered contract `document-path-events` is the schema source of truth for portable ledger
rows and for `corpus.document_path_event`. `catalog.normalize` is the shared physical model used by
portable row codecs, SQLAlchemy metadata, generated quality artifacts, and Alembic `0005`. The
revision freezes HASH partitions, staging, and the contract foreign keys; `upgrade()` adds those
keys with `ALTER TABLE` so overlay SQL can compile without loading `0001` tables into the same
`MetaData`. Catalog document/occurrence objects use the `documents` and `source-occurrences`
contracts; extra fields such as `occurrence.document_id` are refused. Unknown keys and missing
required contract fields fail import. `query.evidence` package import stays parser-only so
`archive --help` does not load the `contracts` extra.

`arxiv-int archive locate TOKEN [--kind content|fact|report]` and
`make archive-locate DOCUMENT_ID=...` read `--catalog` / `--ledger` when given and skip
`ARCHIVE_DIR` / `PGDATA_DIR`. `--silo SILO_ID=ROOT` is the only filesystem access. Locations
are silo-relative POSIX paths. Nested members hash the container. Duplicate silos stay
distinct.

Current-state pages: [Pipeline control](../current/pipeline-control.md);
[Canonical store](../current/canonical-store.md); [Contracts](../current/contracts.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Duplicate silos, member/cell anchors, fact/report | `tests/query/evidence/test_resolve.py::test_duplicate_silos_and_nested_member_and_cell_anchors` | pass |
| Path-only rename, missing, changed, catalog bytes | `test_path_only_rename_missing_changed_and_read_only_catalog` | pass; occurrence provenance unchanged |
| Escaping symlink and ambiguous fact | `test_escaping_link_and_ambiguous_fact_locations` | pass; status `escaped`; `ambiguous=true` |
| Copy extra location | `test_copy_event_adds_additional_current_location` | pass |
| Unknown document | `test_unknown_document_has_no_locations` | pass; empty locations |
| Repeated and conflicting ledger import | `tests/query/evidence/test_ledger.py` | pass; second import skipped; conflict does not rewrite |
| CLI JSON without runtime config | `tests/query/evidence/test_cli.py` | pass; schema `arxiv-int.evidence-resolution.v1` |
| Make wrapper | `tests/pipeline/dag/test_make.py::test_make_archive_locate_is_read_only_and_does_not_require_a_run` | pass |
| Optional imports | `tests/query/evidence/test_optional_imports.py`; `tests/runtime/setup/test_optional_imports.py` | pass; no sqlalchemy/pandera/dbt/pyarrow; `archive --help` with `-S` |
| Path-event schema SSOT | `tests/query/evidence/test_schema.py`; `tests/stores/postgres/test_path_event_revision.py` | pass; unknown `recorded_at` refused; 0005 columns/FKs match contract |
| CUDA host snapshot | `nvidia-smi` | pass on host (NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84) |
| Host fixture locate | `arxiv-int archive locate doc-host --json` | not-run for this schema amendment; locate regressions above remain the proof |
| Format, lint, types, complexity, doc links, spec-plan | `make ci` | pass |
| Contracts, ontology, inference schemas, identity policy, fixtures | `make ci` (`contracts-check`, `contracts-evolution`, `db-check`, `ontology-check`, `inference-schemas-check`, `identity-policy-check`, `evaluation-fixtures-check`) | pass; 21 contracts; head `0005`; live SQL `not-run` |
| Deterministic tests | `make ci` / `make test` (`-m "not heavy"`) | pass; 1121 passed, 2 skipped, 50 deselected (heavy) |
| Plan counts | `make plan-status` | 67 tasks (57 agent, 10 human); next agent `implement-streaming-inventory` |

Fixtures do not prove real-archive extraction quality or CUDA worker fit. Live inventory and
normalize stages remain planned producers of canonical rows.

## Audit handoff

Reviewed sealed-manifest resolution, ODCS-backed portable rows vs frozen Alembic `0005`,
path-event overlay vs original provenance, hash/containment checks, idempotent import, CLI
optional imports, and CUDA-host GPU snapshot without model load.

`none identified`.

## Close or resume

Accepted, including the 2026-09-08 schema-SSOT amendment. Plan task remains removed; dependents
link this record. Counts stay 67 tasks (57 agent, 10 human). `pipeline-control` still has later
corpus proof and checkpoint work. Next agent work: `implement-streaming-inventory`. This amendment
does not start that task. No review-owned service remains running.
