# Versioned UDC-derived Classification Scheme

## Task and scope

- Id / capability / checkpoint: `establish-versioned-udc-derived-scheme` / `archive-classification` /
  `review-retrieval-and-classification-boundaries`
- State: accepted; required gates pass.
- Source: [plan](../plan.md) task `establish-versioned-udc-derived-scheme`, selected by the user and
  reported as the next eligible agent task by `make plan-status` (58 tasks: 48 agent, 10 human).
  Code revision `4bf633a`, clean tree.
- Accepted task:

```markdown
#### establish-versioned-udc-derived-scheme

Establish the authorized UDC-derived hierarchy, project extension namespace, special outcomes, and
evaluation labels used to classify archive files.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: [Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
- Human review handoff:
[approve-classification-policy](#approve-classification-policy)
vocabulary, thresholds and exception examples.
Packet: `$RUNS_DIR/<run-id>/review/classification/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`
and `approve-archive-organization-plan`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept/revise the hierarchy, thresholds and exceptional outcomes, or retain unclassified.
- User-visible outcome: Operators can inspect the exact hierarchy, captions, parent links, licence,
local extensions, and version behind every file assignment.
- Scope boundary: Use the distributable UDC Summary or an operator-provided licensed MRF snapshot;
do not redistribute restricted schedules or label project extensions and exceptional outcomes as
official UDC notation.
- Data and artifact paths: `contracts/datasets/classification*.odcs.yaml`,
`configs/classification/`, `src/arxiv_int/classification/vocabulary/`, synthetic classification
fixtures, and `$RUNS_DIR/<run-id>/classification/`; reviewed gold labels stay under the operator's
configured evaluation roots.
- Execution path: Import and checksum the selected vocabulary; parse simple hierarchy, auxiliaries,
and compound notation; define stable local extension ids plus `unclassified` and `unreadable`;
freeze multilingual captions, parent closure, path-safe tokens, and evaluation splits.
- Acceptance gates: Codes and parents round-trip; cycles, orphaned classes, namespace collisions,
missing attribution, and stale snapshots fail validation; the Summary-only baseline works without a
licence secret; unavailable deep schedules yield a documented Summary baseline rather than guessed
classes.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.
```

- Amendments: none. The `contracts/` and `configs/` paths resolve to the packaged
  `src/arxiv_int/resources/contracts/` and `src/arxiv_int/resources/configs/` trees, as for every
  other contract task. Gold label originals stay at the operator's path; only the frozen, validated
  copy and split ledger are written below `$RUNS_DIR/<run-id>/classification/evaluation/`.

## Implementation

