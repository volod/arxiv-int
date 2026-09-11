# MIT Subject Taxonomy Replaces the UDC Summary

## Task and scope

- Id / capability / checkpoint: `adopt-permissive-subject-taxonomy` / `archive-classification` /
  `review-retrieval-and-classification-boundaries`
- State: accepted; required gates pass.
- Source: ad hoc user request after [record 0076](0076-archive-cls-establish-versioned-udc-derived-scheme.md)
  reported the UDC Summary licence: replace it with a balanced taxonomy under the MIT licence (or
  compose one from several sources), covering science, construction and technical domains first.
  `make plan-status` reported 57 tasks (47 agent, 10 human); this request was not a plan task. Code
  revision `4bf633a` plus the uncommitted record 0076 work.
- Accepted task:

```markdown
#### adopt-permissive-subject-taxonomy

Replace the UDC Summary vocabulary with a balanced, permissively licensed subject taxonomy so
classification needs one licence and covers science, construction and technical domains first.

- Serves: `archive-classification` --
[Hierarchical archive classification and optional reorganization](../design/spec.md#hierarchical-archive-classification-and-optional-reorganization)
- Agent status: CLEAR
- Research: yes
- Dependencies: [Versioned classification scheme](records/0076-archive-cls-establish-versioned-udc-derived-scheme.md).
- Human review handoff:
[approve-classification-policy](#approve-classification-policy)
taxonomy, captions and source coverage.
Packet: `$RUNS_DIR/<run-id>/review/classification/`.
Draft contribution; the linked proof and other human prerequisites still apply.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`
and `approve-archive-organization-plan`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept/revise the hierarchy, thresholds and exceptional outcomes, or retain unclassified.
- User-visible outcome: Operators classify against one MIT taxonomy that needs no licence, secret or
download, and can browse its balanced tree with English, Russian and Ukrainian captions.
- Scope boundary: Search for a suitable permissive taxonomy (GitHub included) or compose one from
permissively licensed sources; drop the UDC Summary import, fetch and licence probe; keep the
scheme, snapshot, label and contract behaviour. No classifier.
- Data and artifact paths: `configs/classification/{scheme,taxonomy,extensions}.json`,
`configs/classification/sources/`, `src/arxiv_int/classification/`,
`contracts/datasets/classification-classes.odcs.yaml`, and `$RUNS_DIR/<run-id>/classification/`.
- Execution path: Compare candidate taxonomies and licences; author a three-level taxonomy with
trilingual captions; snapshot CC0 OpenAlex subfields and construction topics; require exact-once
coverage and structural balance; rebuild the scheme and contract; run on this host.
- Acceptance gates: The shipped taxonomy carries one licence; every source item maps to exactly one
class; leaves share one depth with bounded fan-out and domain share; every class has en/ru/uk
captions; codes and parents round-trip; stale snapshots fail; `make ci` passes.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.
```

- Amendments: two user messages during the task. The first asked for a GitHub search, with
  `cadmiumkitty/taxonomies-for-confluence` as an example, and allowed composing an own taxonomy.
  The second said the repository was only an example, that OpenAlex is acceptable, and that the
  goal is a balanced classification usable for science, construction, technical and other areas.
  Both are inside the accepted scope.

## Implementation

Research (2026-09-11):

| Candidate | Licence evidence | Decision |
| --- | --- | --- |
| UDC Summary | CC BY-NC 4.0, same-licence redistribution (conditions of use page); uneven depth | rejected |
| OpenAlex domains, fields, subfields, topics | CC0 ("complete dataset is free under the CC0 license", official docs README) | adopted as coverage sources |
| NAICS 2022 | US federal work; Census downloads and data API refused scripted access (403, missing key); Wikidata exposes `P3224` | deferred crosswalk |
| GitHub search (SKOS/taxonomy queries) | only a MIT SKOS editor and unrelated projects; the example repository is MIT tooling for Confluence, not a subject vocabulary | no adoptable taxonomy |
| MSC2020, ACM CCS | not permissively licensed (prior knowledge, not re-checked here) | rejected |

No maintained MIT taxonomy fits, so the project authored its own: `arxiv-int-subjects` 1.0.0 in
`src/arxiv_int/resources/configs/classification/taxonomy.json`, MIT, 10 domains, 67 fields and 298
subfields with two-digit dotted codes and en/ru/uk captions stored as JSON escapes. Structure follows
modern research and industry groupings: science, computing, engineering (12 fields) and construction
(12 fields, 63 subfields covering design, structures, geotechnics, building services, materials and
works, management and estimating, infrastructure, planning and surveying, building types,
regulation, and operation) are detailed first. Each class may list crosswalk ids into the committed
CC0 snapshots `sources/openalex-subfields.json` (252 items) and
`sources/openalex-construction-topics.json` (68 topics under subfields 2205, 2215, 2216).

Code changes: the UDC notation parser, Summary fetch, licence probe and source readers were removed.
New `codes` (code shape, parent, kind) and `coverage` (exact-once coverage and balance gates)
modules; `policy` loads the taxonomy, sources and balance limits; `validate`, `build`, `snapshot`,
`describe`, `review`, `labels` (`primary_code`) and the commands follow the `tax:<code>` namespace.
A new `classification tree` command prints the packaged or frozen tree. The
`classification-classes` contract replaces `notation`/`source_tier` with `code`, `caption_uk` and
`crosswalk_json`; the uncommitted revision `0002`, baseline, registry hash and golden fingerprints
were regenerated. The specification and plan wording now describe the subject taxonomy.

Current state: [archive classification](../current/archive-classification.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| One licence for the shipped taxonomy | `test_packaged_taxonomy_builds_without_findings`; `taxonomy.json` licence | pass; MIT; sources are CC0 and need no attribution |
| Exact-once source coverage | `test_every_source_item_is_covered_exactly_once`; `test_unmapped_duplicate_and_unknown_references_fail` | pass; 252/252 subfields, 68/68 topics; missing, duplicate and unknown ids fail |
| Balance | `test_structure_is_balanced_with_technical_domains_detailed`; `test_shallow_leaf_thin_branch_and_dominant_domain_fail` | pass; all leaves depth 3, fan-out 2-12, largest domain share 0.2114 (limit 0.25) |
| Trilingual captions, ASCII file | `test_captions_are_trilingual_and_the_file_is_ascii`; `test_every_required_caption_language_is_needed` | pass; en/ru/uk on all 375 classes |
| Codes and parents round-trip; stale snapshots fail | `test_codes.py`, `test_model.py`, `test_tokens.py`, `test_build_snapshot.py`, `test_commands.py` | pass; deep codes resolve with `truncated`; policy, taxonomy, source, extension and content drift report `stale-snapshot` |
| Run on this host | `make run-create`; `arxiv-int classification build-scheme\|check-scheme\|show\|tree --run-id run-82735ffc69b34708b0e2971260b65280` | pass; `subjects-1c0d5213ec52`, 377 classes, same id as an in-memory build; `show 04.02.05.03` resolves to `tax:04.02.05` truncated |
| Contract and migration | `contracts lint`, `contracts check`, `contracts evolution --skip-live-sql`, `db check` | pass offline; head `0002`; live apply not-run |
| Required CI | `make ci` | pass; 1408 passed, 57 deselected (after the Make fix); format, lint, typing, complexity, shell, doc-links, spec-plan, contracts, evolution, db (head `0002`), ontology and inference-schema checks |
| Markdown | `make lint-md` | diagnostic; only the two over-length `docs/impl/plan.md` lines that predate this work remain |
| CUDA | n/a | not-run; no model or GPU is involved |
| Caption quality and real-archive fit | n/a | not claimed; ru/uk captions are agent-authored and need native review |

## Audit handoff

`none identified` beyond the still-open
[AUD-establish-versioned-udc-derived-scheme-1](0076-archive-cls-establish-versioned-udc-derived-scheme.md#audit-handoff).
Reviewed: licence boundary of shipped data, coverage bijection per source, balance limits,
namespace and token disjointness, staleness fingerprints, contract regeneration and the removal of
every UDC fetch path.

## Close or resume

Post-acceptance fix (user report): `make classification-tree ROOT=04 DEPTH=2` failed with "scheme has
no manifest.json" because Make's `RUN_ID ?= local` default was forwarded as a run. The tree now
reads a run only when `RUN_ID` is set on the command line or in the environment (or `SCHEME=` is
given); `classification-check` and `classification-show` require a created run id or `SCHEME=`; a
missing snapshot now says to run `build-scheme`. Regressions: `tests/classification/test_make.py`
and `test_failed_build_writes_only_the_report`.

Accepted. Plan tasks unchanged at 57 (47 agent, 10 human); this was an ad hoc task. Capability
`archive-classification` stays planned. Dependents of the scheme now link records 0076 and 0077.
Next eligible agent task: `implement-hierarchical-file-classification`.

Human review handoff: task [approve-classification-policy](../plan.md#approve-classification-policy);
packet `$RUNS_DIR/run-82735ffc69b34708b0e2971260b65280/review/classification/vocabulary.json`
(scheme `subjects-1c0d5213ec52`); readiness: draft taxonomy section, pending thresholds and exception
examples from the classify task and the provided-archive proof. Inspect with
`make classification-tree` and
`make classification-show CLASS=04.06.02 RUN_ID=run-82735ffc69b34708b0e2971260b65280`. Required
decision: accept/revise the hierarchy, thresholds and exceptional outcomes, or retain unclassified;
also have a Russian and a Ukrainian reader review the captions. Blocked consumers:
`publish-provided-archive-end-to-end-proof` and `approve-archive-organization-plan`. Nothing was
self-approved. The superseded UDC run `run-a36dcc2e9ca249059857b1dae09a9d46` still holds fetched
CC BY-NC pages under `$RUNS_DIR`; the operator may delete that run directory.
