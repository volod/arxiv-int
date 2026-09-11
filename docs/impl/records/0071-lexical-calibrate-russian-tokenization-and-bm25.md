# Russian Tokenization and BM25 Calibration

## Task and scope

- Id / capability / checkpoint: `calibrate-russian-tokenization-and-bm25` /
  `lexical-retrieval` / `review-retrieval-and-classification-boundaries`
- State: accepted; every required gate below passed.
- Source: `docs/impl/plan.md`, section "Lexical retrieval -- `lexical-retrieval`", at the current
  worktree revision `8dabafd`; initial plan count is 60 tasks (50 agent, 10 human), with no
  pre-existing dirty scope.
- Accepted task:

```markdown
#### calibrate-russian-tokenization-and-bm25

Compare Unicode and ICU segmentation, Russian stemming/stopwords, exact identifier fields, aliases,
and query normalization on a held-out Russian query set.

- Serves: `lexical-retrieval` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: [ParadeDB lexical load and query path](records/0070-lexical-build-paradedb-lexical-load-and-query-path.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md).
- User-visible outcome: The default Russian lexical profile is backed by recall, MRR, evidence
intactness, latency, and index-size evidence rather than an English default.
- Scope boundary: Compare declared tokenizer/query profiles; do not tune on the final split or
silently rewrite source text.
- Data and artifact paths: `configs/retrieval/`, `eval.*`, `$RUNS_DIR/<run-id>/evaluation/lexical/`,
and `docs/impl/current/lexical-retrieval.md`.
- Execution path: Build comparable indexes on identical data; measure inflection, identifiers,
abbreviations, OCR noise, homoglyphs, e/yo variants, keyboard layout, transliteration, and
mixed-language cases; use paired bootstrap verdicts.
- Acceptance gates: One profile receives `adopt`, `retain baseline`, or `inconclusive`; final
metrics and costs cite immutable runs; profile changes name required reindex work.
- Documentation target: `docs/impl/current/lexical-retrieval.md`
- Review checkpoint: `review-retrieval-and-classification-boundaries`.
```

- Amendments: none.

## Implementation

The packaged ASCII JSON configuration freezes four candidates and 12 final queries covering every
required phenomenon. `unicode-russian-v1` is the existing baseline; `unicode-plain-v1` isolates
Russian stemming/stopwords; `unicode-russian-safe-v1` changes only query processing; and
`icu-russian-safe-v1` isolates ICU segmentation. The candidate and baseline, `k=5`, 95% confidence,
2,000 bootstrap resamples and seed 13 are declared before execution. The runner only scores the final
split and offers no parameter-tuning path.

`retrieval.query_normalization` applies NFC without changing stored text, then retains the original
query while adding at most five separately bound variants. The selected `russian-safe-v1` policy
supports a reviewed abbreviation/alias map, mixed-script homoglyph repair, wrong keyboard layout and
bounded Latin transliteration. The exact identifier path remains separate and literal. Search JSON
now reports both query profile and policy fingerprint. All ParadeDB query text remains a SQL bind;
only existing whitelisted identifiers are composed.

`retrieval.calibration` loads the frozen source-safe rows into one covering table per candidate,
creates all four ParadeDB indexes in a single database transaction, warms and scores every query,
measures build time, index/table bytes and p95, and rolls the transaction back. It reuses
`evaluate_retrieval()`, `paired_comparison()` and the immutable evaluation bundle publisher. The
bundle binds the frozen config, calibration code, query policy, production tokenizer and live
`pg_search` version; it registers checksums for the case ledger and profile/comparison report and
refuses replacement. `arxiv-int search calibrate --run-id ...` and `make calibrate-lexical` expose
the run.

The query-normalization candidate was adopted. It uses the exact production tokenizer fingerprint,
so no reindex is required; a future ICU selection or any other tokenizer fingerprint change requires
a full lexical projection rebuild. The official ParadeDB tokenizer material describes Unicode-word
and ICU segmentation plus token filters; the pinned 0.25.6 engine, not later documentation, was the
compatibility authority. A rollback-only probe and the declared live test both accepted ICU with
Russian stemmer/stopwords. The host RTX 4060 Ti was visible, but BM25/index work is CPU/database work
and did not use CUDA.