Research (2026-09-11). The UDC Summary's conditions of use
(<https://udcsummary.info/about.htm>, exports page) are CC BY-NC 4.0 with redistribution under the
same licence ("last updated August 2012"). The older linked-data page (<https://udcdata.info/>) still
names CC BY-SA 3.0, but its dump is offline pending the MRF12 revision; bulk exports are by email
request. The public browse pages carry the whole Summary as structured `d.add(...)` tree entries per
main class and auxiliary table in 51 languages, including `ru` and `uk`; `robots.txt` is absent. The
specification claimed CC BY-SA 3.0, so its reference row, research note and classification section
were corrected. Because an MIT package must not bundle NC-licensed captions, the repository ships the
policy, parser and importer only; the Summary is imported at operator time into run artifacts, with
attribution recorded and the published licence statement probed at retrieval.

Code:

- `arxiv_int.classification.vocabulary`: `outcomes` (namespaces `udc:`, `ext:`, bare outcomes),
  `notation` (exact lexer and kinds, `simple_parent`), `tokens` (reversible path tokens, ASCII
  slugs), `model` (parent closure, nearest-ancestor resolution with truncation), `policy` (committed
  `scheme.json`/`extensions.json` with fingerprints), `sources` (browse pages merged across
  languages by identical structure; licensed JSONL interchange), `fetch` (explicit download with
  checksums and licence probe), `validate`, `build` (content-addressed scheme id), `snapshot`
  (write, load, staleness check), `describe` and `review` (draft handoff packet).
- `arxiv_int.classification.labels` and `label_command`: gold labels, deterministic stratified
  splits with duplicate groups, `evaluation-items` rows. `commands`, `cli`, `layout` register
  `arxiv-int classification ...`; `make/classification.mk` adds the Make wrappers.
- Contract `classification-classes` (dataset, canonical entity `classification_class`, mapping, 14
  new semantic terms, registry hash, evolution baseline, generated artifacts) and Alembic revision
  `0002` creating `corpus.classification_classes`.
- Reuse and shared fixes: `EXCEPTIONAL_CLASSES` now derives from the shared outcome set;
  `ContractBatchValidator` accepts contracts without a partition key (it previously appended a field
  named `None`). The migration head test now compares with the revision manifest instead of the
  literal `0001`, since the plan calls for additive classification revisions after the prerelease
  consolidation.

Decisions: A composite `(scheme_id, class_id)` key made the shared rule compiler demand per-column
uniqueness (see audit note 1), so the table follows the existing `evaluation_item_id` pattern with a
single `scheme_class_id`. Real data drove two parser kinds: class-own hyphen subdivisions (`531-1`,
`616-001`) are `special` and asterisk forestry subdivisions (`630*2`) are `non_udc`. Gold primaries
are limited to `main`, `simple` and `extension` classes; auxiliaries, ranges, signs and headings stay
facets or alternates. The extension list ships empty until archive evidence justifies an entry.
Current state: [archive classification](../current/archive-classification.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Import and checksum | `make run-create`; `arxiv-int classification fetch-summary --run-id run-a36dcc2e9ca249059857b1dae09a9d46` | pass; 33 pages (11 tags x en/ru/uk) plus licence page in 40 s; `fetch.json` sha256 `b2b154cfae2035167f76848bc23b96428ffe19f889014becbfa3e9f8c6fbf3d6`; licence statement verified |
| Summary baseline without licence secret | `build-scheme --run-id run-a36dcc2e9ca249059857b1dae09a9d46`; `test_summary_builds_without_a_licence_ref` | pass; `udc-summary-be59351e5499`, 2,661 UDC classes plus 2 outcomes, max depth 12, `licenceRef` null, 0 findings; `classes.jsonl` sha256 `6112819ad5d60f656ebcc2d0508fa53989e26fbb019169d84ae1af37deace234` (3,719,272 bytes); manifest sha256 `9db4583f9fe9c8bfb14d9dddb80f4d8b04bd7a06ec5fd2fb34730625b3b677e7` |
| Codes and parents round-trip | `test_notation.py`, `test_tokens.py`, `test_snapshot_round_trips_codes_parents_and_tokens`; real run | pass; 2,661/2,661 real notations rebuild exactly; rows reload equal; closure and tokens recomputed by `check-scheme` |
| Cycles, orphans, namespace collisions, missing attribution fail | `test_validate.py`; `test_extensions_join_the_scheme_and_collisions_block`; `test_unverified_licence_or_missing_mrf_ref_blocks_publication` | pass; blocking builds write only `report.json` |
| Stale snapshots fail | `test_tampered_or_out_of_date_snapshots_are_stale`; `test_stale_scheme_is_refused` | pass; policy, extension, content, row, expected-id and missing-manifest drift report `stale-snapshot`; labels refuse a stale scheme |
| Deep schedules yield the documented Summary baseline | `test_deep_notation_resolves_to_the_nearest_present_class`; `classification show 621.396.67 --run-id ...` | pass; resolves to `udc:621.3` with `truncated: true`; the manifest `depthNote` documents the limit |
| MRF needs a licence reference and is not redistributed | `test_mrf_without_licence_ref_is_not_published` | pass; no manifest without `--licence-ref` |
| Captions, tokens, splits frozen | real run; `test_labels.py` | pass; complete `en`/`ru`/`uk` captions; deterministic stratified splits keep duplicates together |
| Reproducibility | rebuild of the same fetched pages under run id `rebuild-probe` | pass; identical scheme id and content hash |
| Contract and migration | `arxiv-int contracts lint`, `contracts check`, `contracts evolution --skip-live-sql`, `db check` | pass offline; head `0002`; live apply not-run |
| Required CI | `make ci` | pass; 1463 passed, 57 deselected; format, lint, typing, complexity, shell, doc-links, spec-plan, contracts, evolution, db, ontology and inference-schema checks |
| Markdown | `make lint-md` | diagnostic; only two pre-existing over-length lines in `docs/impl/plan.md` (1118, 1620) remain, unchanged from `HEAD` |
| CUDA | n/a | not-run; this task loads no model and uses no GPU |
| Real-archive classification quality | n/a | not claimed; owned by the classify and proof tasks |

The fetched pages and snapshot live under the configured `$RUNS_DIR` and are not committed.

## Audit handoff

| Note | Observation |
| --- | --- |
| `AUD-establish-versioned-udc-derived-scheme-1` | Nonblocking. `arxiv_int.data_quality.rules.field_rules` emits per-column `batch_unique` and `unique` rules for every primary-key column, so a composite ODCS key would wrongly require each column to be unique on its own. No current contract uses one; `classification-classes` uses the single `scheme_class_id`. Next check: compile one composite uniqueness rule or refuse composite keys before a contract declares one. Owner: [checkpoint 0080](0080-archive-cls-review-retrieval-and-classification-boundaries.md). Disposition: resolved by [repair 0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md); a composite primary key is refused at rule compilation. |

Reviewed scope: licence and redistribution boundary, namespace disjointness, notation coverage on
the full real Summary, staleness fingerprints, split leakage, contract and migration generation.

## Close or resume

Accepted. Plan tasks: 58 before (48 agent, 10 human), 57 after (47 agent, 10 human). Capability
`archive-classification` stays planned; it gains an inspectable versioned scheme. Dependents now link
this record, and audit note 1 is routed to `review-retrieval-and-classification-boundaries`. Next
eligible agent task: `implement-hierarchical-file-classification`.

Human review handoff: task [approve-classification-policy](0078-archive-cls-approve-classification-policy.md);
packet `$RUNS_DIR/run-a36dcc2e9ca249059857b1dae09a9d46/review/classification/vocabulary.json`
(scheme `udc-summary-be59351e5499`); readiness: draft vocabulary section only, pending thresholds and
exception examples from the classify task and the provided-archive proof. Inspect with
`make classification-show CLASS=udc:5 RUN_ID=run-a36dcc2e9ca249059857b1dae09a9d46` and
`make classification-check RUN_ID=run-a36dcc2e9ca249059857b1dae09a9d46`. Required decision:
accept/revise the hierarchy, thresholds and exceptional outcomes, or retain unclassified; also
confirm that the CC BY-NC 4.0 Summary terms fit the intended use, and whether `special` or `non_udc`
subdivisions may be primaries. Blocked consumers: `publish-provided-archive-end-to-end-proof` and
`approve-archive-organization-plan`. Nothing was self-approved.

Superseded: [record 0077](0077-archive-cls-adopt-permissive-subject-taxonomy.md) replaced the UDC
Summary vocabulary with the MIT arxiv-int Subject Taxonomy at the user's request; the scheme,
snapshot, label and contract design above carried over.
