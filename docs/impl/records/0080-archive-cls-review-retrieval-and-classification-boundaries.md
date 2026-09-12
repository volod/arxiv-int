# Task Record

## Task and scope

- Id / capability / checkpoint: `review-retrieval-and-classification-boundaries` /
  `archive-classification` / none; this is the bounded checkpoint
- State: accepted
- Source: `docs/impl/plan.md#review-retrieval-and-classification-boundaries` at `d5a4901`;
  code revision `d5a4901`, clean working tree at task start.
- Accepted task:

```markdown
#### review-retrieval-and-classification-boundaries

Review searchable/classifiable corpus accounting before archive quality and policy review.

- Serves: `archive-classification` -- [Development
integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Dependencies: [Checkpoint 0063](records/0063-corpus-review-corpus-and-control-integrity.md);
[Russian lexical calibration second
opinion](records/0072-lexical-review-and-deepen-russian-lexical-calibration.md);
[Versioned classification
scheme](records/0076-archive-cls-establish-versioned-udc-derived-scheme.md);
[MIT subject taxonomy](records/0077-archive-cls-adopt-permissive-subject-taxonomy.md);
[Hierarchical file
classification](records/0079-archive-cls-implement-hierarchical-file-classification.md);
[Evidence and source location
lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md).
- Audit inputs:
[AUD-review-corpus-and-control-integrity-7](records/0063-corpus-review-corpus-and-control-integrity.md#audit-handoff);
[AUD-build-paradedb-lexical-1](records/0070-lexical-build-paradedb-lexical-load-and-query-path.md#audit-handoff);
[AUD-review-and-deepen-russian-lexical-calibration-1](records/0072-lexical-review-and-deepen-russian-lexical-calibration.md#audit-handoff);
[AUD-review-and-deepen-russian-lexical-calibration-2](records/0072-lexical-review-and-deepen-russian-lexical-calibration.md#audit-handoff);
[AUD-review-and-deepen-russian-lexical-calibration-3](records/0072-lexical-review-and-deepen-russian-lexical-calibration.md#audit-handoff);
[AUD-build-paradedb-lexical-2](records/0070-lexical-build-paradedb-lexical-load-and-query-path.md#audit-handoff);
[AUD-establish-versioned-udc-derived-scheme-1](records/0076-archive-cls-establish-versioned-udc-derived-scheme.md#audit-handoff).
- User-visible outcome:
Retrieval and classification proofs consume coherent source, vocabulary and query identities.
- Scope boundary:
Inspect fixture/store integration and retained calibration evidence before the provided-archive
proofs. This review neither accepts a classification policy nor authorizes file placement.
Review integrated behavior, not just test totals; no speculative rewrite or model promotion.
- Data and artifact paths: Accepted producer records, current fixtures and retained proof evidence;
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path:
Trace source/chunk/query ids, Russian normalized versus literal identifiers, hierarchy/ancestor
metrics, excluded/unreadable/unclassified denominators, stale mappings, duplicate source occurrence
lookup and empty results. Verify candidate policy packets expose errors and exact fingerprints.
Map each producer invariant to evidence; add missing behavior regressions at stable seams.
- Acceptance gates:
Indexed, excluded and failed rows reconcile; snippets and class assignments resolve to sources;
unknown classes and low-confidence assignments stay exceptional; changed tokenizer/vocabulary
invalidates affected outputs. No relevance or classification-quality claim follows from counts.
Record refactor/no-refactor and proceed/proceed-with-nonblocking-notes/blocked verdicts. Plan a
focused prerequisite repair for any blocker and keep this checkpoint open until it passes.
Run `make ci`; coverage is diagnostic. Route each nonblocking note to one explicit owner.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: none; this is the bounded checkpoint.
```

- Amendments: none.

## Implementation

No refactor was made under this record. The round traced the integrated seams below, planned one
focused prerequisite repair for the blockers it found, and added the stage regressions that existing
tests did not cover.

Traced seams and what each trace established:

