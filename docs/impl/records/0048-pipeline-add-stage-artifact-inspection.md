# Task Record

## Task and scope

- Id / capability / checkpoint: `add-stage-artifact-inspection` / `pipeline-control` /
  `review-corpus-and-control-integrity`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `add-stage-artifact-inspection`; working tree includes accepted
  [0042](0042-pipeline-implement-stage-dag-cli-and-make-targets.md) DAG CLI and
  [0047](0047-pipeline-repair-pipeline-publication-and-reuse-integrity.md) publication/reuse
  repair. Initial count: 70 tasks (60 agent, 10 human); `make plan-status` selected this task.
- Amendments: none.

```markdown
#### add-stage-artifact-inspection

Report what a normal pipeline stage produced without recomputing it.

- Serves: `pipeline-control` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: RUN NEEDED
- Dependencies: [Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md).
- User-visible outcome: After any stage or complete pipeline run, the operator can inspect row and
byte counts, partitions, contract conformance, bounded source anchors, quarantines, and failures by
run id.
- Scope boundary: Read and summarize normal run artifacts; do not introduce development-only paths
or commands, rerun stages, mutate artifacts, or treat an inspection as proof acceptance.
- Data and artifact paths: `src/arxiv_int/inspect/`, `$RESULTS_DIR/normalized/`,
`$RUNS_DIR/<run-id>/`, `src/arxiv_int/cli.py`, `Makefile`, and inspection fixtures.
- Execution path: Add `arxiv-int inspect RUN_ID` and the matching run-artifact lookup using the
pipeline registry and contracts; render console and JSON summaries with bounded samples and masked
secrets; inspect the real run produced after each available stage implementation.
Read retained Pandera/dbt quality results and sanitized model lineage; show rule scope, failed
counts, quarantine references and not-run status without executing transformations.
- Acceptance gates: Normal empty, partial, quarantined, and schema-drifted run artifacts produce
stable summaries; inspection leaves checksums unchanged; summaries contain no secrets, unbounded
corpus text, development alias, or machine-specific path.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Implementation

`src/arxiv_int/inspect/` is a read-only summarizer. It does not take the pipeline lock, rewrite
attempt trees, execute Pandera or dbt, or treat a summary as proof acceptance.

| Module | Role |
| --- | --- |
| `model.py` | Frozen `arxiv-int.inspect.v1` types; refuses developer alias `local` |
| `lookup.py` | Resolve `RUN_ID` / `DATASET` / `latest`; `$RUNS_DIR`-relative POSIX paths |
| `artifacts.py` | Attempt files, partitions, anchors, in-place checksum validation |
| `quality.py` | Retained `quality.json`, published `quality/result.json`, sanitized lineage |
| `lake.py` | Bounded `$RESULTS_DIR/normalized/` listing; parquet footer rows via importlib |
| `summarize.py` | `inspect_run` / `inspect_target` |
| `render.py` | Console lines plus canonical JSON; recursive redaction |
| `cli.py` / `commands.py` | Parser and handler; `--json` writes to stdout |

`arxiv-int inspect RUN_ID|DATASET|latest` and `make inspect RUN_ID=...` require a created run id.
`arxiv-int run artifacts RUN_ID` is the same handler. Package import stays dependency-light so
base CLI help works before optional extras. Explicit `--runs-dir` skips `ARCHIVE_DIR` /
`PGDATA_DIR`. Contract conformance is `matching`, `drifted`, or `unregistered`. Directories
outside `$RUNS_DIR` render as `<path>`. Cache-hit runs report the reused attempt directory.

Current-state page: [Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Fixture counts, read-only checksums | `tests/inspect/test_summarize.py::test_inspect_fixture_run_reports_counts_and_is_read_only` | pass |
| Empty, partial, quarantined, failed | `test_empty_partial_quarantined_and_failed_summaries` | pass; empty `gamma` is `empty`; partial halts; warning rules list as quarantines |
| Schema drift and not-run quality | `test_schema_drift_and_not_run_quality_without_transforms` | pass; `documents` @ `0.9.0` is `drifted`; `run_transform` is not called |
| Malformed quality does not rewrite | `test_malformed_quality_is_stable_and_does_not_rewrite` | pass; checksums unchanged |
| Secrets, paths, alias, corpus | `test_redacts_secrets_paths_and_refuses_developer_alias` | pass; `local` refused; details redacted before render |
| Latest and lake lookup | `test_latest_and_lake_dataset_lookup` | pass; `--limit` bounds lake rows |
| Bounded anchors | `test_bounded_source_anchors` | pass; first two of three |
| CLI and `run artifacts --json` | `tests/inspect/test_cli.py` | pass; JSON on stdout; `local` exit 1 |
| GitHub CI without operator roots | `test_inspect_cli_and_run_artifacts_alias` with runtime config refused | pass; explicit `--runs-dir` does not load `ARCHIVE_DIR` / `PGDATA_DIR` |
| Evaluate stage artifacts | `test_inspect_evaluate_stage_artifacts` | pass; `outcome=produced`; tree valid |
| Make wrapper | `tests/pipeline/orchestration/test_make.py::test_make_inspect_is_read_only_and_requires_created_run_id` | pass |
| Optional imports | `tests/inspect/test_optional_imports.py`; `tests/runtime/setup/test_optional_imports.py` | pass; no pandera/dbt/sqlalchemy/pyarrow at module import; base CLI `-S` help stays light |
| CUDA host snapshot | `nvidia-smi`; host JSON under `$DATA_DIR/pipeline-inspect/0048/` | pass on host (NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84, CUDA 13.2) |
| Host fixture inspect | `arxiv-int inspect RUN_ID --json` after fixture DAG `alpha/beta/gamma` | pass; schema `arxiv-int.inspect.v1`; checksums unchanged; 4851-byte JSON; no operator home path; cache-hit directories stay `$RUNS_DIR`-relative |
| Host evaluate inspect | inspect after registered `EvaluateStage` | pass; `run-b67d786ecabc405c98aa7125a3a1db97`; `outcome=produced` |
| Formatting and required CI | `make format`; `DATA_DIR=/tmp/arxiv-int-inspect-0048 make ci` | pass; 1082 passed, 50 heavy deselected |
| Documentation links and plan integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 69 tasks (59 agent, 10 human); next `implement-streaming-inventory` |

Fixtures do not prove real-archive extraction quality or CUDA worker fit. Production corpus
stages remain unregistered; only the fixture DAG and `evaluate` were available to inspect.
Inspection is not proof acceptance.

## Audit handoff

Reviewed read-only lookup, checksum freeze, quality/lineage without live transforms, developer
alias refusal, stdout JSON, base-CLI optional imports, and CUDA-host GPU snapshot without
model load.

`none identified`.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 70 to 69 tasks
(60 to 59 agent; 10 human unchanged). `pipeline-control` still has later corpus and
reconciliation work. Next agent work: `implement-streaming-inventory`. No review-owned
service remains running.
