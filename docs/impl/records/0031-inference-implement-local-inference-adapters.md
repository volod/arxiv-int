# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-local-inference-adapters` / `local-inference` /
  `review-production-readiness-and-recovery`
- State: accepted
- Source: [plan](../plan.md); initial count 76 tasks (66 agent, 10 human). Working tree also
  contains unrelated accepted 0030 files that this task did not absorb.
- Amendments: none.

```markdown
#### implement-local-inference-adapters

Create a provider-neutral local client for Ollama and vLLM covering chat, structured output,
embeddings, health, model identity, timeout, and cancellation.

- Serves: `local-inference` -- [Local inference](../design/spec.md#local-inference)
- Agent status: CLEAR
- Dependencies: Feature groups and domain interfaces described in
[Project foundation](current/project-foundation.md#feature-groups); runtime roots documented in
[Portable runtime](current/portable-runtime.md).
[Readiness probe safety](records/0008-runtime-refactor-readiness-probe-safety.md).
- User-visible outcome: The same extraction/retrieval code can use the Ollama system service or an
optional vLLM container through explicit configuration.
- Scope boundary: Local endpoints only; no hosted fallback, implicit model pull, or systemd
mutation.
- Data and artifact paths: `src/arxiv_int/inference/`, `configs/models/`, generated
structured-output schemas, and `tests/inference/`.
- Execution path: Implement local API adapters, capability discovery, schema response validation,
bounded repair, streaming/cancel, retries, model digest capture, and fake servers for
deterministic tests. Expose reusable model identity/health/cancellation operations for setup;
explicit asset acquisition and its `models-pull` wrapper belong to
[retryable setup](records/0022-runtime-implement-retryable-setup-command.md), never to
inference request execution.
- Acceptance gates: Provider conformance tests agree on typed results/statuses; unreachable and
incompatible models fail clearly; prompts and secrets are not logged; no remote hostname passes
local-only policy by default.
- Documentation target: `docs/impl/current/local-inference.md`
- Review checkpoint: `review-production-readiness-and-recovery`.
```

## Implementation

`LocalInferenceClient` is the provider-neutral local HTTP client for Ollama and vLLM. It implements
`InferenceProvider` and adds chat, embeddings, health, identity, cancel, retries, and Ollama
unload. Transport reuses loopback URL policy from readiness: no proxies, no redirects, no URL
credentials, `localhost` mapped to `127.0.0.1`. Request execution never calls pull.

Structured output validates JSON Schema locally, strips optional fences, and bounds repair to two
attempts. Generated envelopes are `cited-span` and `refusal` under `configs/models/schemas/`.
`configs/models/registry.json` lists known project models; live discovery still works for other
tags. CLI/Make: `arxiv-int inference health|models|identity|schemas`, `make ollama-check`,
`make models-list`, `make inference-schemas-check` (in `make ci`). Current state:
[local-inference.md](../current/local-inference.md). Host-wide GPU scheduling is
[0032](0032-inference-implement-model-resource-scheduler.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Provider conformance | `.venv/bin/python -m pytest tests/inference -q` | pass; Ollama and vLLM fakes agree on typed statuses; host smoke skipped unless `ARXIV_INT_RUN_INFERENCE_SMOKE=1` |
| Unreachable / incompatible models | `test_missing_and_embedding_mismatch_are_architecture_unsupported`, unreachable `127.0.0.1:1` | pass; missing/chat-as-embed are `architecture_unsupported`; down endpoint is not ready |
| Prompts and secrets not logged | `tests/inference/test_inference_logging.py`, `test_policy.py` | pass; `fixture-secret-prompt` absent from logs |
| Local-only policy | `test_remote_or_credential_urls_are_rejected` | pass; example.com, URL userinfo, query, and fragment refused |
| No implicit pull | `test_inference_never_pulls_models` | pass; `/api/pull` never requested |
| CUDA-host Ollama smoke | `ARXIV_INT_RUN_INFERENCE_SMOKE=1 pytest tests/inference/test_host_smoke.py`; `arxiv-int inference health`; `$DATA_DIR/inference/smoke-0031/generate.json` | pass on RTX 4060 Ti, Ollama 0.32.15, `llama3.2:3b`; health 23 models; chat `ok`; structured `cited-span` `ok`. Not a 27B fit or vLLM result |
| `make ci` | `make ci` | pass; 819 passed, 19 skipped; structured-output schema drift check passed |

## Audit handoff

none identified. Reviewed local-only URL policy reuse, no pull in request paths, prompt-free
logging, bounded repair, fake-server conformance for both backends, and CUDA-host smoke limits.
GPU lease/unload coordination is in
[0032](0032-inference-implement-model-resource-scheduler.md).

## Close or resume

Accepted after deterministic conformance, local-only and logging gates, CUDA-host Ollama smoke,
documentation, and `make ci` (819 passed, 19 skipped). Plan counts: 76 tasks before, 75 after
(agent lane 66 to 65; human 10 unchanged). Capability `local-inference` stays planned; host-wide
scheduling is [0032](0032-inference-implement-model-resource-scheduler.md). No commit or push
was made.
