# Task Record

## Task and scope

- Id / capability / checkpoint: `create-evaluation-fixtures-and-metrics` /
  `evaluation-foundation` / `review-inference-and-evaluation-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `create-evaluation-fixtures-and-metrics`; dirty evaluation
  export work from accepted 0035 is present and reused, not broadened. Initial count: 79 tasks
  (69 agent, 10 human).
- Amendments: none.

```markdown
#### create-evaluation-fixtures-and-metrics

Build immutable extraction, classification, Russian retrieval, semantic, entity, fact, ontology,
graph, domain-artifact, company/product/person catalog, anomaly and reporting fixtures plus
paired evaluation utilities.

- Serves: `evaluation-foundation` -- [Evaluation and acceptance](../design/spec.md#evaluation-and-acceptance)
- Agent status: CLEAR
- Dependencies: [Contract data-quality checks](records/0019-contract-gov-implement-contract-data-quality-checks.md);
[Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
the evaluation and retrieval primitives
documented in [Project foundation](current/project-foundation.md#evaluation-and-retrieval-primitives).
[Evaluation bundle validation](records/0033-eval-found-refactor-evaluation-bundle-validation.md);
[Committed proof identities](records/0035-eval-found-implement-committed-proof-identity-obfuscation.md).
- User-visible outcome: Every store/model/pipeline recommendation names the exact frozen items,
metrics, thresholds, and run artifacts that support it, and every usable stage can publish the same
proof-bundle shape.
- Scope boundary: Provide deterministic fixtures and measurement; human gold review remains in the
human lane.
- Data and artifact paths: `tests/fixtures/`, `eval.*`, `src/arxiv_int/evaluation/`,
`configs/evaluation/`, `configs/proofs/`, `Makefile`, `$RUNS_DIR/<run-id>/evaluation/`, and
`$RESULTS_DIR/proofs/`.
- Execution path: Extend the existing metrics for recall@k, MRR, evidence intactness, p95, paired
bootstrap, extraction/span, hierarchical classification, linkage, financial/BOM arithmetic,
catalog parity, anomaly cohorts/false positives/review-budget
precision, domain artifact, graph parity,
resource cost, and adopt/retain/inconclusive verdicts; register the
`evaluate` stage body that writes the immutable evaluation bundle; add a typed proof manifest,
stage-to-validator registry, redaction, fingerprint freshness, proof summary helpers, and a shared
`make proof CAPABILITY=...` dispatcher.
Reuse shared data-quality result identities and fixtures for missing/global checks; keep
held-out accuracy metrics separate from Pandera/dbt structural validation.
Use the shared Git-bound exporter for committed source-derived fixtures; keep local gold originals
and human-review packets unchanged. Include dynamic ontology add/deprecate/draft cases, source-valid
versus recorded time, uncertain places/CRS, role intervals and revision/effectivity boundaries. Build
same-name nonmatches and domain non-implication cases; obfuscate labels and expected answers together.
- Acceptance gates: Split leakage and provenance checks pass; bootstrap seeds and item ledgers
replay; missing evidence refuses a verdict; metrics have positive/negative fixtures; proof bundles
reject stale fingerprints, missing artifact checksums, unvalidated usable stages, and private paths
or unobfuscated corpus content in repository summaries; proof target discovery and unknown capability
tests pass.
Committed copies pass the exporter gate with policy/export fingerprints; raw local quality and
transformed fixture metrics stay distinct. Temporal, location and domain negatives cannot become
valid merely through identity replacement.
- Documentation target: `docs/impl/current/evaluation-foundation.md`
- Review checkpoint: `review-inference-and-evaluation-boundaries`.
```

## Implementation

Frozen families live under `tests/fixtures/evaluation/` with replayable `index.json` ledger (seed
13). Builders in `families_*.py` cover extraction, classification, Russian retrieval, semantic,
entity, fact, ontology, graph, domain-artifact, catalog, anomaly, reporting, geotemporal, and
domain-negative items. Split leakage refuses shared item ids, gold refs, or gold content.
`EvaluateStage` scores frozen polarities and publishes `$RUNS_DIR/<run-id>/evaluation/` through
`publish_run_bundle()`. Missing predictions, empty metric vectors, and empty latency samples raise
`MissingEvidenceError`. Pandera/dbt `DatasetValidationResult` stays structural; held-out fixture
scores stay held-out; exported metrics stay `data_class=transformed`.

`configs/proofs/capabilities.json` maps capabilities to usable stages and validators. Only
`evaluation-foundation` has a publisher now; other capabilities refuse as unvalidated.
`proof-manifest.json` records fingerprints, stage statuses, validators, and artifact checksums.
Repository summaries redact configured roots and refuse private paths plus synthetic identity
tokens. The Git-bound exporter still rewrites labels and expected answers together.

CLI: `arxiv-int evaluation evaluate|fixtures|proof`. Make: `eval`, `proof`, and
`evaluation-fixtures-check` (the last is part of `make ci`). Setup marks `evaluate` implemented;
other pipeline stages remain unimplemented. Thresholds in `configs/evaluation/thresholds.json` are
fixture defaults and do not auto-adopt.

This host has a working NVIDIA GPU. The evaluate/proof path scores frozen fixtures on CPU and does
not load models, so CUDA presence is not quality or fit evidence. Parser registration stays
dependency-free: scoring and proof summaries do not import `data_quality` at module load, so
`arxiv-int --help` still runs without optional extras.

Current state: [Evaluation foundation](../current/evaluation-foundation.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Split leakage and provenance | `tests/evaluation/test_fixtures.py::test_split_leakage_refuses_shared_identity_and_gold`; `test_frozen_families_cover_required_kinds_and_splits` | pass; `SplitLeakError`; ledger seed 13 replayed |
| Positive/negative polarities | `test_positive_fixtures_beat_negative_fixtures`; `test_scoring.py` extraction/hierarchy/anomaly cases | pass; every item mean(positive) > mean(negative) |
| Missing evidence refuses verdict | `test_missing_prediction_refuses_a_verdict`; `test_p95_and_empty_metrics_refuse_missing_evidence` | pass; `MissingEvidenceError` |
| Structural vs held-out | `test_structural_quality_is_not_held_out_accuracy` | pass; Pandera result is `structural` |
| Ontology/geo/domain after identity export | `test_ontology_and_geotemporal_negatives_do_not_collapse`; `test_fixture_export.py`; `test_same_name_and_domain_negatives_stay_invalid` | pass; dates/CRS kept; `valid` stays false |
| Proof discovery and unknown capability | `test_proof_discovery_and_unknown_capability`; CLI `evaluation proof publish --capability missing-capability` | pass; `ProofUnknownCapabilityError` |
| Stale fingerprints, checksums, unvalidated stages | `test_proof_publish_rejects_unvalidated_and_stale`; prior `$DATA_DIR/evaluation/0036/` proof check | pass; `ProofStaleError` on code fingerprint after source change; missing checksums and `corpus-foundation` refused |
| Private paths and unobfuscated corpus | `test_repository_summary_refuses_private_paths` | pass; `/home/` refused; `Fixture Person` refused |
| Exporter gate | `test_export_rewrites_labels_and_answers_together` | pass; labels+answers rewritten; `data_class=transformed` |
| Synthetic DATA_DIR run | `$DATA_DIR/evaluation/0036-ci/` | pass; evaluate fingerprint `0cf0c6e3aba6cd8fb7b35414c5d5b8cef81c0c81992335e1d6b2e61592ed1b46`; ledger `d7a867378d206deb83d1426dbfb2f8cd9ce3d6b2e8175a7cee644abfaa5c7974`; proof fingerprint `2a0ba541c4facdf97805a8009aeaa615a4923e6a696e0c8fa78ccc0e463909ab`; summary `capability=evaluation-foundation proof_id=0036-ci verdict=adopt data_class=raw code=62ae059bc078 fixtures=d7a867378d20`. Prior `$DATA_DIR/evaluation/0036/` proof is stale after source edits. Fixture tree, not a provided-archive or CUDA proof |
| Required CI | `make ci` | pass; 892 passed, 20 skipped; format, lint, typing, complexity, doc-links, spec-plan, contracts, ontology, inference schemas, identity-policy check, evaluation-fixtures-check |

## Audit handoff

none identified. Scope stayed on frozen fixtures, paired metrics, the `evaluate` stage, and the
shared proof dispatcher. Human gold review remains in the human lane. Provided-archive proofs and
model-fit claims remain later tasks. The inference/evaluation checkpoint owns cross-module review.

## Close or resume

All required gates passed: deterministic fixture, scoring, evaluate, export, and proof
regressions, synthetic `$DATA_DIR/evaluation/0036-ci/` evidence, documentation,
`make lint-doc-links`, `make lint-spec-plan`, and `make ci` (892 passed, 20 skipped). No gate is
outstanding. Next action: none for this task. Plan counts: 79 tasks before, 78 after (agent lane
69 to 68; human 10 unchanged). Capabilities changed: none added or removed;
`evaluation-foundation` remains planned. Dependents now link this record. Next agent work:
`review-inference-and-evaluation-boundaries`. No commit or push was made.