- **Source, chunk and query ids.** `classification/source.py` validates the inventory,
  normalization and extraction manifests by checksum before any read, joins occurrences by
  `(silo_id, relative_path)`, and de-duplicates the document ids behind one physical file.
  `occurrence_id` is `sha256([silo_id, relative_path, members])` and `classification_id` is
  `sha256([occurrence_id, scheme_id, classifier_id])`, so a vocabulary or classifier change yields
  new rows while a content change at the same path relies on `generation_id`, the row's
  `extraction_fingerprint` and `normalizer_id` to separate generations. `load_lexical/source.py`
  validates the chunk chain the same way and `proj_lexical_rows.sql` carries `chunker_id` and the
  source generation into the projection.
- **Russian normalized versus literal identifiers.** `body` and `title` are Russian-stemmed and
  stopworded; `identifiers` uses a whitespace tokenizer with lowercasing disabled, and
  `lookup()` sends the value verbatim through `paradedb.term`, so literal case survives. The
  literal field is currently fed the chunk id, which is note 1 below.
- **Hierarchy and ancestor metrics.** `ancestor_path` is the scheme path joined with `>`;
  `evaluation._hierarchy` scores set overlap and common-prefix distance from it, and
  `snapshot._derived_findings` re-derives each row's closure, depth and path token from the parent
  links before a snapshot may be reused.
- **Denominators.** `publish.finish` refuses to seal unless `classified_rows` equals
  `physical_inventory_rows`, where the physical count is the inventory row count minus the rows
  that carry archive members. `counts_by_primary` carries `unclassified` and `unreadable`
  separately. The one denominator that was missing, a file classified from partially read text,
  is repaired by
[0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md).
- **Stale mappings.** `check_snapshot` recomputes file checksums, content identity, row scheme ids,
  derived closure and tokens, and compares the builder, policy, taxonomy, source and extension
  fingerprints with the current configuration; `classify` refuses to run on a stale snapshot.
  `stages.py` puts the whole `classification` package and `resources/configs/classification` in the
  stage's `code_paths`, so an edited taxonomy invalidates the stage's reuse key. The equivalent
  check was missing on the lexical side and is repaired by [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md).
- **Duplicate source occurrence lookup and empty results.** `query/evidence/resolve.py` collects
  every occurrence sharing a document's content hash and reports `ambiguous source locations`
  rather than picking one, which `tests/query/evidence/test_resolve.py` covers. An empty ranked
  search is a successful query; only an unresolved identifier lookup exits non-zero.
- **Candidate policy packets.** The operating-point packet binds the mapping manifest path and
  checksum, the classifier and scheme identities, the class distribution and bounded
  assigned/ambiguous/exceptional samples with their failure reasons, and stays `readiness: draft`
  with the proof named as pending. It omitted the upstream corpus identities and the accounting
  denominators, which the repair record
  [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md) adds.

Coverage limit: the round read and reasoned about the Postgres-backed paths but could not execute
them. `arxiv-int-database-1` is in a restart loop on this host because `PGDATA_DIR` is empty and
root-owned while the container runs as uid 1000, so `make test-heavy` and `make test-archive` did
not run and no live ParadeDB projection exists. Live retrieval evidence therefore remains
[0073](0073-lexical-prove-lexical-retrieval-on-provided-archive.md)'s and
[0074](0074-lexical-retract-superseded-lexical-chunks.md)'s, which predate this round's changes to
the projection identity check.

