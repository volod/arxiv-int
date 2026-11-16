# Russian Lexical Calibration Second Opinion

## Task and scope

- Id / capability / checkpoint: `review-and-deepen-russian-lexical-calibration` /
  `lexical-retrieval` / `review-retrieval-and-classification-boundaries`
- State: accepted; every required gate below passed.
- Source: `docs/impl/plan.md`, section "Lexical retrieval -- `lexical-retrieval`", at worktree
  revision `f4ae6c6` with a clean tree; `make plan-status` reported 60 tasks (50 agent, 10 human)
  and this task as the next agent task.
- Accepted task:

```markdown
#### review-and-deepen-russian-lexical-calibration

Take an independent second opinion on the accepted Russian lexical calibration, then implement and
rerun a higher-effort comparison with stronger held-out and negative evidence.

- Serves: `lexical-retrieval` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: [Russian tokenization and BM25 calibration](records/0071-lexical-calibrate-russian-tokenization-and-bm25.md).
- User-visible outcome: The selected Russian query/index profile survives an independent challenge
with adequately powered inflection, ranking, collision and false-positive evidence, or is replaced by
a better measured profile.
- Scope boundary: Preserve the accepted run and source text; do not tune on its final items, promote
from synthetic recall alone, or change the profile without a fresh immutable adopt/retain/inconclusive
decision. Keep the provided-archive proof separate.
- Data and artifact paths: `src/arxiv_int/resources/configs/retrieval/`, retrieval calibration code
and tests, `$RUNS_DIR/<run-id>/evaluation/lexical-second-opinion/`, and
`docs/impl/current/lexical-retrieval.md`.
- Execution path: Start from a fresh second-opinion review of record 0071, its configuration, case
ledger and implementation, using a higher-reasoning reviewer/agent when available. Freeze distinct
development and untouched final expansions before running them. Add enough inflectional pairs for the
paired gate, hard irrelevant and alias-collision negatives, multi-term ranking, identifier near misses,
mixed-script false positives, and repeated latency/build samples. Factor tokenizer, morphology,
stopwords and query transformations independently; compare precision as well as recall/MRR/intactness;
replay on the pinned ParadeDB version and report sensitivity to seeds and query order.
- Acceptance gates: The second-opinion packet records findings and dispositions; final items and
promotion thresholds were frozen before execution; positive and negative cohorts have sufficient
decided pairs for the declared confidence; one profile receives `adopt`, `retain baseline`, or
`inconclusive` from paired quality evidence without a mandatory-gate regression. Costs and every input
fingerprint cite an immutable verified run. Any selected tokenizer change names and proves required
reindex work; a query-only decision proves whether existing indexes remain valid.
- Documentation target: `docs/impl/current/lexical-retrieval.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.
```

- Amendments: none.

## Summary

This section restates the decision for readers; the evidence sections below are authoritative.

### Outcome

The accepted profile did not survive the challenge, and a better measured profile replaced it. On
the frozen final split, `russian-guarded-v2` beat the previously accepted `russian-safe-v1`, both
served on the unchanged `unicode-russian-v1` index.

| Measure | `russian-safe-v1` | `russian-guarded-v2` |
| --- | --- | --- |
| nDCG@10, 90 quality cases | 0.680 | 0.959 |
| Returned precision@5, 54 precision cases | 0.431 | 0.464 |
| p95 latency | 4.88 ms | 5.15 ms |

- Quality: 27 wins and 0 losses (95% interval +0.187 to +0.375, sign-test p=1.5e-8), above the
  preregistered minimum of 20 decided pairs.
- Precision: 4 wins and 0 losses (interval +0.005 to +0.069), so no precision was given up.
- Every mandatory gate passed. All five bootstrap seeds agreed, and ranked results were identical
  across 30 repetitions in seeded random query orders.
- The change is query-only. The index tokenizer fingerprint is unchanged, no reindex is needed,
  and existing lexical projections stay valid. The production default now points at
  `russian-guarded-v2`.

### Why the old decision fell

The independent reviewer agent and this session's probes on the pinned engine agreed on the
following.

- Leakage: every `legacy-v1` alias key was one of record 0071's final queries, and one alias mapped
  a correct word to that fixture's own OCR misspelling. Three of the six wins needed a dictionary
  entry. Without the OCR alias the result was 5-0, p=0.0625, which is not significant.
- Precision was never measured. Each query had one relevant chunk and no negatives, and the extra
  variants were OR-ed with the original, so the candidate could only add matches. A multi-word
  alias expansion already matched an unrelated chunk through one common word.
- Power was at the minimum: 6-0 was the only passing outcome, categories held one or two items, and
  the identifier cases could never differ.
- Recall, MRR, span coverage and intactness were one reading, because every span was a whole chunk
  and every hit ranked first.
- Cost readings were single samples on 12 rows; the p95 was the maximum of 12 samples and index
  sizes were identical page allocations.
- Factors were confounded: five transforms were bundled, stemming and stopwords toggled together,
  and no case was sensitive to ICU segmentation.
- Four real bugs:
  - NFC normalization never reached the primary query clause;
  - homoglyph repair translated the whole query, in one direction, lowercase only;
  - the transliteration tables were wrong (initial e never became ae, y-endings, unmapped x/w/q);
  - variants rewrote query syntax, so field prefixes failed and exclusions were defeated.
- Aliases expanded only when the whole query equalled a key.
- The pinned stemmer misses fleeting-vowel inflection, conflates homonymous stems, and already folds
  yo to e, which made the v1 e/yo alias redundant.

### How the new comparison was kept honest

- Test sets: separate development and final sets (122 cases each, 197 and 199 judged chunks) were
  authored and checksummed before any candidate mechanism existed. The general technical
  abbreviation dictionary was written before either set. A static audit with the engine
  tokenizer, which scored no profile, closed judgment gaps before freezing.
- Cohorts: hard negatives, alias collisions, stemming collisions, English/transliteration
  collisions, no-answer queries, identifier near-misses, query-syntax probes with forbidden hits,
  multi-term ranking, numeric formats, and 20 inflection pairs per split (8 fleeting-vowel).
- Scale: 70,000 deterministic, vocabulary-disjoint filler chunks brought the corpus to archive
  scale without ever becoming relevant hits.
- Factors: a 2x2x2 tokenizer x stemmer x stopwords index factorial, each accepted transform alone,
  and leave-one-out ablations of every candidate component.
- Metrics: chunk-level nDCG, recall, MRR, returned precision, no-answer false positives,
  hard-negative, forbidden and unjudged hits, identifier exactness, and intactness from real
  offsets.
- Thresholds, cohort minimums and the decision rule were frozen in `protocol.json` before any
  execution. The only pre-execution change added an absolute latency-increase alternative.
- Tuning happened only on the development split (three development runs; one mechanism change,
  a conjunctive long-word fuzzy stage). The last development run on the final code reproduced the
  previous run's ranked hits exactly.
- The final stage refuses to run unless a preregistration bundle in the same run recorded the exact
  final split, protocol, arms, review packet, query policy and code fingerprints first. It ran
  once, with no overrides.
- Replay: every run used the pinned ParadeDB 0.25.6, and the 0071 calibration replay still
  reproduces its original verdict.

### Limitations and open notes

- Both profiles return an unrelated Russian row for all 12 English no-answer words, because
  transliteration reads them as Russian (`AUD-review-and-deepen-russian-lexical-calibration-1`).
- Wrong-layout typing on bracket, semicolon or quote keys still produces a query-syntax error
  (`AUD-review-and-deepen-russian-lexical-calibration-2`).
- OCR recovery runs only when a query otherwise finds nothing
  (`AUD-review-and-deepen-russian-lexical-calibration-3`).
- These are synthetic cases, not proof of relevance on the provided archive; that proof is
  [record 0073](0073-lexical-prove-lexical-retrieval-on-provided-archive.md).
- The CUDA device played no role: BM25 calibration is CPU and database work.

## Freeze ledger

Recorded before any development or final execution of the second-opinion harness.

| Input | SHA-256 | Frozen |
| --- | --- | --- |
| `second-opinion/development.json` (122 cases, 197 judged chunks) | `17edf576c743a53446a1fd3f982b1aa87c3988c9162f60858310943e2bd3cdb2` | 2026-09-10T21:46:52Z |
| `second-opinion/final.json` (122 cases, 199 judged chunks) | `222ba2291d2429910bf2cfa9677847ed285af8089043f98fa924942330602cb6` | 2026-09-10T21:46:52Z |
| `second-opinion/filler.json` (394 audited words) | `bed36955f350802d0664d91fe298e578858710aff852d88b207452fdeb1fe9ac` | 2026-09-10T21:46:52Z |
| `second-opinion/protocol.json` (cohorts, minimums, gates, thresholds) | `15d3423b5007d2fc83d1b82883e755c362c907e53baa6448df5a1efec94c977e` | before first execution |
| `second-opinion/review.json` (findings and dispositions) | `6aa0f778dc468aeb9226f9723218c1f8eee159219d2a5a2e9030148b437591f2` | before first execution |

The technical abbreviation dictionary (`technical-v2`) was written before either split was
authored. Both splits were authored together, before any candidate mechanism was implemented, and
audited statically with the pinned engine tokenizer for judgment gaps; no profile was scored during
authoring. The first protocol draft (`ebad0f43...`) gained only an absolute latency-increase
alternative (`latency_p95_increase_ms_max`) before any execution. `arms.json` may change during
development; the preregistration bundle binds its final form.

## Second-opinion review

An independent read-only reviewer agent examined record 0071, its configuration, case ledger and
implementation. This session repeated the review with rollback-only probes on the pinned
ParadeDB 0.25.6 engine. The packet
`src/arxiv_int/resources/configs/retrieval/second-opinion/review.json` records nineteen findings,
each with severity, evidence and disposition, plus the recommendations that were not adopted and
why. Blocking findings:

- F1: every legacy alias key was a final 0071 query. One alias mapped the correct word to the
  fixture's own OCR misspelling. Without that alias the accepted comparison is 5-0, p=0.0625,
  `inconclusive`.
- F3: precision was never measured, and OR-ed variants could only add matches.

Major findings:

- Power sat at the minimum, and the identifier cases were structurally tied.
- Recall, MRR, coverage and intactness were one reading (F5).
- Cost readings were single samples on 12 rows.
- Factors were confounded.
- NFC never reached the primary clause (F8).
- Homoglyph repair ran on the whole query in one direction.
- The transliteration tables were wrong.
- Variants rewrote query syntax.
- Aliases expanded only whole queries.
- The stemmer misses fleeting-vowel inflection. Engine probes showed that the Russian stemmer
  folds yo to e, conflates homonymous stems, and stems some expansion words differently in
  nominative and oblique forms.

## Implementation

- `retrieval.query_transforms` and `retrieval.query_aliases` hold pure, bounded transforms.
  - The `*_v1` functions keep `russian-safe-v1` byte-identical.
  - The candidate transforms:
    - per-token homoglyph repair toward the majority script, including uppercase-only lookalikes
      and cross-script identifier codes;
    - positional transliteration (word-initial e/ae, glides, x/w/q/c, apostrophe) that drops
      any output with residual Latin;
    - a fleeting-vowel genitive probe limited to the -ets/-ok/-ek/-en'/-el/-ol endings;
    - token-level alias substitution with phrase binding and reverse expansion (two-letter keys
      only in upper case);
    - query-syntax detection.
- `retrieval.query_normalization` loads schema v2 of `query-normalization.json`:
  - named alias sets: `legacy-v1`, unchanged, and the general `technical-v2` list of 58
    abbreviations written before any case;
  - declared profiles;
  - a `QueryPlan` with primary variants, mechanical variants that run only when the primary
    stage matches nothing, and conjunctive fuzzy texts of words with at least 5 characters.
  - `russian-guarded-v2` is the candidate. The ablation profiles each remove one component, and
    `aliases-v1`/`homoglyphs-v1`/`layout-v1`/`translit-v1` isolate the accepted transforms.
- `retrieval.lexical` runs the plan stages in order and reports `queryStage`. It binds the NFC
  base as the primary clause (F8 fix), and it skips the count query when the first page already
  holds every match. `lexical_model` now holds the request, hit and result types.
  `adapters.lexical_search.fuzzy_query` binds bounded-distance conjunctive `paradedb.match`
  clauses.
- `retrieval.second_opinion` is the new harness.
  - It verifies the frozen splits and filler by SHA-256 against `protocol.json`, and refuses
    shared cases or queries between splits and final cohorts below the preregistered minimums.
  - It loads 197/199 judged chunks plus 70,000 deterministic, vocabulary-disjoint filler chunks
    into one shared table, then copies identical rows for a 2x2x2 tokenizer x stemmer x
    stopwords index factorial.
  - It rebuilds every index in seeded random orders, and runs every arm/case pair repeatedly in a
    fresh seeded order each repetition, inside a rolled-back transaction.
  - Scoring is chunk-level: nDCG@10, recall, MRR, returned precision@5, no-answer false
    positives, hard-negative, forbidden and unjudged hits, identifier exactness, and intactness
    computed from real offsets.
  - Decisions use preregistered mandatory gates and paired verdicts, recomputed for five
    bootstrap seeds, with a repetition-stability override.
  - `development` accepts cost overrides. `preregister` publishes a bundle that binds the final
    split, protocol, arms, review packet, query policy and code. `final` refuses to run unless
    that bundle verifies and every fingerprint still matches, and refuses any override.
  - `arxiv-int search second-opinion` and `make lexical-second-opinion` expose the stages.

## Development evidence

Development runs used 70,000 filler rows, one build repetition and three query repetitions. Only
the development split was executed.

| Run | Change under test | Development verdict |
| --- | --- | --- |
| `run-ba14b80787e04fafbfc3e1543d5735d0` (manifest `5fd71994...`) | first candidate | `inconclusive`: quality 26/0/65 vs accepted, precision 4/3/47 with lower bound -0.099 |
| `run-51570961196b4353b8ca9dc074762cab` (manifest `3ca908e1...`) | fuzzy stage conjunctive over long words of every primary variant | `adopt`: quality 28/0/63, lower bound +0.191; precision 4/0/50, lower bound +0.006; all five seeds agree |
| `run-b6a70bdaa8084154afb802fe4a060775` (manifest `ddaccff5...`) | complexity-only refactors, final code | `adopt`; ranked hits, stages and errors identical to the previous run for all 2,806 arm/case pairs |

Diagnosis between the two runs:

- The stemmer's inconsistent nominative/oblique stems (for example battery and heat-power-plant
  expansions) defeated exact alias phrases.
- Fuzzy matching of 2-3 letter abbreviations returned unrelated rows.

No split, threshold or dictionary entry changed. Development leave-one-out showed that every
retained component was non-negative:

- aliases: +7 quality wins;
- phrase binding: +5 precision wins;
- fallback gating: +3/+3;
- homoglyphs: +2;
- fleeting vowels: +1;
- fuzzy: +10;
- syntax guard: removes one error.

Other development findings:

- The stemmer raises quality (18/0) but costs precision (0/19).
- ICU never changed a ranked hit beyond one tie-level loss.
- Transliteration in both profiles returned an unrelated Russian row for all 11 English
  no-answer queries.

## Preregistration

- Code final before binding: `make format` was clean and `make ci` passed with 1,322 tests passed
  and 54 heavy tests deselected. The declared live checks passed:
  - the harness check `test_live_second_opinion.py` (`-m heavy` with
    `ARXIV_INT_RUN_LEXICAL_SECOND_OPINION=1`);
  - the production path `test_live_lexical.py`;
  - the 0071 replay `test_live_calibration.py`, all on the pinned disposable
    `arxiv-int/postgres:17-0.25.6-age1.7.0`.
- Bundle: `$RUNS_DIR/run-204c1ec6c5c846fd8546a0781a7b1789/evaluation/lexical-second-opinion/preregistration/`.
  Published 2026-09-10T22:22:00Z; manifest `6bf8669688b02725745da844371dcbc667104db164073c9a3280d10838e4ab82`,
  verified in place. It holds the final case list and copies of `arms.json`, `protocol.json` and
  `review.json`.
- Bound fingerprints:

  | Input | Fingerprint |
  | --- | --- |
  | final split | `222ba229...` |
  | protocol | `15d3423b...` |
  | arms | `caba8ade...` |
  | filler | `bed36955...` |
  | review packet | `6aa0f778...` |
  | query policy | `9a37dfc6...` |
  | code | `67b36809...` |
  | runtime tokenizer | `3b277b23...` |

  The last development run cites the same code, policy and arms fingerprints.
- The final stage started immediately afterwards on the same run. It verified this bundle and ran
  with no overrides.

## Acceptance evidence

Final bundle: `$RUNS_DIR/run-204c1ec6c5c846fd8546a0781a7b1789/evaluation/lexical-second-opinion/final/`.
Its manifest is `e691b9b8db5b7063171be9cc84c0c904c176cc2850305adc8f9b471489835872`, verified in
place. It holds `scores.jsonl` (2,806 arm/case rows), `report.json` and copies of the frozen
inputs. The run started 2026-09-10T22:22:00Z and finished 22:27:30Z, with no overrides.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Second-opinion packet with findings and dispositions | `second-opinion/review.json` (`6aa0f778...`), bound by the preregistration and final manifests; this record's review section | pass; 19 findings, 2 blocking, each with a disposition; unadopted recommendations listed with reasons |
| Final items and thresholds frozen before execution | freeze ledger above; `tests/retrieval/test_second_opinion_inputs.py`; preregistration manifest `6bf86696...` published before the final stage; final manifest cites it as `preregistration_manifest` | pass; development and final split fingerprints unchanged since authoring; final executed once; development leakage and memorized-alias gates pass |
| Sufficient decided pairs for 95% confidence | final report: quality endpoint 27 decided pairs (minimum 20) over 90 cases; precision endpoint 54 cases (minimum 40), including 12 no-answer, 12 identifier checks and 8 syntax probes | pass; quality 27/0; precision 4/0, non-inferior by the preregistered rule; 20 inflection pairs per split, 8 of them fleeting-vowel |
| One paired verdict without a mandatory-gate regression | final manifest verdict `adopt`; `report.json` decision | pass; `russian-guarded-v2` adopted: nDCG@10 0.680 to 0.959, interval +0.187 to +0.375, p=1.5e-8; all gates true; all 5 seeds `adopt`; hits stable across 30 randomized repetitions |
| Precision alongside recall, MRR and intactness | `report.json` arms | pass; guarded recall 0.967, MRR 0.956, intactness 0.967 (computed from real offsets; invariant to lexical profile), returned precision 0.464 versus 0.431 |
| Factor isolation | 2x2x2 index factorial, single-transform v1 arms, candidate leave-one-out | pass; stemming +0.204 nDCG and -0.105 precision; stopwords and ICU no significant effect; v1 transliteration -0.25 precision |
| Costs and input fingerprints cite an immutable verified run | same final manifest; inputs: code `67b36809...`, query policy `9a37dfc6...`, protocol `15d3423b...`, arms `caba8ade...`, final split `222ba229...`, filler `bed36955...`, runtime tokenizer `3b277b23...` | pass; 5 builds per profile (medians 0.38-1.18 s; indexes 17.3-21.4 MB over 88-92 MB tables); 3,660 latency samples per arm; guarded p50/p95 2.67/5.15 ms |
| Replay on the pinned ParadeDB version | live engine 0.25.6 recorded in every manifest; `test_live_calibration.py` replay of 0071; `test_live_lexical.py` | pass; all on the pinned image |
| Reindex decision | final `reindex_required=false`; `tests/retrieval/test_second_opinion_inputs.py::test_production_index_profile_needs_no_reindex` | pass; query-only adoption; the production tokenizer fingerprint is unchanged, so existing projections remain valid; ICU arms would require a rebuild |
| Deterministic and required CI | `make format`; `make ci` on the finished tree; `make lint-md`; `make lint-spec-plan` | pass; 1,322 passed, 54 heavy deselected; Markdown, doc links and plan integrity clean |

## Audit handoff

| Note | Observation |
| --- | --- |
| `AUD-review-and-deepen-russian-lexical-calibration-1` | Nonblocking. Transliteration in both the accepted and the adopted profile turns English no-answer words into unrelated Russian hits (12 of 12 final no-answer cases); the guarded fallback only removes collisions when the English word itself matches. Evidence: final `report.json`, `no_answer_false_positives=12` for both arms. Next check: whether an English lexicon or length rule is justified on archive queries. Owner: [checkpoint 0080](0080-archive-cls-review-retrieval-and-classification-boundaries.md). Disposition: resolved as routed; the measurement it needs continues as `AUD-review-retrieval-and-classification-boundaries-3`. |
| `AUD-review-and-deepen-russian-lexical-calibration-2` | Nonblocking. Wrong-layout text typed on bracket, semicolon or quote keys becomes query syntax and fails in non-lenient mode for every profile (review finding F19). Next check: sanitize or lenient-parse mechanical variants without weakening reported syntax errors. Owner: [checkpoint 0080](0080-archive-cls-review-retrieval-and-classification-boundaries.md). Disposition: resolved by [repair 0081](0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md); layout punctuation keeps its Cyrillic reading as a fallback and a refused stage no longer hides a later one or its own message. |
| `AUD-review-and-deepen-russian-lexical-calibration-3` | Nonblocking. OCR recovery is a zero-hit fuzzy fallback, so recall on OCR-damaged archive text whose correct spelling also occurs is unmeasured. Next check: measure it on provided-archive queries. Owner: [checkpoint 0080](0080-archive-cls-review-retrieval-and-classification-boundaries.md). Disposition: resolved as routed; the measurement continues as `AUD-review-retrieval-and-classification-boundaries-4`. |

## Close or resume

- **Gates:** every acceptance gate passed. `russian-guarded-v2` replaces `russian-safe-v1` as the
  production query profile; the default is flipped in `query-normalization.json` and in
  `SELECTED_QUERY_PROFILE`. The adoption is query-only, so no reindex is needed and existing
  lexical projections remain valid.
- **Replay-only material:** the accepted profile and its `legacy-v1` aliases remain declared only
  for replaying record 0071. Record 0071 now points to this record as its supersession.
- **Post-decision live checks:** after the flip, `test_live_lexical.py` (the production path with
  the new default) and `test_live_second_opinion.py` passed on the pinned disposable store.
- **Plan:**
  - The task was removed from the forward plan.
  - Its three dependents
    ([0073](0073-lexical-prove-lexical-retrieval-on-provided-archive.md),
    `review-retrieval-and-classification-boundaries` and
    `build-search-graph-and-report-interfaces`) now link this record.
  - The checkpoint lists the three audit notes as inputs.
  - Counts went from 60 tasks (50 agent, 10 human) to 59 (49 agent, 10 human); `RUN NEEDED` fell
    from 32 to 31.
  - The next eligible agent task is `establish-versioned-udc-derived-scheme`.
- **Capability change:** `lexical-retrieval` now serves the guarded staged query profile and ships
  the frozen second-opinion harness (`make lexical-second-opinion`).
- **Updated documents:**
  - [lexical retrieval](../current/lexical-retrieval.md);
  - `docs/impl/current.md`;
  - `docs/guide/commands.md`;
  - the record index.
- **No human review handoff applies.** The provided-archive proof is
  [record 0073](0073-lexical-prove-lexical-retrieval-on-provided-archive.md).
