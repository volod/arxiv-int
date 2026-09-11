# Archive Classification

The versioned classification scheme is built from the **arxiv-int Subject Taxonomy**, a
project-authored hierarchy released under the project's MIT licence. The code includes the
committed policy and taxonomy, CC0 source snapshots with an exact-once coverage gate, a balance gate,
checksummed content-addressed snapshots, staleness checks, class inspection (`show`, `tree`), and
frozen gold-label splits. The `classify` stage that assigns files to the scheme is not implemented;
see
[implement-hierarchical-file-classification](../plan.md#implement-hierarchical-file-classification).

See [record 0076](../records/0076-archive-cls-establish-versioned-udc-derived-scheme.md) (first
scheme, built on the UDC Summary and superseded) and
[record 0077](../records/0077-archive-cls-adopt-permissive-subject-taxonomy.md) (current taxonomy).

## Subject taxonomy

`src/arxiv_int/resources/configs/classification/taxonomy.json` (`arxiv-int-subjects` version
`1.0.0`, MIT) lists 375 classes: 10 domains, 67 fields and 298 subfields. Codes use two digits per
level (`04`, `04.02`, `04.02.01`); the parent is the code without its last segment, and the kind
follows the depth. Every class has English, Russian and Ukrainian captions, stored as JSON escapes
so the file stays ASCII. Science, computing, engineering and construction are detailed first:

| Code | Domain | Fields | Subfields |
| --- | --- | --- | --- |
| `01` | Natural sciences | 6 | 40 |
| `02` | Computing and information technology | 7 | 29 |
| `03` | Engineering and technology | 12 | 58 |
| `04` | Construction and built environment | 12 | 63 |
| `05` | Medicine and health | 6 | 22 |
| `06` | Agriculture, food and forestry | 5 | 13 |
| `07` | Economics, business and finance | 6 | 26 |
| `08` | Law, government and public administration | 4 | 18 |
| `09` | Social sciences, education and communication | 5 | 17 |
| `10` | Humanities and arts | 4 | 12 |

The construction domain covers architecture, structures, geotechnics, building services,
materials and works, management and estimating, transport and utility infrastructure, planning and
surveying, building types, regulation, and operation and renovation.

## Sources and coverage

Source snapshots under `configs/classification/sources/` are CC0 data from OpenAlex, retrieved
2026-09-11: all 252 subfields, and the 68 topics below the three construction-related subfields.
Each class lists `crosswalk` ids (`openalex:subfield/2205`, `openalex:topic/T10479`). The build
requires every source item to map to exactly one class and every crosswalk id to exist, so topic
coverage is checked rather than assumed. The UDC Summary was rejected: its terms are CC BY-NC 4.0
with same-licence redistribution, and its depth is uneven. No suitable MIT taxonomy was found on
GitHub.

## Balance

`scheme.json` sets the limits: every taxonomy leaf at depth 3, every parent with 2 to 16 children,
and no domain above 25% of subfields. The shipped taxonomy has fan-out 2 to 12 and a largest domain
share of 21.1% (construction).

## Namespaces and outcomes

| Namespace | Id form | Meaning |
| --- | --- | --- |
| `tax` | `tax:<code>` | Shipped taxonomy class |
| `ext` | `ext:<name>` | Operator-local subdivision with an explicit `tax:` or `ext:` parent (`extensions.json`, empty) |
| `outcome` | `unclassified`, `unreadable` | Mandatory outcomes with no parent |

`arxiv_int.evaluation.scoring.constants.EXCEPTIONAL_CLASSES` reuses the same outcome set. Gold
primaries may be domains, fields, subfields or extensions.

## Snapshot build and validation

`build-scheme` validates duplicate ids, codes against ids, kinds and parents, orphans and cycles,
namespace collisions, required captions, token round-trip, overlong and colliding tokens, taxonomy
and source licences, coverage, and balance. A blocking finding writes only `report.json`. A
publishable build freezes rows with parent closure, captions, crosswalk, reversible `path_token` and
ASCII `slug`; rows pass the `classification-classes` contract before
`$RUNS_DIR/<run-id>/classification/scheme/{classes.jsonl,report.json,manifest.json}` is written.

The scheme id `subjects-<sha12>` hashes the scheme-independent row content, so the same taxonomy
gives the same id in every run. `check-scheme` recomputes checksums, content hash, closure and
tokens, re-runs validation, and compares policy, taxonomy, source, extension and builder
fingerprints; any drift is `stale-snapshot`. A code deeper than the taxonomy resolves to its nearest
present class with `truncated: true`.

Tokens are `t<code>`, `x-<name>`, `_unclassified` and `_unreadable`; only `[0-9a-z.-]` pass
through, and other bytes, `_` and a trailing `.` become `_hh`.

## Evaluation labels

`freeze-labels` reads gold JSONL rows (`item_id`, `gold_ref`, `primary` or `primary_code`, and
optional `alternates`, `content_sha256`, `split`) from an operator path and refuses a stale scheme.
A deep `primary_code` records `truncated_from`. Items sharing a content hash (or gold reference)
form one group with one split; undeclared groups are balanced per domain by a seeded hash order.
Output below `$RUNS_DIR/<run-id>/classification/evaluation/<label-set>/` is `labels.jsonl` (the
`path`/`primary` shape scored by `score_classification`), `evaluation-items.jsonl` (validated
against `evaluation-items`) and `splits.json`.

## Contract and store

Product ODCS `classification-classes` binds `corpus.classification_classes` with the single key
`scheme_class_id` (`<scheme id>:<class id>`) and columns for the code, captions in three languages,
crosswalk and path token; Alembic revision `0002` creates the table. Loading snapshots into the
store belongs to the classify stage.

## Commands

`arxiv-int classification build-scheme|check-scheme|show|tree|freeze-labels`, with Make wrappers
`classification-scheme`, `classification-check`, `classification-show`, `classification-tree` and
`classification-labels`; see the
[command reference](../../guide/commands.md#classification-vocabulary). `tree` prints codes and
English captions of the packaged taxonomy without a run. `build-scheme` also writes a draft
`$RUNS_DIR/<run-id>/review/classification/vocabulary.json` packet for
`approve-classification-policy`; it is not an approval and carries no thresholds yet.

## Maintaining the taxonomy

Add or rename classes in `taxonomy.json` with all three captions, map any new source item, and bump
`version`; the build refuses gaps, duplicates, unbalanced branches and unknown crosswalk ids. A new
version yields a new scheme id, and existing snapshots report `stale-snapshot`. Archive-specific
subdivisions belong in `extensions.json` rather than the shipped taxonomy.

## Evidence on this host

Run `run-82735ffc69b34708b0e2971260b65280` (2026-09-11) published `subjects-1c0d5213ec52`: 377
classes (375 taxonomy plus 2 outcomes), no findings, coverage 252/252 and 68/68, the same id as an
independent in-memory build. It uses no GPU and makes no real-archive classification-quality claim.

## Tests

`tests/classification/` covers codes, tokens, closure and resolution, every validation finding,
coverage and balance gates, build identity and staleness, the packaged taxonomy (licence, coverage,
balance, trilingual captions, ASCII file), labels and splits, and the CLI end to end.
