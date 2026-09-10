# Lexical Retrieval

The `load-lexical` stage bulk-loads the canonical corpus, rebuilds the ParadeDB BM25 projection, and
`arxiv-int search lexical` serves calibrated Russian-aware ranked search, filters, snippets, facets,
literal identifier lookup and diagnostics over the active projection. Semantic and hybrid fusion are
not implemented; see the [forward plan](../plan.md).

See [record 0070](../records/0070-lexical-build-paradedb-lexical-load-and-query-path.md),
[record 0071](../records/0071-lexical-calibrate-russian-tokenization-and-bm25.md) and
[record 0072](../records/0072-lexical-review-and-deepen-russian-lexical-calibration.md). The projection
lifecycle, versioned tables and activation pointers belong to the
[canonical store](canonical-store.md); the stage contract and reuse rules belong to
[pipeline control](pipeline-control.md).

## Load stage

`arxiv_int.pipeline.load_lexical` runs after `chunk`. It validates the chunk snapshot manifest the
DAG hands it, then follows the checksum-bound pointers that manifest names to the normalization and
extraction snapshots, so a load never reads an artifact it has not rehashed. Extraction rows carry no
language, so the load applies the language normalization detected per document and leaves undetected
documents null rather than inventing `und`.

Rows stream in 2000-row batches. Each batch is Pandera-validated against its contract, written into
`staging.*` with psycopg binary COPY, upserted into `corpus.documents` and `corpus.chunks` through a
bound SQLAlchemy `ON CONFLICT DO UPDATE`, and the staging table is emptied before the next batch.
Binary COPY applies no cast rule, so `copy_binary()` reads the declared staging column type OIDs and
binds them; a staging table missing a declared column is refused instead of producing a protocol
error.

The stage then calls the shared projection lifecycle for the lexical kind, which builds the dbt
`derived.proj_lexical_rows__g_<version>` input, creates the versioned covering table and its BM25
index, validates the build and switches the active pointer. Everything runs under one publication
lock below `$RUNS_DIR/<run-id>/search/`.

## Reconciliation and evidence

A load is only publishable when no canonical chunk is missing from the covering table, the projection
row count equals the canonical chunk count, and, when this load covered the whole corpus, the loaded
chunk checksum equals the projection checksum. An incremental load whose projection legitimately
covers earlier generations reports `partial` scope and does not require checksum equality. Failing
reconciliation raises and no manifest is published.

`$RUNS_DIR/<run-id>/search/lexical.json` records the schema id, generation, load counts and
checksums per contract, projection identity, quality status, row count, index and covering-table
byte sizes, the indexed columns, the tokenizer fingerprint, the reconciliation decision, and the
three validated upstream pointers. `validate_load_lexical_output()` rehashes that manifest on every
cache check and refuses a symlinked path, a generation mismatch or a stored non-reconciling result,
so a stale attempt cannot be reused.

## Index and query assets

`arxiv_int.stores.projections.adapters.lexical` owns the covering table and the single BM25 index per
version. The selected `unicode-russian-v1` index profile keeps ParadeDB's default Unicode tokenizer
with the Russian stemmer and Russian stopwords for `body` and `title`;
`identifiers` uses a whitespace tokenizer with lowercasing disabled so literal ids survive intact;
`language` and `document_id` use fast keyword fields for filters and facets. The JSON profile is
hashed into a tokenizer fingerprint that is retained with every load.

The selected `russian-guarded-v2` query profile applies NFC, then plans bounded, query-only
variants in three stages.

- The primary stage always runs. It sends:
  - the original text;
  - reviewed `technical-v2` abbreviations, substituted as phrases inside the query, plus the
    abbreviation for any expansion the query already contains (two-letter keys only in upper
    case);
  - per-token homoglyph repair toward each token's majority script, and cross-script variants of
    identifier codes;
  - a genitive-stem probe for nouns with a fleeting e/o.
- Keyboard-layout and positional transliteration variants run only when the primary stage matches
  nothing.
- A conjunctive edit-distance-1 match over the words of at least five characters in each primary
  variant runs only when both earlier stages match nothing.

A query that uses query syntax (field prefixes, quotes, grouping, leading `+`/`-`, AND/OR/NOT) is
sent unchanged. Every variant is a separate bound parameter, with at most five per stage. Stored
text and source snippets are never rewritten. Search JSON reports the profile, the policy
fingerprint and `queryStage`. The previously accepted `russian-safe-v1` profile and its
`legacy-v1` aliases stay declared only to replay record 0071. That legacy map contains an alias
fitted to 0071's final fixture and must not be served.

