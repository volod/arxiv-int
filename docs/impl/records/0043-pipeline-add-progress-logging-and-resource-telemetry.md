# Task Record

## Task and scope

- Id / capability / checkpoint: `add-progress-logging-and-resource-telemetry` /
  `pipeline-control` / `review-pipeline-publication-and-reuse-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `add-progress-logging-and-resource-telemetry`; working tree
  includes accepted [0042](0042-pipeline-implement-stage-dag-cli-and-make-targets.md) DAG CLI.
  Initial count: 74 tasks (64 agent, 10 human); `make plan-status` selected this task.
- Amendments: none.

```markdown
#### add-progress-logging-and-resource-telemetry

Provide serialized human logs, structured logs, periodic database progress, and bounded resource
metrics for every stage.

- Serves: `pipeline-control` --
[Logging, progress, and observability](../design/spec.md#logging-progress-and-observability)
- Agent status: CLEAR
- Audit inputs: [AUD-codebase-15](records/0001-govern-codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md).
- User-visible outcome: Long runs continuously report processed/remaining items, bytes, throughput,
ETA, errors, and resource pressure without garbled concurrent output.
- Scope boundary: Record operational metadata; do not place document content, prompts, secrets, or
unbounded ids in logs/metric labels.
- Data and artifact paths: `src/arxiv_int/observability/`, `$RUNS_DIR/<run-id>/logs/`,
`ctl.stage_run`, Grafana provisioning, and logging tests.
- Execution path: Extend the existing logging and timing interfaces with time/count-throttled
progress, explicit queue bounds/overload behavior, heartbeats, psutil/NVML/disk/Postgres metrics,
redaction filters, JSONL schema, and final
manifests.
- Acceptance gates: Concurrent-log tests produce intact lines; redaction fixtures remove secrets and
corpus text; stalled worker and ETA states are distinguishable; metric labels have bounded
cardinality.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.
```

## Implementation

`src/arxiv_int/observability/` owns queued logging, redaction, throttled progress, bounded metric
labels, host samples, JSONL/manifest sinks, and an optional SQLAlchemy writer for
`ctl.stage_progress`. Core modules do not import SQLAlchemy; `postgres.py` and `tables.py` do.
psutil is an optional import, not a base dependency. GPU samples reuse inference `nvidia-smi`.

`QueuedLogSession` uses a bounded `queue.Queue`: newest records drop on saturation, and
`BoundedQueueListener` drops oldest rows to insert the stop sentinel. `ProgressTracker`
distinguishes `stalled` (heartbeat timeout) from `slow` (fresh heartbeat, large ETA).
`StageSession` writes
`$RUNS_DIR/<run-id>/logs/` (`console.log`, `events.jsonl`, `progress.jsonl`, `latest.json`,
`observability-manifest.json`) and appends `pipeline.resource` telemetry. A background heartbeat
pump keeps long stages reporting without a worker callback. Frozen `LOG_FORMAT` and
`PROGRESS_INTERVAL_SEC` control format and throttle. The orchestrator wraps every stage; `run
status` prints the latest snapshot and `worker_state`.

Alembic `0003` creates `ctl.stage_progress` without embedding `ctl.stage_run` in the same
MetaData; the foreign key is added with `ALTER TABLE` so offline SQL can render. Head is `0003`;
ledger-only catalogs still stamp `0002`. Grafana `pipeline-progress.json` and
`resource-pressure.json` query that table through `arxiv-int-postgres`. Topic/entity/fact panels
remain planned.

[AUD-codebase-15](0001-govern-codebase-and-workflow-audit.md#audit-handoff) is resolved.

Current-state page: [Pipeline control](../current/pipeline-control.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Concurrent-log intact lines | `tests/observability/test_logging.py::test_queued_session_serializes_concurrent_records` | pass; 80 intact lines from four workers |
| Queue overload and shutdown | `test_bounded_queue_drops_newest_on_overload_and_shutdown_joins` | pass; drops newest; listener joins |
| Redaction fixtures | `tests/observability/test_redact.py` | pass; secrets, prompts, paths, and long quotes removed |
| Stalled vs ETA | `tests/observability/test_progress.py` | pass; `stalled` vs `slow` are distinct |
| Bounded metric labels | `tests/observability/test_obs_metric_labels.py` | pass; `run_id`/`document_id` refused; unknown names refused |
| Fixture DAG progress files | `tests/pipeline/orchestration/test_progress_logs.py` | pass; JSONL schema `arxiv-int.observability.v1` and manifest |
| Frozen revision `0003` | `tests/observability/test_obs_revision_alignment.py`; `make db-check` | pass; head `0003`; live evidence not-run in `make ci` |
| Disposable schema at head `0003` | `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1 pytest tests/integration/postgres/test_canonical_schema.py tests/integration/postgres/test_run_ledger.py tests/integration/postgres/test_catalog_boundaries.py` | pass; 16 tests on this CUDA host with image `arxiv-int/postgres:17-0.25.6-age1.7.0` |
| CUDA host sample | `nvidia-smi`; `tests/observability/test_obs_resource_sampler.py::test_live_nvidia_snapshot_when_a_device_is_present` | pass on host (NVIDIA GeForce RTX 4060 Ti, 16380 MiB, driver 595.84); `make ci` skipped the live probe in the sandbox |
| Formatting and required CI | `make format`; `DATA_DIR=/tmp/arxiv-int-obs-0043 make ci` | pass; 1000 passed, 1 skipped (live NVIDIA under sandbox), 48 heavy deselected |
| Documentation links and plan integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 73 tasks (63 agent, 10 human); next `implement-evidence-based-pipeline-forecast` |

Fixtures do not prove real-archive extraction quality. CUDA inventory was sampled for resource
telemetry and was not used as a DAG worker-fit gate.

## Audit handoff

Reviewed queue bounds/overload/shutdown, redaction, stalled-versus-slow taxonomy, metric
cardinality, 0003 overlay FK rendering, and CUDA-host resource sampling.

`AUD-codebase-15` resolved. `none identified` as a new note.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 74 to 73 tasks
(64 to 63 agent; 10 human unchanged). `pipeline-control` still has forecast and publication work.
Next agent work: `implement-evidence-based-pipeline-forecast`. No review-owned service remains
running.
