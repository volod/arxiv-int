# Local Inference

A provider-neutral client talks to a local Ollama system service or an optional vLLM Compose
endpoint. A host-wide scheduler serializes GPU-heavy embedding, reranking, OCR, and generation on
one CUDA device, estimates declared footprints, and records why a model ran, offloaded, skipped, or
fell back.

See [record 0031](../records/0031-inference-implement-local-inference-adapters.md) and
[record 0032](../records/0032-inference-implement-model-resource-scheduler.md).

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
`$SERVICE_STATE_DIR/inference/`. CPU fallback does not take that lease, so it does not block a
later CUDA session. Cancellation or error always releases the lease. A model already resident on
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
`$SERVICE_STATE_DIR/inference/ctl.resource_lease.jsonl`. Applying that table in PostgreSQL remains
with the run-ledger task. Telemetry JSONL is `$RUNS_DIR/<run-id>/telemetry/resource-events.jsonl`
(load time, throughput, VRAM, power, util). Pipeline logging can consume the same sink later.

## Schemas and model registry

Committed JSON Schema envelopes live under `configs/models/schemas/`. Python constants in
`arxiv_int.inference.schema` are the source; `make inference-schemas` writes them and
`make inference-schemas-check` (part of `make ci`) fails on drift. The current envelopes are
`cited-span` (a value plus required source quotes) and `refusal`. Callers may pass any schema.

`configs/models/registry.json` lists known project model ids, capabilities, and resource
footprints. Live `/api/show` or `/v1/models` discovery still works for unlisted tags; unlisted
models get a conservative size-token footprint.

## Commands

```text
make ollama-check
make models-list
make inference-resources
make inference-fit MODEL=llama3.2:3b
make inference-schedule RUN_ID=local MODEL=llama3.2:3b
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
`RUNS_DIR` / `SERVICE_STATE_DIR`.

## Tests and verification

Deterministic tests under `tests/inference/` drive in-process fake Ollama and vLLM servers.
Conformance covers health, identity, chat, generate, structured repair, refusal, missing models,
embedding mismatch, timeout, cancel, retries, unreachable endpoints, and pull-path refusal. Policy
tests reject remote and credential URLs. Logging tests assert prompt text is absent. Schema tests
cover validation, fence stripping, and drift. Scheduler tests cover simulated contention,
cancellation, CPU fallback, RAM refusal, vLLM occupancy without unapproved stop, Ollama unload,
and telemetry without prompt text.

A declared host smoke (`ARXIV_INT_RUN_INFERENCE_SMOKE=1`) uses the running local Ollama service and
the NVIDIA driver. On this CUDA host it proved RTX 4060 Ti 16 GB, `llama3.2:3b` CUDA placement and
leased generate status `ok`, and `qwen3.8:27b` GPU-only rejection (18.4 GiB need vs 14.5 GiB free).
That smoke is not a vLLM start/stop or 27B quality result. Evidence:
`$DATA_DIR/inference/scheduler-0032/` and `$RUNS_DIR/scheduler-0032/telemetry/`.