`adapters.lexical_search` holds every ParadeDB operator and query-builder call. User text, field
names, filter values, limits, offsets and snippet tags are always bound parameters; only whitelisted
identifiers are composed into SQL. A field that is not indexed, or a facet column that is not a
filter field, is refused by name with the allowed set. `arxiv_int.retrieval.lexical` exposes the typed
`LexicalRequest`, ranked `search()`, literal `lookup()` and `explain()`; `retrieval.projection`
resolves the active target, index sizes and in-flight BM25 builds; `retrieval.citations` resolves each
hit back to its `corpus.chunks` chunker and source span and reports any hit that does not resolve.

## Commands

`make search-lexical QUERY=...` and `arxiv-int search lexical QUERY` query the active projection.
`--mode identifier` switches from ranked matching to exact literal lookup, `--language` and
`--document-id` filter, `--facet` counts a filter column, `--field` narrows the searched fields,
`--limit`/`--offset` page, `--snippet-chars` and `--no-snippets` control highlighting, `--citations`
resolves source spans, `--lenient` tolerates unparsable query syntax, `--explain` adds the analyzed
plan with index sizes and concurrent build activity, and `--json` prints one canonical object.

Exit 2 means no validated projection is active and names the command that builds one. Exit 1 covers a
refused field, an unparsable query or a driver failure, each reported with the engine's own message.
An empty ranked search is a successful query; only an unresolved identifier lookup fails.

`make calibrate-lexical RUN_ID=<created-run-id>` (or `arxiv-int search calibrate --run-id ...`)
builds every declared candidate on identical frozen rows inside a rolled-back transaction, measures
held-out retrieval and cost, and publishes one immutable bundle at
`$RUNS_DIR/<run-id>/evaluation/lexical/`. An existing bundle is never replaced.

`make lexical-second-opinion RUN_ID=<created-run-id> STAGE=development|preregister|final` (or
`arxiv-int search second-opinion --run-id ... --stage ...`) runs the frozen second-opinion
calibration in `retrieval.second_opinion`:

- `development` scores only the development split. It accepts `FILLER_CHUNKS`,
  `BUILD_REPETITIONS` and `QUERY_REPETITIONS` cost overrides.
- `preregister` publishes a bundle that binds the final split, protocol, arms, review packet,
  query policy and code fingerprints.
- `final` refuses to run without a verified preregistration in the same run whose fingerprints
  still match, and refuses every override.

Each stage publishes once at `$RUNS_DIR/<run-id>/evaluation/lexical-second-opinion/<stage>/`, with
a per-arm, per-case ledger, `report.json`, and copies of the frozen inputs.

## Calibration decision

Record 0072's preregistered final run `run-204c1ec6c5c846fd8546a0781a7b1789` on ParadeDB 0.25.6
adopted `russian-guarded-v2` over the previously accepted `russian-safe-v1`. Both served the
unchanged `unicode-russian-v1` index.

- **Inputs:** the final split has 122 frozen cases and 199 judged chunks, alongside 70,000
  vocabulary-disjoint filler chunks. It was preregistered at 2026-09-10T22:22:00Z (manifest
  `6bf8669688b0...`) and executed once, with 5 index rebuilds and 30 query repetitions in seeded
  random orders.
- **Quality:** on 90 quality cases, nDCG@10 rose from 0.680 to 0.959: 27 wins, 0 losses and 63
  ties; 95% interval +0.187 to +0.375; sign-test p=1.5e-8.
- **Precision:** on 54 precision cases, returned precision@5 rose from 0.431 to 0.464: 4/0/50;
  interval +0.005 to +0.069.
- **Gates:** every mandatory gate passed:
  - identifier exactness;
  - no new syntax errors or forbidden hits;
  - no increase in no-answer false positives;
  - latency (p95 5.15 ms versus 4.88 ms).
- **Stability:** all five bootstrap seeds agreed, and every ranked hit was identical across
  repetitions and query orders.
- **Bundle:** the final manifest is `e691b9b8db5b...`.

Factor readings from the same run:

- Russian stemming added 0.204 nDCG (19/0) but cost 0.105 returned precision (0/13), because it
  conflates homonymous stems. It is retained.
- Russian stopwords and ICU segmentation made no significant difference. The Unicode tokenizer
  is retained; ICU would require a rebuild for no measured gain.
