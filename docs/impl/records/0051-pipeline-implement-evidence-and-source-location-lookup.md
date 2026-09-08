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
- Amendments: none.

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

## Implementation

`src/arxiv_int/query/evidence/` is a read-only citation resolver plus an explicit portable
path-event import. It does not place files, reclassify, open virtual members as independent
files, or require Postgres, models, or graph services.

| Module | Role |
| --- | --- |
| `model.py` | Frozen catalog, citation, path-event, location, and import types |
| `codec.py` / `catalog.py` | Sealed `arxiv-int.evidence-catalog.v1` and ledger JSON |
| `overlay.py` | Apply initial/rename/copy/import events without rewriting occurrence rows |
| `validate.py` | Silo-root containment and SHA-256 of the physical file |
| `resolve.py` | Content, fact, and report lookup |
| `ledger.py` | Idempotent `event_id` merge; conflicting payloads refused |
| `render.py` | Console lines plus canonical JSON with path/secret redaction |
| `cli.py` / `commands.py` | `archive locate` and `archive import-ledger` |

`arxiv-int archive locate TOKEN [--kind content|fact|report]` and
`make archive-locate DOCUMENT_ID=...` read `--catalog` / `--ledger` when given and skip
`ARCHIVE_DIR` / `PGDATA_DIR`. `--silo SILO_ID=ROOT` is the only filesystem access. Locations
are silo-relative POSIX paths. Nested members hash the container. Duplicate silos stay
distinct. Path-event field names match the intended `corpus.document_path_event` relation;
SQL/Alembic publication remains with archive organization.

Current-state page: [Pipeline control](../current/pipeline-control.md).

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
| CUDA host snapshot | `nvidia-smi` | pass on host (NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84) |
| Host fixture locate | `arxiv-int archive locate doc-host --json` | pass; status `matching`; JSON under `$DATA_DIR/pipeline-locate/0051/`; no `/home/` in resolution |
| Format, lint, types, complexity, doc links, spec-plan | `make ci` | pass |
| Contracts, ontology, inference schemas, identity policy, fixtures | `make ci` (`contracts-check`, `contracts-evolution`, `db-check`, `ontology-check`, `inference-schemas-check`, `identity-policy-check`, `evaluation-fixtures-check`) | pass; live SQL `not-run` |
| Deterministic tests | `make ci` / `make test` (`-m "not heavy"`) | pass; 1114 passed, 2 skipped, 50 deselected (heavy) |
| Plan counts | `make plan-status` | 67 tasks (57 agent, 10 human); next agent `implement-streaming-inventory` |

Fixtures do not prove real-archive extraction quality or CUDA worker fit. Live inventory and
normalize stages remain planned producers of canonical rows.

## Audit handoff

Reviewed sealed-manifest resolution, path-event overlay vs original provenance, hash/containment
checks, idempotent import, CLI optional imports, and CUDA-host GPU snapshot without model load.

`none identified`.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 68 to 67 tasks
(58 to 57 agent; 10 human unchanged). `pipeline-control` still has later corpus proof and
checkpoint work. Next agent work: `implement-streaming-inventory`. No review-owned service
remains running.