Current state: [lexical retrieval](../current/lexical-retrieval.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Frozen, leak-resistant final set | `tests/retrieval/test_calibration_config.py`; config fingerprint `bda16d3dd59332bb27b7933fcd52e9348ba889bf9fdfbc84473116974b4c5f4f` | pass; 12 final items cover inflection, exact identifiers, abbreviations, OCR noise, homoglyphs, e/yo, keyboard layout, transliteration and mixed language; no tuning interface |
| Query-only normalization and safe binding | `tests/retrieval/test_query_normalization.py`; `tests/retrieval/test_lexical_assets.py` | pass; NFC/literal behavior, aliases, layout, transliteration, homoglyphs, five-variant bound and injection-shaped input |
| Identical live indexes and immutable publication | `ARXIV_INT_RUN_LEXICAL_CALIBRATION=1 .venv/bin/python -m pytest tests/integration/lexical/test_live_calibration.py -m heavy -q`; configured-store `pg_tables` check | pass; pinned disposable `arxiv-int/postgres:17-0.25.6-age1.7.0`, four profiles, bundle verification; `calibration_relations=0` after rollback |
| Final adopt/retain/inconclusive gate | `$RUNS_DIR/run-68bd28ccf0244b07b40320d11c282407/evaluation/lexical/profiles.json` | pass; query normalization `adopt`: 6 wins / 0 losses / 6 ties, mean MRR delta +0.5, 95% interval +0.25 to +0.75, sign-test p=0.03125; ICU and morphology comparisons `inconclusive` |
| Held-out retrieval quality | same run `manifest.json`, artifact checksums `profiles.json=48f77fc5687bb900d9421f3d4d0a6700a1b1ee6079a5bc005a49e66f64b38c57`, `scores.jsonl=8d17d7d7fe4555eb07c9d001c217a0a98b004e4396ad09b57577cf7b26884522` | pass; adopted recall@5, MRR, span coverage and intactness 0.9167 versus baseline 0.4167; one inflection miss retained honestly |
| Cost and engine identity | same manifest, ParadeDB 0.25.6 | pass with fixture limit; adopted build 0.002389 s, p95 2.281 ms, index 3,022,848 bytes, table 3,055,616 bytes; ICU tied quality with p95 2.552 ms; one tiny synthetic run does not estimate archive scale or settle latency |
| Runtime and reindex decision | tokenizer `3b277b2329ad0f884d7af43261e195bc8577f8790b40792aaa3b0ac0b62ed47e`; code `509c68495feb205e056084d6682e1f9160cd66943ae0c5772c2fab04c2659ace`; manifest `7731ea19f6f3bc4b86802bc92fd1668631716c51ab8cb5a677b457a97f5016bf` | pass; query-only adoption, `reindex_required=false`; future tokenizer changes require rebuild |
| Deterministic retrieval tests | `.venv/bin/python -m pytest tests/retrieval -q` | pass; 27 passed |
| Static Python checks | `make format`; `make lint typecheck` | pass; 487 source files typed |
| Required CI | `make ci` | pass; 1,296 passed, 53 deselected; initial sandbox-only `make test` had 18 loopback `PermissionError` failures plus the deliberately not-yet-accepted record finding, then the unrestricted required rerun passed |

## Audit handoff

`none identified` after reviewing the query/index boundary, source preservation, candidate isolation,
bound parameters, publication immutability, costs and the retained inflection miss. The final run is
a synthetic held-out calibration, not evidence for provided-archive relevance; that proof is
[record 0073](0073-lexical-prove-lexical-retrieval-on-provided-archive.md).

## Close or resume

Implementation and live acceptance evidence pass. The task was removed from the forward plan and
dependent links now resolve through this record. At the user's request, the independent
second-opinion task ([record 0072](0072-lexical-review-and-deepen-russian-lexical-calibration.md))
owned stronger negative, inflectional, precision and repeated-cost evidence before provided-archive
proof. Final plan counts and CI evidence are recorded after the closing checks: 60 before and 60
after because this task closed and the user-requested second-opinion task was added; agent/human
lane counts remain 50/10. No human review handoff applies. Superseded by [record
0072](0072-lexical-review-and-deepen-russian-lexical-calibration.md): its independent review found
that the three dictionary wins here relied on aliases fitted to this run's final items and that
precision was unmeasured; its preregistered final run replaced `russian-safe-v1` with
`russian-guarded-v2`. This run remains immutable history.
