# Task Record

## Task and scope

- Id / capability / checkpoint: `repair-retrieval-and-classification-identity-and-evidence` /
  `archive-classification` / `review-retrieval-and-classification-boundaries`
- State: accepted
- Source: `docs/impl/plan.md#repair-retrieval-and-classification-identity-and-evidence`, planned by
  checkpoint [0080](0080-archive-cls-review-retrieval-and-classification-boundaries.md) at `d5a4901`;
  dirty scope is that checkpoint's record, the record index and the new plan task.
- Accepted task:

```markdown
#### repair-retrieval-and-classification-identity-and-evidence

Repair emitted identities and evidence that do not describe the artifacts they name, and the
projection commands that cannot reach the configured store.

- Serves: `archive-classification` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Hierarchical file classification](records/0079-archive-cls-implement-hierarchical-file-classification.md);
[ParadeDB lexical load and query path](records/0070-lexical-build-paradedb-lexical-load-and-query-path.md);
[Russian lexical calibration second opinion](records/0072-lexical-review-and-deepen-russian-lexical-calibration.md);
[Versioned classification scheme](records/0076-archive-cls-establish-versioned-udc-derived-scheme.md).
- User-visible outcome:
A decisive-evidence span addresses a real token occurrence in a named coordinate space, an
operating-point packet carries the corpus identities and denominators its counts came from, a
search result reports the tokenizer the active index was built with, and the projection commands
act on the store the pipeline loads.
- Scope boundary:
Repair the six findings recorded by the checkpoint only. No new classifier, scoring change,
taxonomy change, reindex, tokenizer change or projection schema migration; no new query profile.
Published class assignments, thresholds and scheme content stay as accepted.
- Data and artifact paths: `src/arxiv_int/classification/`, `src/arxiv_int/retrieval/`,
`src/arxiv_int/stores/projections/`, `src/arxiv_int/data_quality/rules/`, mirrored tests, and
`$RUNS_DIR/<run-id>/review/classification/`.
- Execution path:
Anchor evidence on the token occurrence that produced the feature and declare its coordinate
space; add upstream identities, accounting denominators and text-budget truncation to the
operating-point packet; bind the engine profile fingerprint into the projection input fingerprint
and verify it when the query path resolves the active target; resolve the projection commands
through the canonical store selection while keeping an unselectable store `not-run`; keep a
wrong-layout reading reachable when the syntax guard holds the literal query; refuse a composite
primary key where per-column uniqueness rules would be wrong.
- Acceptance gates:
Every published evidence span is a token-boundary occurrence of its term in the artifact its
declared space names; the packet resolves to the exact upstream manifests and checksums and its
denominators reconcile with the mapping manifest; a projection built under a different engine
profile is refused instead of reported as current; `projections-status`/`-cleanup`/`-build` reach
the configured service without an exported URL and still report `not-run` when no store exists;
a wrong-layout query whose literal form is unparseable returns the intended hits and a genuinely
broken query still reports its syntax error; a composite-key contract is refused with a named
message. Failing regressions precede each fix. Run `make ci`; coverage is diagnostic.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.
```

- Amendments: none.

## Implementation

Six bounded repairs, each preceded by a failing regression. No classifier, scoring, threshold,
taxonomy, tokenizer or projection-schema change; no reindex and no migration.

1. **Evidence spans.** `classification/text_features.py` gains `word_spans`, which returns each
   normalized token with the span of the characters that produced it; `words` now derives from it.
   `features.CaptionClassifier._file_features` keys positions from those spans instead of
   `text.casefold().find(token)`, and every source carries a coordinate space
   (`relative-path`, `title`, `normalized-search`) that `_evidence` writes into each item.
   Two defects are removed: the old search found the first *substring* occurrence, so a matched
   term was reported inside a longer unrelated word, and the offsets addressed a casefolded copy,
   so a fold that changes length (sharp s to `ss`) shifted every later span. Measured before the
   fix on the search view `relearning: machine relearning artificial intelligence and data science
   methods. machine learning`: term `learning` was published at `[2, 10)`, inside `relearning`;
   it is now `[89, 97)`, the standalone occurrence.

2. **Text-budget denominator.** `classification/source.py::_read_documents` now returns the
   documents the 120,000-character file-level budget cut short or skipped instead of dropping
   them silently; `PhysicalFile.truncated_document_ids` carries them, the row sidecar records
   them, and `publish.finish` reports `accounting.text_budget_truncated_rows`.

