# Task Record

## Task and scope

- Id / capability / checkpoint: `approve-representative-corpus-and-gold` / `corpus-foundation` /
  `review-corpus-and-control-integrity`
- State: accepted
- Source: [plan](../plan.md) (task removed on acceptance). Operator request: use the already
  configured representative slice for subsequent proof runs, remove the task, and keep
  documentation abstract.
- Initial count: 80 tasks (69 agent, 11 human).
- Accepted task:

```markdown
#### approve-representative-corpus-and-gold

Select a legally usable, distribution-representative corpus slice and adjudicate the gold
extraction, classification, dedupe, Russian query, entity, fact, ontology, domain-artifact, anomaly
cohorts/hard negatives, three catalogs, and
report samples.

- Serves: `corpus-foundation` -- [Evaluation datasets](../design/spec.md#evaluation-datasets)
- Agent status: BLOCKED BY HUMAN
- Dependencies: Inventory summary from `implement-streaming-inventory`; draft fixture tooling from
`create-evaluation-fixtures-and-metrics`.
- User-visible outcome: Expensive model/store decisions are evaluated on the archive's real formats,
languages, noise, and business questions rather than synthetic convenience data, and one approved
readable path is designated as `PROOF_ARCHIVE_DIR`.
- Scope boundary: Human selects and reviews bounded samples and confirms permission to process them;
no full-corpus authorization.
- Data and artifact paths: Private `$PROOF_ARCHIVE_DIR` used without modification, approved slices,
local review ledgers under `$RUNS_DIR/<run-id>/review/`, and frozen manifests without copied private
text or machine-specific paths in Git.
- Execution path: Produce stratified candidate manifests and draft labels; human reviews source
spans, file classes and exceptional outcomes, duplicate groups, queries, entities, facts, ontology
constraints, design/BOM, equipment, suppliers, invoices, and payments; seal tuning/final splits.
- Acceptance gates: Processing authorization and the readable proof path are explicit; coverage across
major bytes/file types/languages and high-value questions is documented; reviewer decisions and
disagreements are recorded; final split remains unopened for tuning.
- Documentation target: `docs/impl/current/evaluation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

- Amendments: the operator provided the representative slice and designated it as
  `PROOF_ARCHIVE_DIR` in local configuration. Candidate-manifest production, item-level gold
  adjudication, and corpus-specific coverage notes are out of this acceptance. Item-level gold
  fixtures and split seals remain with `create-evaluation-fixtures-and-metrics` and later
  human-gated policy tasks. Repository documentation stays abstract: no machine-specific path and
  no private source description.

## Implementation

The operator authorized a bounded, legally usable, distribution-representative slice for
provided-archive proof runs. Local `.env` names that directory as `PROOF_ARCHIVE_DIR`. The pipeline
reads it without modification. Host write permission on the source path is acceptable.

No inventory, extraction, or gold-label artifacts were produced. No private path, filename, or
source text enters Git. Redacted configuration evidence is under
`$DATA_DIR/corpus-approval/<run-id>/proof-archive-check.json`.

Current-state page: [evaluation.md](../current/evaluation.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Processing authorization | Operator request to use the configured slice for proof runs | pass; bounded slice only, not full-corpus authorization |
| Readable proof path | Runtime `PROOF_ARCHIVE_DIR` check `20260906T160007Z` | pass; configured directory exists, is readable, and is nonempty; path not recorded |
| Coverage documented | [evaluation.md](../current/evaluation.md) | pass; abstract representative-slice description only |
| Reviewer decisions | Operator designated the slice; no competing candidate | pass; no recorded disagreement |
| Final split unopened | No gold scoring or threshold tuning on this slice | pass; item-level gold remains planned |
| `make lint-spec-plan` | `make lint-spec-plan` | pass; 0 findings; 79 tasks (69 agent, 10 human) |
| `make lint-doc-links` | `make lint-doc-links` | pass; 0 broken links |
| `make ci` | `make ci` | pass; 671 passed, 9 skipped |

## Audit handoff

none identified. Reviewed that machine-specific archive paths and private source content stay out
of repository documentation, that this acceptance does not freeze scored gold items, and that later
proof tasks now depend on this record rather than the open human task.

## Close or resume

Accepted after operator authorization and a redacted readable-path check. Plan counts: 80 tasks
before, 79 after (agent lane 69 unchanged; human 11 to 10). Capability `corpus-foundation` remains
planned. Next agent work is unchanged: `implement-dbt-transformation-foundation`. Next human work
is the first remaining human-gated task whose prerequisites resolve. No commit or push was made.
