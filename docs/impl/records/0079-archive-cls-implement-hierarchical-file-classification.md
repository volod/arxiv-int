# Hierarchical File Classification

## Task and scope

- Id / capability / checkpoint: `implement-hierarchical-file-classification` /
  `archive-classification` / `review-retrieval-and-classification-boundaries`
- State: accepted
- Source: [plan](../plan.md), selected 2026-09-11 with 57 remaining tasks (47 agent, 10 human);
  clean worktree at task start.
- Accepted task:

```markdown
#### implement-hierarchical-file-classification

Add a restartable stage that maps every inventoried physical file to primary and alternate
subject-taxonomy classes or one explicit exceptional outcome.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: [Versioned classification scheme](records/0076-archive-cls-establish-versioned-udc-derived-scheme.md);
[MIT subject taxonomy](records/0077-archive-cls-adopt-permissive-subject-taxonomy.md);
[Normalization, dedupe and chunking](records/0062-corpus-implement-normalization-dedupe-and-chunking.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md).
Reviewed real-corpus quality is accepted by the separate proof/human tasks.
[Corpus and control integrity checkpoint](records/0063-corpus-review-corpus-and-control-integrity.md).
- Human review handoff:
[approve-classification-operating-point](#approve-classification-operating-point)
thresholds and exception examples.
Packet: `$RUNS_DIR/<run-id>/review/classification/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`
and `approve-archive-organization-plan`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept/revise the thresholds and exceptional outcomes, or retain unclassified.
- User-visible outcome: Each source file has a searchable, evidence-backed hierarchical assignment,
while random text and extraction failures remain visibly `unclassified` or `unreadable`.
- Scope boundary: Produce mappings and review candidates only; do not move source files, classify
virtual archive members as independently movable files, or force low-confidence assignments.
- Data and artifact paths: `$RESULTS_DIR/normalized/classifications/`, `corpus.file_classification`,
additive `src/arxiv_int/migrations/versions/`, `src/arxiv_int/classification/`, classifier profiles,
and `$RUNS_DIR/<run-id>/evaluation/classification/`.
- Execution path: Combine metadata and normalized-text rules with a measured lightweight classifier;
allow bounded local-model assistance only when it improves held-out results; retain multi-label
scores, one primary ancestor path, decisive evidence, failure taxonomy, and complete fingerprints;
generate and apply reviewed classification Alembic Python revisions from the extended ODCS metadata;
use Polars for batch feature preparation and shared Pandera checks for classification outputs.
- Acceptance gates: Every inventory file appears exactly once; unreadability follows extraction
evidence; exact and ancestor-aware precision/recall, hierarchical distance, calibration, selective
coverage, exceptional-outcome confusion, reproducibility, throughput, and memory meet predeclared
gates. A high `unclassified` or `unreadable` rate is a valid reported result.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.
```

- Amendments: none.

## Implementation

- Registered `classify` after `inventory` and `normalize`. The stage validates the complete
  inventory -> extraction -> normalization identity chain, streams bounded normalized text, and
  publishes one immutable mapping row per physical inventory file. Archive-member text can inform
  its container, but virtual members never become independently movable rows. Its executed
  production quality boundary remains fail closed until contract validation and exact accounting
  pass.
- Added the deterministic `taxonomy-caption-overlap-v1` classifier and a versioned profile. It
  scores English, Russian, and Ukrainian captions separately, combines path/title/text evidence,
  retains ancestor paths and alternate branches, and uses explicit threshold, margin, and minimum
  evidence gates. Inventory or text failures remain `unreadable`; usable low-signal inputs remain
  `unclassified`.
- Added bounded Polars/Parquet feature input, shared Pandera output validation, 64-row atomic
  publication, deterministic rerun checks, complete upstream/configuration fingerprints, runtime
  evidence, and mapping-bound operating-point review packets without source text. Interrupted
  publishers abort before a manifest can seal.
- Added the `file-classifications` product contract and generated artifacts, plus reviewed additive
  Alembic revision `0003`. The revision creates a 16-way hash-partitioned
  `corpus.file_classification`, lookup indexes, protected staging clones for both classification
  datasets, and grants; canonical-store head metadata and load keys now include the new mapping.
- Added frozen-label evaluation for exact multi-label, ancestor-aware, distance, calibration,
  selective-coverage, exceptional-outcome, reproducibility, throughput, and memory gates, exposed
  as `arxiv-int classification evaluate` and `make classification-evaluate`.
- Updated the classification, pipeline, contract, canonical-store, command, and operator current
  state. No source file was moved and no operating point was approved.

