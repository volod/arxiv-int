# Local Inference

A provider-neutral client talks to a local Ollama system service or an optional vLLM Compose
endpoint. Extraction and retrieval callers use the same typed chat, structured-output, embedding,
health, identity, timeout, and cancel operations. Model acquisition remains a setup operation.

See [record 0031](../records/0031-inference-implement-local-inference-adapters.md). Host-wide GPU
scheduling remains [planned](../plan.md#implement-model-resource-scheduler).

## Client and local-only policy

`arxiv_int.inference.LocalInferenceClient` implements `InferenceProvider` and adds chat, embeddings,
health, identity, and Ollama unload. `client_from_config()` builds it from resolved runtime
configuration (`INFERENCE_BACKEND`, `OLLAMA_BASE_URL` or `VLLM_PORT`, and model identities).

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

## Schemas and model registry

Committed JSON Schema envelopes live under `configs/models/schemas/`. Python constants in
`arxiv_int.inference.schema` are the source; `make inference-schemas` writes them and
`make inference-schemas-check` (part of `make ci`) fails on drift. The current envelopes are
`cited-span` (a value plus required source quotes) and `refusal`. Callers may pass any schema.

`configs/models/registry.json` lists known project model ids and capabilities. Live `/api/show` or
`/v1/models` discovery still works for unlisted tags.

## Commands

```text
make ollama-check
make models-list
arxiv-int inference health
arxiv-int inference models
arxiv-int inference identity [--model ID]
arxiv-int inference schemas generate|check
```

`make ollama-check` and `make models-list` target the configured backend, including vLLM when
`INFERENCE_BACKEND=vllm`. They do not start systemd units or Compose services.

## Tests and verification

Deterministic tests under `tests/inference/` drive in-process fake Ollama and vLLM servers.
Conformance covers health, identity, chat, generate, structured repair, refusal, missing models,
embedding mismatch, timeout, cancel, retries, unreachable endpoints, and pull-path refusal. Policy
tests reject remote and credential URLs. Logging tests assert prompt text is absent. Schema tests
cover validation, fence stripping, and drift.

A declared host smoke (`ARXIV_INT_RUN_INFERENCE_SMOKE=1`) uses the running local Ollama service.
On this CUDA host it proved health for 23 tags, `llama3.2:3b` identity/digest, chat status `ok`,
and structured `cited-span` status `ok`. That smoke is not a 27B memory-fit or vLLM result. vLLM
was not running. Evidence: `$DATA_DIR/inference/smoke-0031/`.