- Among the accepted transforms, transliteration alone cost 0.25 returned precision (0/15) by
  reading English words as Russian. The v1 aliases changed nothing on new items, because their
  entries matched 0071's final queries.
- Candidate leave-one-out, in wins over the ablated profile:
  - aliases: +6 quality;
  - fuzzy stage: +8 quality;
  - phrase binding: +5 precision;
  - fallback gating: +4 precision;
  - homoglyph repair: +2 quality and +2 precision.

  The fleeting-vowel probe and the syntax guard tied here. The fuzzy stage recovered the same
  inflections, and the guard removes the error `russian-safe-v1` raised on a field query.

Costs on 70,199 rows:

- BM25 indexes took 17.3 to 21.4 MB, 18.9 MB for `unicode-russian`, over 88 to 92 MB covering
  tables.
- Median build time was 0.38 to 1.18 s per profile, and rebuilds of one profile varied up to
  about six-fold.
- The guarded profile's p50/p95 was 2.67/5.15 ms. Of 122 cases, 22 were answered by the fallback
  stage and 9 by the fuzzy stage.

Residual limits:

- Both profiles return an unrelated Russian row for all 12 English no-answer words through
  transliteration.
- OCR recovery happens only when the correct spelling is absent from the corpus, because fuzzy
  matching is a zero-hit fallback.
- These synthetic cases do not prove provided-archive relevance.

The adoption changes only query processing. The index tokenizer fingerprint stays
`3b277b2329ad0f884d7af43261e195bc8577f8790b40792aaa3b0ac0b62ed47e`, `reindex_required=false`, and
existing lexical projections remain valid. Switching the default profile after the decision changed
the query-policy fingerprint from `9a37dfc6...` to `8c020cf3...`; the adopted profile's declaration
did not change. Selecting ICU or any other index profile changes the tokenizer fingerprint and
requires a full lexical projection rebuild before activation.

Record 0071's run `run-68bd28ccf0244b07b40320d11c282407` adopted `russian-safe-v1` on 12 final
cases. The second opinion found that that run's three dictionary wins relied on aliases fitted to
those items, one of them mapping a word to the fixture's OCR misspelling, and that it never
measured precision. The run remains immutable history, not current evidence. The CUDA device was
available but unused: BM25 calibration is CPU and database work.

## Tests and results

Deterministic tests cover the tokenizer and query profiles, bounded aliases/layout/transliteration,
parameter binding against injection-shaped input,
field and facet refusals, statement shape, request validation, result and citation JSON, load
reconciliation across full and partial scope, manifest publication and tamper refusal, reuse
validation, language enrichment, batch streaming, staging type binding, and stage registration.
`tests/integration/lexical/test_live_lexical.py` is the declared live check: it applies revisions to
a disposable pinned store, refuses before activation, loads, builds, then asserts ranked hits,
snippets, facets, filters, identifier lookup, the ParadeDB plan and resolved citations. It is marked
`heavy` and needs `ARXIV_INT_RUN_LEXICAL=1`, so `make ci` does not start containers.

On the operator archive the stage loaded 414 documents and 70550 chunks, built a 27 MiB BM25 index
over a 65 MiB covering table, reconciled with zero unindexed chunks, and served filtered Russian
queries with snippets in single-digit milliseconds. A second load rebuilt and switched the active
version while queries continued to serve the previous one, and the retired version was reported and
dropped by the projection cleanup command.

`tests/integration/lexical/test_live_calibration.py` is the separate declared calibration check. It
uses the pinned disposable ParadeDB image, creates all four indexes on identical source-safe rows,
checks the paired adoption and no-reindex decision, verifies the immutable bundle, and rolls back all
calibration relations.

`tests/retrieval/test_query_plans.py`, `test_second_opinion_inputs.py` and
`test_second_opinion_decision.py` cover:

- staged plans, syntax preservation, alias phrase binding and homoglyph, transliteration and
  fleeting-vowel rules, including the NFC primary clause and stage order;
- frozen-input tamper refusal, split distinctness and minimums;
- alias leak gates against both splits and filler disjointness;
- chunk-level scoring;
- the preregistered verdict rule.

`tests/integration/lexical/test_live_second_opinion.py` (`heavy`,
`ARXIV_INT_RUN_LEXICAL_SECOND_OPINION=1`) runs a small development stage on the pinned disposable
store. It checks that final execution is refused without preregistration or with overrides, that
the bundle verifies, that every arm is reported, and that rollback leaves no relations. It asserts
harness invariants, never the research verdict.
