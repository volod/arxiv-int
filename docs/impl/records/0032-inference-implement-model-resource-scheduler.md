# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-model-resource-scheduler` / `local-inference` /
  `review-production-readiness-and-recovery`
- State: accepted
- Source: [plan](../plan.md); initial count 75 tasks (65 agent, 10 human). Prerequisite:
  [0031 local inference adapters](0031-inference-implement-local-inference-adapters.md).
  Audit input: [AUD-codebase-14](0001-govern-codebase-and-workflow-audit.md#audit-handoff).
- Amendments: none.

```markdown
#### implement-model-resource-scheduler

Schedule GPU-heavy embedding, reranking, OCR, and generation sequentially by default and record
resource evidence.

- Serves: `local-inference` --
[Performance and scalability assumptions](../design/spec.md#performance-and-scalability-assumptions)
- Agent status: RUN NEEDED
- Audit inputs: [AUD-codebase-14](records/0001-govern-codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Local inference adapters](records/0031-inference-implement-local-inference-adapters.md).
- User-visible outcome: The 16 GB GPU does not thrash between models, and operators see why a model
ran, offloaded, skipped, or fell back.
- Scope boundary: Single-host resource coordination; no cluster scheduler and no unapproved service
stop.
- Data and artifact paths: `src/arxiv_int/inference/scheduler.py`, `ctl.resource_lease`, model
profiles, and `$RUNS_DIR/<run-id>/telemetry/`.
- Execution path: Replace the current placement-only scheduler with tested host-wide coordination;
detect GPU/RAM,
estimate declared footprints, acquire one GPU lease, manage Ollama
keep-alive/unload through API when allowed, start/stop vLLM profile when requested, and record
load/throughput/VRAM/power through a narrow telemetry sink that later pipeline logging also
consumes.
- Acceptance gates: Simulated contention and real single-CUDA-device smoke account for weights,
KV cache, context, batch, runtime overhead
and CPU/database memory; no incompatible workloads overlap;
cancellation releases leases; model-fit rejection is actionable; CPU fallback is explicit.
- Documentation target: `docs/impl/current/local-inference.md`
- Review checkpoint: `review-production-readiness-and-recovery`.
```

## Implementation

`ModelResourceScheduler` is the host-wide coordinator. Placement still uses `ModelScheduler` /
`place_requirement` as a pure function. CUDA work acquires one exclusive GPU lease
(`threading.Lock` plus `fcntl.flock`) under `$SERVICE_STATE_DIR/inference/`. CPU fallback does not
take that lease. A model already resident is kept; only other Ollama models are unloaded via
`/api/generate` `keep_alive=0` and counted as reclaimable VRAM from `/api/ps`. vLLM Compose
start/stop runs only when the caller sets `allow_service_control`. A vLLM endpoint that is not
ready, or vLLM occupancy for an Ollama CUDA request, yields CPU fallback or an actionable
rejection instead of acquiring the GPU lease and then failing. Footprints live in
`configs/models/registry.json`; unlisted ids use a size-token envelope that does not treat `27b`
as `3b`. Lease rows use the `ctl.resource_lease` shape in
`$SERVICE_STATE_DIR/inference/ctl.resource_lease.jsonl`; applying the PostgreSQL table stays with
the run-ledger task. Telemetry is `$RUNS_DIR/<run-id>/telemetry/resource-events.jsonl` and
snapshots VRAM after load and after release. CLI/Make: `arxiv-int inference resources|fit|schedule`,
`make inference-resources`, `make inference-fit`, `make inference-schedule`. Current state:
[local-inference.md](../current/local-inference.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Simulated contention, cancel, fallback, vLLM policy | `.venv/bin/python -m pytest tests/inference -q` (host smokes skipped unless `ARXIV_INT_RUN_INFERENCE_SMOKE=1`) | pass; CUDA sessions do not overlap; CPU fallback does not hold the GPU lease; cancel releases; GPU-only 27B reject is actionable; vLLM without service control does not take CUDA |
| Weights / KV / context / batch / overhead / RAM | `tests/inference/test_footprint.py`, `test_scheduler.py` | pass; KV scales with context and batch; CPU offload reduces GPU weights; RAM shortfall rejects even when VRAM fits; already-resident target is not listed for unload |
| Real single-CUDA-device smoke | `ARXIV_INT_RUN_INFERENCE_SMOKE=1 pytest tests/inference/test_host_scheduler_smoke.py tests/inference/test_host_smoke.py`; `arxiv-int inference resources`; `arxiv-int inference fit --model llama3.2:3b`; `arxiv-int inference fit --model qwen3.8:27b --no-allow-cpu`; `$DATA_DIR/inference/scheduler-0032/` | pass on RTX 4060 Ti 16 GB, 125.6 GiB RAM, Ollama; `llama3.2:3b` CUDA need 2.9 GiB, leased generate `ok`; `qwen3.8:27b` GPU-only need 18.4 GiB vs about 14.5 GiB free, exit 2. Not a vLLM start/stop or 27B quality result. Fixtures do not prove archive quality |
| `make ci` | `make ci` | pass; 841 passed, 20 skipped; doc-links 0; spec-plan 0 |

## Audit handoff

Incoming `AUD-codebase-14` resolved: exclusive host GPU lease, simulated contention, cancellation
release, and one-device CUDA evidence. Reviewed no unapproved service stop, prompt-free telemetry,
already-resident keep vs reclaim, and file JSONL lease rows until Postgres `ctl.resource_lease`
apply. none identified as new notes.

## Close or resume

Accepted after deterministic scheduler gates, CUDA-host fit/lease/generate smoke, documentation,
and `make ci` (841 passed, 20 skipped). Plan counts: 75 tasks before, 74 after (agent lane 65 to
64; human 10 unchanged). Capability `local-inference` marked shipped. Next agent work:
`refactor-evaluation-bundle-validation`. No commit or push was made.