3. **Review packet identities.** `classification/review.py` adds `accounting`, `scheme` and
   `upstream` to the operating-point packet, so the human decision sees which inventory,
   extraction and normalization manifests and checksums produced the counts, and the
   physical/virtual/truncated denominators behind them, not only the class distribution.

4. **Projection engine profile.** New `stores/projections/profiles.py` declares one profile
   identity per kind (lexical is the existing `TOKENIZER_FINGERPRINT`) and
   `projection_input_fingerprint`, which `builder.py` now writes into
   `ctl.projections.input_fingerprint`. `retrieval/projection.active_target` selects that column
   and recomputes the expected value, refusing a projection built under a different profile.
   Before this, `LexicalTarget.tokenizer_fingerprint` defaulted to the running code's constant and
   every search result published it as a property of the active index, which the code could not
   substantiate; editing `TEXT_FIELDS` left an existing active index searchable and reported as
   current. The registry column already existed, so no migration was needed.

5. **Projection store selection.** `stores/postgres/selection.optional_store_url` resolves an
   explicit URL, then the configured loopback service, and returns `None` only when no store can
   be selected at all. `stores/projections/commands.py` and `lifecycle.py` use it in place of
   `resolve_database_url`. Decision recorded for `AUD-build-paradedb-lexical-1`: the service
   fallback *is* specified behavior for these commands, because they act on the same canonical
   store `load-lexical` loads and `retrieval/commands.py` queries. `not-run` now means no store
   configuration exists, which is what a wheel or bare tree gives; two tests that asserted the old
   premise were rewritten to the decided behavior rather than deleted.

6. **Wrong-layout queries and composite keys.** `query_transforms.is_layout_artifact` recognizes a
   query whose only syntax is punctuation a Russian layout emits; `query_plan` then keeps the
   literal base as the sole primary variant and offers the mechanical readings as a fallback,
   marking the plan `literal_primary`. New `retrieval/lexical_stages.py` (split out of
   `lexical.py`, which crossed the 250-line limit) leaves that unparseable literal out of the
   fallback clause and keeps a refused stage from hiding a later one, re-raising the engine's own
   message when no stage matches. `data_quality/rules/_primary_key` refuses a composite primary
   key, since uniqueness is compiled per column and would otherwise require each key column to be
   unique on its own.