Current state: [archive classification](../current/archive-classification.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Interrupted-run integrity | Inspect `run-27551fb96a984b2b8922b8bd3d284b16` attempt and result roots | No partial artifact or seal; empty attempt and zero-byte stage lock only. Source snapshot remained `bcbedbd7d1d471d96899394bd89ffcba785bd6ce7db573970917d03d4587989e`. |
| OCR and normalization recovery | `pipeline run --run-id run-a8e9c160b5584bd09abe83d5b6535d6c --to classify` with the remounted source and writable scratch | Tesseract reran and sealed 414 documents, 48,985 spans, 121 extraction quarantines and 33 reused documents; normalization sealed 414 documents with zero additional quarantines. |
| Complete physical-file mapping | `classify.json` for `run-a8e9c160b5584bd09abe83d5b6535d6c` | 546 classification rows = 546 physical inventory rows; 546 unique occurrence and classification ids; 22 virtual member rows excluded from independent output. |
| Explicit outcome and hierarchy policy | Manifest `counts_by_primary` plus `tests/classification/test_classifier.py` | 7 taxonomy assignments, 431 `unclassified`, 108 extraction-backed `unreadable`; English, Russian and Ukrainian decisions, ancestor paths, alternates, margin, random-text and unreadable cases pass. High exceptional coverage is reported, not treated as quality acceptance. |
| Integrity and interruption behavior | `tests/classification/test_stage.py` | Upstream tampering and inconsistent accounting are refused; interrupted publication leaves no sealed manifest; retry publishes one atomic result. |
| Reproducibility and resources | Final classification manifest | 546/546 decisions reproduced; 15.101 s, 36.157 files/s >= 20; 317.434 MiB <= 512. |
| Sealed artifact validation and cache reuse | `validate_manifest(..., "f687e9605fac9adfd283a697fa2b242e9e2585aef972fcd5d5b430552393f7e1")`; refreshed forecast and unchanged `stage classify` | Contract/checksum validation passed. Identical stage rerun returned `cache_hit=true`, attempt 1, without invoking the worker. |
| Frozen evaluator wiring | `pytest tests/classification -q` and 32-item `synthetic-held-out` report | Exact accuracy 1.0, hierarchical F1 1.0, mean distance 0, calibration error 0, exceptional macro-F1 1.0, 59.1 files/s and 247.0 MiB. These deterministic labels do not prove archive quality. |
| Store migration | `make db-check`; `.data/migrations/0079-classification-v2/live-schema.json` | Head `0003` applied to disposable PostgreSQL 17; 16 mapping partitions, indexes, both protected staging tables and grants inspected; no findings and no input rows. |
| Repository acceptance | `make ci` | pass; 1,424 passed, 57 deselected in 257.68 s; format, lint, typing, doc links, spec/plan, contracts, evolution, migration head `0003`, ontology and structured-output checks passed. |
| Diagnostic quality/build | `make quality` | pass; instrumented suite passed, 85% diagnostic coverage, Markdown checks passed, and wheel/sdist built successfully. |

## Audit handoff

`none identified` after resolving the orchestration boundary omission described below. Reviewed:
source and virtual-member accounting, interrupted publication, lineage and checksum drift,
exception semantics, trilingual scoring, deterministic reruns, contract generation and live schema.

- Scope remained mapping-only: no archive move, rename, or independently movable virtual-member
  output was introduced.
- The supplied archive has no frozen human labels, so the 32-item held-out integration corpus proves
  evaluator/stage wiring only. Real-archive quality remains owned by
  `prove-archive-classification-on-provided-archive` and the human operating-point decision.
- The first archive attempt exposed an operator-path problem: configured `TMP_DIR` was on a
  read-only archive volume. Subsequent attempts used `/tmp/arxiv-int-0079-tmp`; operators should
  keep scratch on a writable non-source filesystem. Route any durable configuration change to the
  provided-archive proof rather than broadening this implementation task.
- The user-requested shutdown killed Tesseract during `extract` in
  `run-27551fb96a984b2b8922b8bd3d284b16`. The attempt contained no files or seal, and its result root
  contained only a zero-byte stage lock. On restart, both archive devices mounted under suffixed
  paths and the implementation fingerprint had changed, so normal drift protection refused reuse.
  A fresh bounded run was selected instead of editing the ledger.
- Replacement run `run-eebd5578b94e4ab7965b97d311d20f88` resealed extraction (414 documents,
  48,985 spans, 121 quarantines) and normalization (414 documents, no normalization quarantines),
  then exposed a missing orchestration route for the classification quality boundary. The generic
  boundary correctly failed closed before invoking the worker. The route and its regression test
  were added; conservative stage identities made the old upstream attempts stale, so a new bounded
  run was required rather than bypassing lineage checks.
- Final run `run-a8e9c160b5584bd09abe83d5b6535d6c` used the same source snapshot and completed
  preflight through classification. Its mapping manifest reconciles every physical item and validates
  at sha256 `f687e9605fac9adfd283a697fa2b242e9e2585aef972fcd5d5b430552393f7e1`.
  The 431 `unclassified` and 108 `unreadable` outcomes are intentionally visible. They require the
  separately owned archive proof and human review rather than threshold adjustment without labels.
- CUDA was available (RTX 4060 Ti, 16 GiB), but the deterministic CPU profile remained selected:
  the task had no real-archive labels with which to justify or evaluate local-model assistance.
- Human task `approve-classification-operating-point` remains pending. Its draft packet is
  `$RUNS_DIR/run-a8e9c160b5584bd09abe83d5b6535d6c/review/classification/operating-point.json`,
  bound to the final manifest digest and containing 5 assigned, 5 ambiguous and 5 exceptional
  examples without source text. Inspect the packet and run
  `arxiv-int classification tree --run-id run-a8e9c160b5584bd09abe83d5b6535d6c --runs-dir "$RUNS_DIR"`.
  After `prove-archive-classification-on-provided-archive`, decide whether to accept or revise the
  thresholds and exceptional outcomes, or retain unclassified, and confirm the Russian and
  Ukrainian captions. Until recorded, `publish-provided-archive-end-to-end-proof` and
  `approve-archive-organization-plan` remain blocked.

## Close or resume

Accepted. The archive run is sealed and the remaining-work plan now contains 56 tasks (46 agent,
10 human), down from 57 (47 agent, 10 human). The human-review draft is ready for the separately
planned provided-archive proof, not yet for decision.
