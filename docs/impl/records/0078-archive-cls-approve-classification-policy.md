# Classification Taxonomy Approval

## Task and scope

- Id / capability / checkpoint: `approve-classification-policy` / `archive-classification` /
  `review-investigation-and-report-integrity`
- State: accepted
- Source: [plan](../plan.md) (task removed on acceptance). Operator decision on 2026-09-11 after
  reviewing the tree with `make classification-tree`: "It is accepted." Initial count: 57 tasks
  (47 agent, 10 human).
- Accepted task:

```markdown
#### approve-classification-policy

Review the hierarchy and confidence/exception policy without authorizing any file placement.

- Serves: `archive-classification` -- [Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: HUMAN-GATED
- Dependencies: `prove-archive-classification-on-provided-archive`.
- User-visible outcome: The owner accepts the classification operating point, vocabulary,
exceptional outcomes,
and coverage limits for use in archive browsing and future organization plans.
- Scope boundary: Approve one versioned classification policy only; this neither chooses a
destination nor
authorizes copying or moving files.
- Data and artifact paths: `configs/policy/classification.yaml`, vocabulary manifest, and
`$RUNS_DIR/<run-id>/review/classification/`.
- Execution path: Present hierarchical errors, ancestor metrics, ambiguous/exception samples, thresholds,
calibration, attribution and review effort; record accept, revise, or retain-unclassified.
- Acceptance gates: The exact vocabulary/profile/policy fingerprints and decision are recorded; low-confidence
files remain exceptional; no filesystem mutation is requested.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-investigation-and-report-integrity`.
```

- Amendments: the operator accepted the vocabulary half of this task: the hierarchy, English
  captions, source coverage and balance of the MIT arxiv-int Subject Taxonomy, as shown by
  `make classification-tree`. The classifier operating point (thresholds, calibration, exception
  samples, coverage limits) cannot be judged yet, because the classifier and its provided-archive
  proof do not exist; it moves unchanged in intent to the new human task below, which keeps the
  proof dependency and the gate on every downstream consumer. Russian and Ukrainian captions were not
  displayed by the reviewed command, so their review is carried into that task.

```markdown
#### approve-classification-operating-point

Accept the classifier operating point on the approved subject taxonomy without authorizing any file
placement.

- Serves: `archive-classification` -- [Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: HUMAN-GATED
- Dependencies: `prove-archive-classification-on-provided-archive`;
[Classification taxonomy approval](records/0078-archive-cls-approve-classification-policy.md).
- User-visible outcome: The owner accepts the thresholds, calibration, exceptional-outcome handling
and coverage limits used for archive browsing and future organization plans.
- Scope boundary: Approve one versioned operating point on the approved taxonomy only; the taxonomy
itself was accepted separately. This neither chooses a destination nor authorizes copying or moving
files.
- Data and artifact paths: `configs/policy/classification.yaml`, classifier profile, scheme
manifest, and `$RUNS_DIR/<run-id>/review/classification/`.
- Execution path: Present hierarchical errors, ancestor metrics, ambiguous/exception samples,
thresholds, calibration and review effort; confirm the Russian and Ukrainian captions; record accept,
revise, or retain-unclassified.
- Acceptance gates: The exact scheme/profile/policy fingerprints and decision are recorded;
low-confidence files remain exceptional; no filesystem mutation is requested.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-investigation-and-report-integrity`.
```

## Implementation

Decision: **accept** the taxonomy. It is pinned to these fingerprints, recorded in
`$RUNS_DIR/run-82735ffc69b34708b0e2971260b65280/review/classification/taxonomy-decision.json`:

| Item | Value |
| --- | --- |
| Taxonomy | `arxiv-int-subjects` 1.0.0, MIT; `taxonomy.json` sha256 `18ce5c7f0a5be1a07d52d0fb5442e61b7f321c272f4eb93691b61845107b8878` |
| Scheme | `subjects-1c0d5213ec52` (`1.0.0+1c0d5213ec52`), content sha256 `1c0d5213ec52493eecee69fedbca19f454ba51d99ddfe799aa4cd6a3f5e1e53f` |
| Policy | `scheme.json` 2.0.0, sha256 `1e4684428ce7ff1365ae5fda895545c409c4c66031bbc072d4b11ceadf1f747d` |
| Extensions | none; sha256 `6075aa27b34e1a528e56eb33f027c1cf1310d7b0635a1164ee62331de0ff091e` |
| Sources | `openalex-subfields` `fc0dc2a463867d10d416d20c9f64dbef24698b974e9d361e8a6380c3dd8af37c`; `openalex-construction-topics` `b18e723d8fa64ba9ae943f7b7555ba174f3bb347a66088b5900d23e9a6ff8245` |
| Run and manifest | `run-82735ffc69b34708b0e2971260b65280`; manifest sha256 `71cd256e51f94974d16d542aa415673894e079858ae2c2d99d93ac6725516e31` |

A changed `taxonomy.json` (new sha256) is not covered by this decision and needs a new taxonomy
decision before downstream use. The build-scheme review packet now names the open
`approve-classification-operating-point` task. No file placement or filesystem mutation was
requested. Current state: [archive classification](../current/archive-classification.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Exact fingerprints and decision recorded | `taxonomy-decision.json` in the run's review packet; table above | pass for the taxonomy; operating-point fingerprints do not exist yet |
| Reviewed snapshot is current | `arxiv-int classification check-scheme --run-id run-82735ffc69b34708b0e2971260b65280` | pass; "scheme snapshot is intact and current"; taxonomy sha256 equals the committed file |
| Low-confidence files remain exceptional | n/a | not-run; moved to `approve-classification-operating-point` with the classifier |
| No filesystem mutation requested | decision scope | pass; no placement, copy or move |
| Required CI | `make ci`; `make lint-doc-links lint-spec-plan` | pass; 1408 passed, 57 deselected; 0 broken links, 0 spec-plan findings |

## Audit handoff

`none identified`. Reviewed: the decision is pinned to exact fingerprints, the unfinished
operating-point decision stays gated by its own human task, and every consumer that depended on this
task now depends on that task.

## Close or resume

Accepted for the taxonomy. Plan tasks stay at 57 (47 agent, 10 human): this human task is removed
and `approve-classification-operating-point` replaces it for the operating point. Dependents
`implement-hierarchical-file-classification`, `prove-archive-classification-on-provided-archive`,
`publish-provided-archive-end-to-end-proof`, `authorize-full-corpus-run` and
`approve-archive-organization-plan` now reference the new task. Capability `archive-classification`
stays planned. Next human decision: `approve-classification-operating-point`, blocked until the
classifier and its provided-archive proof exist.