Tests added by this checkpoint (beyond the repair's own regressions):
`tests/classification/test_stage.py::test_every_assigned_class_and_ancestor_resolves_to_a_published_scheme_row`
asserts at the stage seam that every published primary class and every ancestor segment resolves to
a `classification-classes` row of the same scheme, that alternates are never exceptional outcomes,
and that an exceptional row carries a failure reason and a single-segment path. Scheme staleness,
duplicate-occurrence ambiguity, physical/virtual accounting, interruption and reproducibility were
already covered and needed no addition.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Indexed, excluded and failed rows reconcile | `publish.ClassificationPublisher.finish` accounting refusal; `tests/classification/test_stage.py::test_stage_maps_every_physical_file_once_with_explicit_outcomes`, `::test_virtual_archive_member_informs_but_does_not_duplicate_container_row` | pass on fixtures; lexical load/retract reconciliation traced statically, live evidence is 0073/0074 |
| Class assignments resolve to published scheme rows | `tests/classification/test_stage.py::test_every_assigned_class_and_ancestor_resolves_to_a_published_scheme_row` | pass; added by this checkpoint |
| Snippets and evidence resolve to sources | reproduced the defect, then `tests/classification/test_classifier.py::test_evidence_spans_address_real_token_occurrences_in_a_named_space` | blocked at review, repaired by [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md); now pass |
| Unknown classes and low-confidence assignments stay exceptional | `tests/classification/test_classifier.py::test_low_signal_content_is_not_forced_into_the_taxonomy`, `::test_unreadable_requires_recorded_upstream_failure`; namespace disjointness in `vocabulary/outcomes.py` | pass |
| Changed tokenizer/vocabulary invalidates affected outputs | `tests/classification/vocabulary/test_build_snapshot.py::test_tampered_or_out_of_date_snapshots_are_stale`; `tests/retrieval/test_projection_identity.py::test_a_projection_built_under_another_profile_is_refused` | vocabulary side already held; the tokenizer side was blocked at review and is repaired by [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md) |
| Candidate policy packets expose errors and exact fingerprints | `tests/classification/test_stage.py::test_review_packet_names_the_upstream_chain_and_its_denominators` | blocked at review, repaired by [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md); now pass |
| Prerequisite repair passes | [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md) acceptance table | pass |
| Required gate | `make ci` | pass; 1439 passed, 57 deselected (baseline at task start: 1424) |
| Markdown, links, plan integrity | `make lint-md`, `make lint-spec-plan` | pass; 0 broken links, 0 findings |
| Diagnostic suite | `make quality` | pass; coverage 85 percent, Markdown and package build clean. A coverage percentage is not an acceptance signal. |
| Live ParadeDB and provided-archive checks | `make test-heavy`, `make test-archive` | not-run; host database container restarting, see the coverage limit above |

No relevance or classification-quality claim follows from these counts. Fixture evidence does not
establish real-archive quality or CUDA fit.

## Audit handoff

Coverage: the six producer records named as dependencies; `src/arxiv_int/classification/` and its
`vocabulary/` package; `src/arxiv_int/retrieval/`; `src/arxiv_int/stores/projections/` and
`stores/postgres/selection.py`; `src/arxiv_int/pipeline/load_lexical/`;
`src/arxiv_int/query/evidence/`;
the `classify` and `load-lexical` entries in `pipeline/dag/stages.py` and
`pipeline/control/owned.py`;
`data_quality/rules/`; and the seven routed notes. Coverage limit as recorded above: no
Postgres-backed path was executed.

Incoming notes and their dispositions:

| Source round and concern | Note and disposition |
| --- | --- |
| Corpus and control integrity, corpus identities into the store and its activation gate | `AUD-review-corpus-and-control-integrity-7`. Resolved. The chunk, normalization and extraction manifests are rehashed before any read and retained as checksum-bound pointers in the load manifest; loaded rows keep `generation_id`, `chunker_id` and `contract_version`, and the projection model carries them forward. Activation requires a publishable build, an active pointer, and now the engine profile that built the version. No further work. |
| ParadeDB lexical load, projection commands cannot reach the configured service | `AUD-build-paradedb-lexical-1`. Resolved. Decision: the canonical-store selection fallback *is* specified behavior for `projections-build`, `-status` and `-cleanup`, because they act on the store `load-lexical` loads and `retrieval/commands.py` queries; `not-run` now means no store configuration exists at all. Implemented by [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md). |
| ParadeDB lexical load, shared executor code invalidates every stage | `AUD-build-paradedb-lexical-2`. Reconciled, no change. `pipeline/dag/execute.py` decides reuse and where each stage publishes, so every stage's output depends on it; exempting it the way `stages.py` is exempt would let an edited executor reuse artifacts it did not produce. `stages.py` is exempt only because it is the declaration table the fingerprinter itself reads. The remaining cost question is carried forward as nonblocking note 5 below. |
| Russian lexical calibration, transliteration no-answer collisions | `AUD-review-and-deepen-russian-lexical-calibration-1`. Reconciled, no change here. Deciding an English lexicon or length rule needs archive-query measurement that this `CLEAR` round cannot produce, and the host has no live projection. Carried forward as nonblocking note 6 below. |
| Russian lexical calibration, wrong-layout text becomes query syntax | `AUD-review-and-deepen-russian-lexical-calibration-2`. Resolved. Reproduced: `gjcnfdrf[` and `['i` (Cyrillic *postavkah* and *hash* typed on a Latin keyboard) produced a single literal primary variant and no fallback, so the intended reading was never sent and the literal failed to parse. Repaired by [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md). |
| Russian lexical calibration, OCR recovery recall unmeasured | `AUD-review-and-deepen-russian-lexical-calibration-3`. Reconciled, no change here; the measurement needs archive queries. Carried forward as nonblocking note 7 below. |
| Versioned scheme, composite primary keys | `AUD-establish-versioned-udc-derived-scheme-1`. Resolved. Confirmed latent, not live: every canonical ODCS contract declares exactly one primary-key column today. `RuleCatalog.primary_key` already carries the ordered key, so [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md) refuses a composite one at rule compilation rather than emitting per-column uniqueness. |

Blocking findings, all repaired by
[0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md):

| Finding | Evidence, invariant and consumers |
| --- | --- |
| `AUD-review-retrieval-and-classification-boundaries-1` | Blocking, resolved. `CaptionClassifier._file_features` located each matched term with `text.casefold().find(token)`, so a published evidence span was the first *substring* occurrence in a casefolded copy. Measured on the search view `relearning: machine relearning artificial intelligence and data science methods. machine learning`: term `learning` was published at `[2, 10)`, inside `relearning`, not at the standalone occurrence `[89, 97)`. A fold that changes length shifts every later span independently, and no row declared which artifact its offsets addressed. Invariant: published evidence addresses a real occurrence of its term in a named artifact. Consumers: the provided-archive classification proof's evidence gate, the human operating-point decision, and archive reorganization review. Repaired and regressed by [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md). |
| `AUD-review-retrieval-and-classification-boundaries-2` | Blocking, resolved. The operating-point packet carried class counts, thresholds and samples but not the upstream inventory, extraction and normalization manifests and checksums, nor the physical/virtual accounting, so the human decision could not say which corpus generation or which denominators produced the distribution it was asked to approve. A file classified from partially read text was also invisible. Invariant: a decision packet names the exact inputs behind every number it shows. Consumer: `approve-classification-operating-point`. Repaired and regressed by [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md). |
| `AUD-review-retrieval-and-classification-boundaries-3` | Blocking, resolved. `LexicalTarget.tokenizer_fingerprint` defaulted to the running code's `TOKENIZER_FINGERPRINT` and was never read from the registry, while `ctl.projections.input_fingerprint` bound only kind, version and row checksum. Every search result and every run record therefore published the current code's tokenizer identity as a property of the active index; editing `TEXT_FIELDS` left an index built by the old profile searchable and reported as current. Same class as `AUD-review-corpus-and-control-integrity-3`: an inspection field must describe the artifact it names. Consumers: every lexical query, the retained retrieval proof evidence, and any later relevance claim. Repaired and regressed by [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md). |

Nonblocking notes, one owner each:

| Note | Finding, next check and owner |
| --- | --- |
| `AUD-review-retrieval-and-classification-boundaries-4` | The `identifiers` literal field is fed `c.chunk_id` by `proj_lexical_rows.sql`, so literal lookup resolves chunk and document ids only. The specification's [search and vector projections](../../design/spec.md#search-and-vector-projections) says this field supports identifiers, part numbers and model names; none of those reach it, and text-borne codes are reachable only through the Russian-stemmed `body`. [Record 0070](0070-lexical-build-paradedb-lexical-load-and-query-path.md) documents the limitation but no task owned it. Next check: emit technical tokens and identifier codes from the Russian lane, then populate the projection column from them and re-measure identifier exactness. Owner: [build-russian-language-morphology-and-terminology-lane](../plan.md#build-russian-language-morphology-and-terminology-lane). Disposition: open, nonblocking. |
| `AUD-review-retrieval-and-classification-boundaries-5` | Carried forward from `AUD-build-paradedb-lexical-2`. Narrowing the executor seam is unsound, so the cost stands: an edit under `pipeline/dag` invalidates every stage's `code_fingerprint` and forced a 46-minute re-extraction on an unchanged archive. Next check: measure the rebuild cost of a late-stage edit at representative scale and decide whether an explicit operator-confirmed reuse override is warranted. Owner: [test-failure-and-capacity-boundaries](../plan.md#test-failure-and-capacity-boundaries). Disposition: open, nonblocking. |
| `AUD-review-retrieval-and-classification-boundaries-6` | Carried forward from `AUD-review-and-deepen-russian-lexical-calibration-1`. Transliteration turned English no-answer words into unrelated Russian hits in 12 of 12 final no-answer cases in both arms. Next check: measure no-answer false positives on archive queries and decide whether an English lexicon or a minimum-length rule is justified for the transliteration variants. Owner: [build-russian-language-morphology-and-terminology-lane](../plan.md#build-russian-language-morphology-and-terminology-lane). Disposition: open, nonblocking. |
| `AUD-review-retrieval-and-classification-boundaries-7` | Carried forward from `AUD-review-and-deepen-russian-lexical-calibration-3`. OCR recovery is a zero-hit fuzzy fallback, so recall on OCR-damaged archive text whose correct spelling also occurs is unmeasured. Next check: measure it on archive queries against the restored projection. Owner: [build-russian-language-morphology-and-terminology-lane](../plan.md#build-russian-language-morphology-and-terminology-lane). Disposition: open, nonblocking. |
| `AUD-review-retrieval-and-classification-boundaries-8` | `ClassificationStage._scheme_snapshot` raises `classification scheme snapshot is stale or damaged` and discards the findings `check_snapshot` returned, so an operator whose taxonomy moved under an existing run id learns neither which fingerprint changed nor how to recover. Next check: on the provided-archive run, confirm the message names the differing fingerprint and the rebuild command. Owner: [prove-archive-classification-on-provided-archive](../plan.md#prove-archive-classification-on-provided-archive). Disposition: open, nonblocking. |
| `AUD-review-retrieval-and-classification-boundaries-9` | `evidence_json` is a free-form string in the `file-classifications` contract, so the `space`/`source`/`start`/`end`/`term` shape that [0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md) introduced is a convention rather than a validated declaration, and a `normalized-search` span still requires a document-id to normalized-document-id join to reach the file it addresses. Next check: on the provided-archive run, resolve a sample of published spans end to end and decide whether the shape belongs in an additive contract revision. Owner: [prove-archive-classification-on-provided-archive](../plan.md#prove-archive-classification-on-provided-archive). Disposition: open, nonblocking. |

Refactor verdict: **refactor needed**, bounded to the evidence anchoring, the review-packet
identities, the projection engine-profile binding, the projection store selection, the wrong-layout
query path and the composite-key guard, and implemented by accepted repair
[0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md). Splitting
`retrieval/lexical.py` into `lexical_stages.py` was required by the 250-line limit the staged
execution crossed. No broader rewrite is warranted: the classifier's scoring, thresholds and
multilingual caption handling, the taxonomy and its staleness checks, the inventory/occurrence
identity scheme, the lexical load, retraction and locking, the query profiles' declared settings,
and the evidence catalog's ambiguity handling need no change, and no model promotion, contract
change or dependency change follows from this round.

Checkpoint verdict: **proceed-with-nonblocking-notes** for
`prove-archive-classification-on-provided-archive`, now that repair
[0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md) has passed.
The six nonblocking notes above each have one owner and none of them blocks that proof.

## Close or resume

Passed: every acceptance gate above, `make ci` and the prerequisite repair. Not run: `make
test-heavy` and `make test-archive`, because this host's database container is restarting on an
empty root-owned `PGDATA_DIR`; that is host state, not a code defect, and it must be restored
before the next store-backed run. Next action: `prove-archive-classification-on-provided-archive`,
which is `RUN NEEDED` and does not require the store (classification publishes to the lake).

Plan updates: both `repair-retrieval-and-classification-identity-and-evidence` and
`review-retrieval-and-classification-boundaries` are removed and replaced by links to
[0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md) and this
record in `prove-archive-classification-on-provided-archive`; that task, plus
`build-russian-language-morphology-and-terminology-lane`, `test-failure-and-capacity-boundaries` and
`publish-provided-archive-end-to-end-proof`, gain the audit inputs routed above. Plan counts before
57 (agent lane 47), after 55 (agent lane 45). Capabilities changed: none added or shipped;
`archive-classification`, `lexical-retrieval` and `canonical-store` now emit identities that
describe the artifacts they name. Current-state pages updated by the repair are listed in
[0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md). No human
decision is ready from this record: `approve-classification-operating-point`
still waits on the provided-archive proof.
