# Inference and Evaluation Boundary Review

## Task and scope

- Id: `review-inference-and-evaluation-boundaries`; capability: `evaluation-foundation`.
- State: accepted.
- Source: `docs/impl/plan.md` at `cfdf5587154cfaced7997983f75eb385d288f970`; clean tree.
- Initial count: 78 tasks (68 agent, 10 human); selected task is eligible.
- Amendments: none.

```markdown
#### review-inference-and-evaluation-boundaries

Review inference, resource ownership and immutable evaluation inputs before pipeline integration.

- Serves: `evaluation-foundation` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: [Prior foundation checkpoint](records/0027-store-review-foundation-and-store-boundaries.md);
[Archive roots](records/0029-runtime-retire-separate-proof-archive-root.md);
[Pandera compatibility](records/0030-contract-gov-upgrade-pandera-polars-concat-compat.md);
[Inference adapters](records/0031-inference-implement-local-inference-adapters.md);
[Resource scheduler](records/0032-inference-implement-model-resource-scheduler.md);
[Bundle validation](records/0033-eval-found-refactor-evaluation-bundle-validation.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md);
[Committed proof identities](records/0035-eval-found-implement-committed-proof-identity-obfuscation.md).
- User-visible outcome:
Pipeline workers receive compatible typed inference, cancellation, resource and evidence contracts.
- Scope boundary:
Review accepted 0029-0033 with the new evaluation/export producers. Use deterministic local fixtures
and inspect retained CUDA evidence; a small-model smoke cannot establish another model's fit.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace local-only requests, leases across processes, cancel/exception release, declared CPU fallback,
footprint/model identity, no implicit pull/service control, and optional-import boundaries. Trace
metric denominators, split isolation, bundle immutability, missing evidence and Git-export identity
joins/format/anchors; ensure ontology and geotemporal fixture meanings survive export.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
Show contention/cancellation and model-mismatch refusals; empty/failed metrics cannot pass;
corrupt/stale bundles and leaking or inconsistent exports cannot publish. Existing accepted producer
checks remain evidence; missing cross-module cases receive targeted tests before DAG integration.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/evaluation-foundation.md`
- Review checkpoint: none; this is the bounded checkpoint.
```

## Implementation

Reviewed accepted 0029-0033 plus evaluation/export producers 0035 and 0036 against the named
invariants. Existing producer tests already cover local-only URLs, no implicit pull, in-process
lease contention, cancel-while-waiting, declared CPU fallback, 27B-versus-3B footprints, vLLM
service-control refusal, bundle symlink/fifo/no-replace publication, split leakage, missing
predictions, and Git-export join/format/anchor gates.

The review added missing cross-module regressions and three targeted seam repairs so those
invariants hold before pipeline DAG integration:

- GPU `current()` ignored a crashed holder's leftover `gpu.lease.json` while the flock was already
  free. Inspection now treats that row as absent; the next process can acquire.
- Proof publication used `mkdir(..., exist_ok=True)` and could replace Git-bound proof files.
  Destinations are exclusive; identity tokens, `identities.json`, private paths, and nonregular
  entries refuse check.
- Empty metric dicts already failed, but non-finite values could still be published. Failed NaN/inf
  metrics now raise `MissingEvidenceError`. Parser registration no longer imports the HTTP client.

No speculative rewrite, model promotion, or new framework. Current behavior:
[Evaluation foundation](../current/evaluation-foundation.md) and
[Local inference](../current/local-inference.md).

## Acceptance evidence

Review evidence is under `$DATA_DIR/architecture-review/0038/`. The producer matrix covers the
named milestone requirements. Fixture verdicts enable pipeline-interface implementation, not
corpus/CUDA promotion or archive placement.

| Producer / boundary | Reviewed requirements and current evidence | Disposition |
| --- | --- | --- |
| 0029 retired proof-archive root | `tests/config/test_paths.py::test_retired_proof_archive_variable_is_ignored`; evaluation paths ignore leftover `PROOF_ARCHIVE_DIR` | existing plus `test_retired_proof_archive_is_not_an_evaluation_root` |
| 0030 Pandera/Polars concat | producer pin and warning-free null-id path remain in CI | existing coverage sufficient |
| 0031 local-only, no pull, identity | conformance, policy, logging; generate records requested model id/digest and refuses unknown ids | existing plus `test_generate_records_requested_identity_and_refuses_unknown_models` |
| 0032 leases, cancel, CPU fallback, fit | in-process scheduler tests; cross-process flock; exception release; crash `_exit` releases flock and clears stale current | existing plus process/exception regressions; CUDA smoke inspected, not promoted |
| 0033 bundle immutability | layout/concurrency producer tests; evaluate same `run_id` cannot replace | existing plus `test_evaluate_same_run_cannot_replace_the_bundle` |
| 0035 Git-export joins/format/anchors | producer export tests; ontology/geotemporal fields survive rewrite | existing plus `test_exported_ontology_and_geotemporal_meanings_survive` |
| 0036 metrics, split, proof freshness | split leakage, polarity, missing prediction; empty/non-finite metrics refuse; empty resource does not publish; leaking proof trees fail check | existing plus boundary regressions |
| Optional imports | `arxiv-int --help`, `inference --help`, and `evaluation --help` under `python -S` | existing plus two parser cases |
| Provided archive | 0023/0029 designation; no new corpus proof | not claimed |
| CUDA host | retained `$DATA_DIR/inference/smoke-0031/` and `scheduler-0032/`; current nvidia-smi RTX 4060 Ti 16380 MiB, driver 595.84, about 14.6 GiB free; re-ran `ARXIV_INT_RUN_INFERENCE_SMOKE=1` host smokes, 2 passed | small-model `llama3.2:3b` smoke only; not 27B quality or vLLM start/stop |

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Cross-process lease and crash release | `.venv/bin/python -m pytest tests/inference/test_lease.py tests/inference/test_lease_processes.py -q` | pass |
| Evaluate/proof/export boundaries | `.venv/bin/python -m pytest tests/evaluation/test_boundary_review.py tests/evaluation/test_scoring.py -q` | pass; overwrite, empty resource, proof exists, leak/catalog, ontology/geo export |
| Optional parser imports | `tests/runtime/setup/test_optional_imports.py` | pass including `inference --help` and `evaluation --help` with `-S` |
| CUDA inspect and smoke | `nvidia-smi`; `ARXIV_INT_RUN_INFERENCE_SMOKE=1 pytest tests/inference/test_host_smoke.py tests/inference/test_host_scheduler_smoke.py` | pass; 2 tests; copies under `$DATA_DIR/architecture-review/0038/` |
| Required CI | `make ci` | pass; 906 passed, 20 skipped; format, lint, typing, complexity, doc-links, spec-plan, contracts, ontology, inference schemas, identity-policy, evaluation-fixtures-check |

## Audit handoff

Incoming `AUD-codebase-05` remains resolved by [0033](0033-eval-found-refactor-evaluation-bundle-validation.md);
this review added evaluate-run no-replace and exclusive proof publication on the same immutability
rule. Incoming `AUD-codebase-14` remains resolved by [0032](0032-inference-implement-model-resource-scheduler.md);
this review added cross-process flock and crash-release evidence.

none identified as new notes. PostgreSQL `ctl.resource_lease` apply stays with the run-ledger task.
Provided-archive proofs, 27B quality, and vLLM start/stop keep their later owners. Concurrent
protected-root swap remains with
[review-archive-organization-integrity](../plan.md#review-archive-organization-integrity).

Refactor verdict: **refactor needed**, targeted seam repairs accepted in this checkpoint. Final
checkpoint decision: **proceed** for pipeline stage/artifact interface integration. Fixture
verdicts do not waive CUDA, provided-archive, or human gates.

## Close or resume

All required gates pass. Current pages and the record index link this checkpoint; downstream plan
dependencies link the accepted record. Only the satisfied checkpoint block was removed. Plan
counts: 78 at review start (68 agent, 10 human), 77 after (67 agent, 10 human).
`evaluation-foundation` changes from planned to shipped for its documented fixture foundation.
No other capability is promoted. The next eligible task at close was
[stage and artifact interface contracts](0040-pipeline-refactor-stage-and-artifact-interface-contracts.md).
No review-owned service remains running.
Retained evidence includes CUDA snapshots and `make ci` output. No commit or push was made.
