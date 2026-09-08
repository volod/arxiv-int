# Local Inference

A provider-neutral client talks to a local Ollama system service or an optional vLLM Compose
endpoint. A host-wide scheduler serializes GPU-heavy embedding, reranking, OCR, and generation on
one CUDA device, estimates declared footprints, and records why a model ran, offloaded, skipped, or
fell back.

See [record 0031](../records/0031-inference-implement-local-inference-adapters.md),
[record 0032](../records/0032-inference-implement-model-resource-scheduler.md), and
[record 0038](../records/0038-eval-found-review-inference-and-evaluation-boundaries.md).

## Client and local-only policy

`arxiv_int.inference.LocalInferenceClient` implements `InferenceProvider` and adds chat, embeddings,
health, identity, loaded-model listing, and Ollama unload. `client_from_config()` builds it from
resolved runtime configuration (`INFERENCE_BACKEND`, `OLLAMA_BASE_URL` or `VLLM_PORT`, and model
identities).

Endpoints must be HTTP/HTTPS loopback (`127.0.0.1`, `localhost`, or `::1`). `localhost` is mapped to
literal IPv4 so host resolution cannot send a request elsewhere. URL credentials, query strings,
fragments, and remote hostnames are refused before connect. Proxies and redirects are disabled.
Inference request paths never call model pull.

## Operations

Chat and generate stream internally so timeout and cancel stay responsive. Temperature defaults to
zero. Structured output validates JSON against the caller schema, strips optional Markdown fences,
and retries at most twice with a repair instruction that does not repeat the original prompt.
Statuses are `ok`, `refused`, `malformed`, `timeout`, `cancelled`, `backend_error`, and
`architecture_unsupported`. Missing or embedding-only models fail as unsupported architecture, not
as a silent fallback. Embeddings require a discovered embedding capability. Outcome logs record
operation, backend, model id, status, latency, and token counts; prompt text and secrets are not
logged.

Health and identity are reusable by setup. `make models-pull` still owns asset acquisition.

## Host-wide GPU scheduler

`ModelResourceScheduler` replaces placement-only residency as the production coordinator.
GPU-heavy work takes one exclusive host lease (in-process lock plus `fcntl` flock) under
`$SERVICE_STATE_DIR/inference/`. The flock is exclusive across processes. A crashed holder
releases the kernel lock; leftover `gpu.lease.json` is not treated as held when the flock is
free. CPU fallback does not take that lease, so it does not block a later CUDA session.
Cancellation or error always releases the lease. A model already resident on
the GPU is kept; only other Ollama models are unloaded and counted as reclaimable VRAM.

Fit accounting uses declared registry footprints: weights, KV cache from context and batch, runtime
overhead, optional CPU offload, host RAM, and a database RAM reserve. Observed free VRAM comes from
`nvidia-smi`; reclaimable Ollama VRAM from `/api/ps` is added when unload is allowed. A 27B
GPU-only load on 16 GB is rejected with an actionable message. CPU fallback is explicit in the
placement detail. vLLM occupancy blocks Ollama CUDA placement unless the caller requested Compose
service control. A vLLM backend whose endpoint is not ready also falls back or rejects unless the
caller requested start. The scheduler never stops systemd Ollama and never starts or stops vLLM
unless `--allow-service-control` (or `allow_service_control=True`) is set. CUDA acquire/release
telemetry snapshots VRAM after load and after unload.

Lease rows use the `ctl.resource_lease` shape and are appended to
`$SERVICE_STATE_DIR/inference/ctl.resource_lease.jsonl`. Alembic `0001` creates that table; inference
does not yet dual-write SQL rows (`insert_resource_lease` is the bound helper when a caller does).
Telemetry JSONL is `$RUNS_DIR/<run-id>/telemetry/resource-events.jsonl`
(load time, throughput, VRAM, power, util). Pipeline stages append `pipeline.resource` events to
the same sink.

## Schemas and model registry

Committed JSON Schema envelopes live under `src/arxiv_int/resources/configs/models/schemas/`.
Python constants in `arxiv_int.inference.policy.schema` are the source; `make inference-schemas`
writes them and
`make inference-schemas-check` (part of `make ci`) fails on drift. The current envelopes are
`cited-span` (a value plus required source quotes) and `refusal`. Callers may pass any schema.

`src/arxiv_int/resources/configs/models/registry.json` lists known project model ids, capabilities, and resource
footprints. Ollama generation defaults to `qwen3.8:27b`; the CUDA-fitting Gemma family tag is
`gemma3:4b`. vLLM stays on pinned `Qwen/Qwen3.8-27B-FP8`. Live `/api/show` or `/v1/models`
discovery still works for unlisted tags; unlisted models get a conservative size-token footprint
(`<=4b` small, `>=24b` large).

## Commands

```text
make ollama-check
make models-list
make inference-resources
make inference-fit MODEL=gemma3:4b
make inference-schedule RUN_ID=local MODEL=gemma3:4b
arxiv-int inference health
arxiv-int inference models
arxiv-int inference identity [--model ID]
arxiv-int inference resources
arxiv-int inference fit [--model ID] [--context N] [--batch N] [--no-allow-cpu]
arxiv-int inference schedule [--model ID] [--run-id ID] [--wait-seconds N] [--allow-service-control]
arxiv-int inference schemas generate|check
```

`make ollama-check` and `make models-list` target the configured backend, including vLLM when
`INFERENCE_BACKEND=vllm`. They do not start systemd units or Compose services.
`inference-resources` does not require operator roots. Fit and schedule use configured
`RUNS_DIR` / `SERVICE_STATE_DIR`. `arxiv-int inference --help` does not import the HTTP client.

## Tests and verification

Deterministic tests under `tests/inference/` drive in-process fake Ollama and vLLM servers.
Conformance covers health, identity, chat, generate, structured repair, refusal, missing models,
embedding mismatch, timeout, cancel, retries, unreachable endpoints, and pull-path refusal. Policy
tests reject remote and credential URLs. Logging tests assert prompt text is absent. Schema tests
cover validation, fence stripping, and drift. Scheduler tests cover simulated contention,
cancellation, CPU fallback, RAM refusal, vLLM occupancy without unapproved stop, Ollama unload,
telemetry without prompt text, cross-process flock serialization, crash-release of a held flock,
and exception release without a cancel event. Generate results record the requested model identity
and refuse unknown model ids. Scheduler fixtures use `gemma3:4b` and `qwen3.8:27b`.

Host CUDA checks are operator commands (`make inference-fit`, `make inference-schedule`), not
pytest. Use `gemma3:4b` on a 16 GB GPU and `qwen3.8:27b` for the default generation / GPU-only
reject path. Historical llama3.2:3b pytest smokes were removed in
[record 0039](../records/0039-foundation-exclude-heavy-docker-and-llama-smokes.md). Prior CUDA
evidence remains in
[record 0031](../records/0031-inference-implement-local-inference-adapters.md),
[record 0032](../records/0032-inference-implement-model-resource-scheduler.md), and
[record 0038](../records/0038-eval-found-review-inference-and-evaluation-boundaries.md).
Those runs are not a vLLM start/stop or 27B quality result.
