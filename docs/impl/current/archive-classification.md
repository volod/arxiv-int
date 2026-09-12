# Archive Classification

The versioned classification scheme is built from the **arxiv-int Subject Taxonomy**, a
project-authored hierarchy released under the project's MIT licence. The code includes the
committed policy and taxonomy, CC0 source snapshots with an exact-once coverage gate, a balance gate,
checksummed content-addressed snapshots, staleness checks, class inspection (`show`, `tree`), and
frozen gold-label splits. The restartable `classify` stage assigns every physical inventory file
exactly once to a taxonomy class or the explicit `unclassified`/`unreadable` outcomes; see
[record 0079](../records/0079-archive-cls-implement-hierarchical-file-classification.md).

See [record 0076](../records/0076-archive-cls-establish-versioned-udc-derived-scheme.md) (first
scheme, built on the UDC Summary and superseded) and
[record 0077](../records/0077-archive-cls-adopt-permissive-subject-taxonomy.md) (current taxonomy) and
[record 0078](../records/0078-archive-cls-approve-classification-policy.md) (taxonomy approval).

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

## Approval

On 2026-09-11 the operator reviewed the tree with `make classification-tree` and accepted taxonomy
`arxiv-int-subjects` 1.0.0 (`taxonomy.json` sha256 `18ce5c7f...`, scheme `subjects-1c0d5213ec52`);
see [record 0078](../records/0078-archive-cls-approve-classification-policy.md). The acceptance
covers the hierarchy, English captions, source coverage and balance. A changed `taxonomy.json`
needs a new taxonomy decision before downstream use. Thresholds, calibration, exception handling,
coverage limits and the Russian and Ukrainian captions await
[approve-classification-operating-point](../plan.md#approve-classification-operating-point), after
the classifier and its provided-archive proof exist.

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

## Classification stage

The deterministic `taxonomy-caption-overlap-v1` profile combines normalized text, titles and the
original relative path with separately scored English, Russian and Ukrainian class captions.
Domain, field and subfield candidates receive multi-label scores. A primary threshold, a minimum
feature count and a margin gate prevent weak or cross-branch evidence from forcing a taxonomy
assignment; qualifying secondary branches remain alternates. Each accepted decision retains the
matched terms and normalized-document offsets. Inventory or extraction failures produce
`unreadable`; usable low-signal and random text produce `unclassified`.

Classification consumes checksum-validated inventory, extraction and normalization manifests. It
streams normalized Parquet batches through Polars, reads at most 120,000 characters across each
physical file and its archive members, and validates each output batch with the shared Pandera
contract rules. Virtual archive members may inform their physical container but never receive an
independently movable row. The stage checks every decision twice, reconciles its row count with the
physical inventory denominator, publishes atomically in 64-row batches, and leaves no sealed
snapshot after interruption. It never moves source files.

The manifest records class distribution, thresholds, policy/scheme/upstream fingerprints,
reproducibility, elapsed time, throughput and peak memory. The draft review packet at
`$RUNS_DIR/<run-id>/review/classification/operating-point.json` binds the exact mapping checksum and
contains bounded assigned, ambiguous and exceptional examples without source text.

`classification evaluate` joins a sealed mapping to a frozen held-out label set and writes
`$RUNS_DIR/<run-id>/evaluation/classification/<label-set>/metrics.json`. It reports exact accuracy,
precision/recall/F1 across primary and alternate labels,
ancestor precision/recall/F1, mean tree distance, ten-bin calibration error, selective coverage,
exceptional-outcome confusion and macro-F1, reproducibility, throughput and peak memory against the
predeclared profile gates. Fixture metrics validate the evaluator and wiring; only the separate
provided-archive proof and human decision may establish real-corpus quality.

## Contract and store

Product ODCS `classification-classes` binds `corpus.classification_classes` with the single key
`scheme_class_id` (`<scheme id>:<class id>`) and columns for the code, captions in three languages,
crosswalk and path token. Product ODCS `file-classifications` binds the complete mapping to
`corpus.file_classification`, including source identity, primary/alternate classes, ancestor path,
confidence/calibration, scores, evidence/failure reason and producer fingerprints. Alembic `0002`
creates the scheme table; reviewed additive `0003` creates the mapping as a 16-way HASH-partitioned
table, adds class/document/scheme lookup indexes, and provides protected staging clones for both
classification datasets. Head `0003` was applied and inspected on a disposable PostgreSQL 17 store
with no catalog findings.

## Commands

`arxiv-int classification build-scheme|check-scheme|show|tree|freeze-labels|evaluate`, with Make wrappers
`classification-scheme`, `classification-check`, `classification-show`, `classification-tree` and
`classification-labels` plus `classification-evaluate`; see the
[command reference](../../guide/commands.md#classification-vocabulary). `tree` prints codes and
English captions of the packaged taxonomy without a run. `build-scheme` also writes a draft
`$RUNS_DIR/<run-id>/review/classification/vocabulary.json` packet for
`approve-classification-operating-point`. Running `classify` replaces this vocabulary-only draft
with a mapping-bound operating-point draft; neither packet is an approval.

## Maintaining the taxonomy

Add or rename classes in `taxonomy.json` with all three captions, map any new source item, and bump
`version`; the build refuses gaps, duplicates, unbalanced branches and unknown crosswalk ids. A new
version yields a new scheme id, and existing snapshots report `stale-snapshot`. Archive-specific
subdivisions belong in `extensions.json` rather than the shipped taxonomy.

## Evidence on this host

Run `run-82735ffc69b34708b0e2971260b65280` (2026-09-11) published `subjects-1c0d5213ec52`: 377
classes (375 taxonomy plus 2 outcomes), no findings, coverage 252/252 and 68/68, the same id as an
independent in-memory build. The classification implementation was exercised on this CUDA host
(RTX 4060 Ti, 16 GiB); the deterministic CPU profile was retained because no frozen real-archive
labels justify local-model promotion. The frozen 32-item integration fixture produced exact and
hierarchical scores of 1.0, mean distance 0, calibration error 0, exceptional macro-F1 1.0,
59.1 files/s and 247.0 MiB peak memory. These are wiring/regression results, not a real-archive
quality claim.

After the operator stopped Tesseract for a host shutdown, the interrupted stage-attempt directory
had no files or seal, while the result root contained only an empty stage lock. The source snapshot
was unchanged after remount. Conservative
identity checks rejected reuse after mount and implementation drift, so run
`run-a8e9c160b5584bd09abe83d5b6535d6c` reran Tesseract and the full bounded chain. Extraction sealed
414 documents and 48,985 spans, with 121 quarantines and 33 reused documents; normalization sealed
all 414 documents with no additional quarantine.

The final classification manifest accounts for all 546 physical inventory rows exactly once and
excludes 22 virtual archive members from independently movable output. It contains 7 taxonomy
assignments, 431 `unclassified` outcomes and 108 extraction-backed `unreadable` outcomes. All 546
decisions reproduced; classification ran in 15.1 seconds at 36.2 files/s with 317.4 MiB peak memory.
The manifest digest is `f687e9605fac9adfd283a697fa2b242e9e2585aef972fcd5d5b430552393f7e1`,
and an unchanged rerun was a cache hit. The high exceptional count is a valid complete result, not
a quality claim; archive-label evaluation and the human operating-point decision remain pending.
The complete interruption and rerun audit is in record 0079.

## Tests

`tests/classification/` covers codes, tokens, closure and resolution, every validation finding,
coverage and balance gates, build identity and staleness, the packaged taxonomy (licence, coverage,
balance, trilingual captions, ASCII file), labels and splits, classifier decisions and evidence,
physical/member accounting, interruption/retry, upstream tamper refusal, evaluation metrics and the
CLI end to end.