Compatibility: an already-built lexical projection has a three-part input fingerprint and is now
refused until rebuilt with `arxiv-int store projections-build --kind lexical --activate`. Published
`evidence_json` gains a `space` key and corrected offsets; earlier rows keep the old shape and
should not be compared across the change. Current-state pages updated:
[archive classification](../current/archive-classification.md),
[lexical retrieval](../current/lexical-retrieval.md),
[canonical store](../current/canonical-store.md) and
[contracts](../current/contracts.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Evidence spans are token-boundary occurrences in a named space | `tests/classification/test_classifier.py::test_evidence_spans_address_real_token_occurrences_in_a_named_space` | pass; failed before the fix on the `relearning`/`learning` case |
| A length-changing fold cannot move a span | `tests/classification/test_classifier.py::test_evidence_offsets_survive_a_length_changing_casefold` | pass; failed before the fix |
| Budget truncation is reported | `tests/classification/test_stage.py::test_text_budget_truncation_is_reported_not_silently_dropped` | pass; failed before the fix |
| Packet names the upstream chain and denominators | `tests/classification/test_stage.py::test_review_packet_names_the_upstream_chain_and_its_denominators` | pass; failed before the fix (`KeyError: 'upstream'`) |
| Engine profile is bound and verified | `tests/retrieval/test_projection_identity.py` (3 cases) | pass; failed before the fix (no `profiles` module) |
| Projection commands reach the configured service, and `not-run` survives | `tests/stores/projections/test_projection_units.py::test_projection_store_selection_falls_back_to_the_configured_service`, `::test_cli_projection_status_uses_the_configured_service`, `::test_cli_projection_status_not_run`, `::test_build_without_any_selectable_store_is_not_run` | pass |
| Wrong-layout reading stays reachable; deliberate syntax untouched | `tests/retrieval/test_query_plans.py::test_wrong_layout_punctuation_keeps_the_cyrillic_reading_reachable`, `::test_deliberate_query_syntax_gains_no_mechanical_fallback`, `::test_query_syntax_disables_every_variant_and_fallback` | pass; the first failed before the fix |
| A refused stage neither hides a later one nor its own error | `tests/retrieval/test_lexical_stages.py` (2 cases) | pass; both failed before the fix |
| Composite primary key refused | `tests/data_quality/rules/test_rules.py::test_a_composite_primary_key_is_refused_instead_of_compiled_per_column` | pass; failed before the fix |
| Required gate | `make ci` | pass; 1438 passed, 57 deselected, 262 s (baseline before this task: 1424 passed) |
| Format, lint, types, complexity, shell, docs, contracts, evolution, db, ontology, schemas | `make ci-checks` (inside `make ci`) | pass |
| Markdown and links | `make lint-md` | pass; 0 broken links |
| Diagnostic suite | `make quality` | pass; coverage 85 percent (diagnostic), package build clean |
| File-size soft limit | `make quality-report` | pass for changed files; `retrieval/lexical.py` 189 lines after the split, `lexical_stages.py` 133 |
| Live ParadeDB and provided-archive checks | `make test-heavy`, `make test-archive` | not-run; `arxiv-int-database-1` is in a restart loop on this host because `PGDATA_DIR` (`.../BPLA_RES/pgdata`) is empty and root-owned while the container runs as uid 1000. Host state, not a code change; no live projection exists to query. |

Fingerprints: classifier policy `taxonomy-caption-overlap-v1` 1.0.0 and scheme
`subjects-1c0d5213ec52` are unchanged by this task. The lexical tokenizer profile is unchanged; only
where its fingerprint is recorded and checked changed. Fixture evidence does not establish
real-archive quality or CUDA fit.

## Audit handoff

| Note | Observation |
| --- | --- |
| `AUD-repair-retrieval-and-classification-identity-and-evidence-1` | Nonblocking. `ClassificationStage._run` calls `classifier.classify(item)` twice for every file to assert reproducibility, so the whole archive is scored twice, and the manifest records `reproducibility.status` as `pass` for every row. `CaptionClassifier` holds no mutable state and `PhysicalFile` is frozen, so the check can only fire on interpreter-level nondeterminism. Impact: cost, not correctness, against the profile's `minimumThroughputFilesPerSecond` gate of 20.0. Next check: measure classify throughput on the provided archive and decide whether a bounded sample replaces the per-row double scoring. Owner: [prove-archive-classification-on-provided-archive](../plan.md#prove-archive-classification-on-provided-archive). Disposition: open. |
| `AUD-repair-retrieval-and-classification-identity-and-evidence-2` | Nonblocking. `classification/source.py` holds one in-memory entry per normalized document (`_normalized_documents`) and per extraction occurrence (`mapped`) before streaming inventory rows, so peak memory grows with document count rather than with the bounded batch. The 0068 archive run held 414 documents; the gate is 512 MiB. Next check: record classify peak memory on the provided archive against that gate. Owner: [prove-archive-classification-on-provided-archive](../plan.md#prove-archive-classification-on-provided-archive). Disposition: open. |
| `AUD-repair-retrieval-and-classification-identity-and-evidence-3` | Nonblocking. Rebuilding the lexical projection cannot be verified on this host: the database container restarts because `PGDATA_DIR` is empty and root-owned. The refusal path is covered deterministically, but no live projection proved that a rebuilt version's recomputed fingerprint matches. Next check: rebuild and query a live projection once the store is restored. Owner: [publish-provided-archive-end-to-end-proof](../plan.md#publish-provided-archive-end-to-end-proof). Disposition: open. |

Reviewed scope: the six repaired seams, their callers, and the tests that cover them. The
classifier's scoring, the taxonomy, the query profiles' declared settings and the projection
lifecycle's locking were read but deliberately left unchanged.

## Close or resume

All required gates passed except the live and archive runs, which the host's database state blocks
and which are not acceptance gates for this `CLEAR` task. Next action: close checkpoint
[0080](0080-archive-cls-review-retrieval-and-classification-boundaries.md), which named this repair
as its prerequisite. Plan counts before 57 agent-lane 47; after this record and 0080 close, 55 with
agent lane 45. Capabilities changed: none added; `archive-classification` and `lexical-retrieval`
emit identities that describe the artifacts they name, and `canonical-store` projection commands
reach the configured service. Record index updated; both plan tasks are removed by 0080's close and
replaced with links to these records.
