# Lexical Retrieval

The `load-lexical` stage bulk-loads the canonical corpus, rebuilds the ParadeDB BM25 projection, and
`arxiv-int search lexical` serves calibrated Russian-aware ranked search, filters, snippets, facets,
literal identifier lookup and diagnostics over the active projection. Semantic and hybrid fusion are
not implemented; see the [forward plan](../plan.md).

See [record 0070](../records/0070-lexical-build-paradedb-lexical-load-and-query-path.md) and
[record 0071](../records/0071-lexical-calibrate-russian-tokenization-and-bm25.md). The projection
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

The selected `russian-safe-v1` query profile applies NFC and bounded, query-only variants for the
reviewed abbreviation/alias dictionary, Cyrillic/Latin homoglyphs, wrong keyboard layout, and Latin
transliteration. The original query remains a bound variant, every added variant is separately bound,
and at most five variants are sent to the engine. Stored text and source snippets are never rewritten.
The query-policy fingerprint and selected profile id appear in search JSON.

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

## Calibration decision

Run `run-68bd28ccf0244b07b40320d11c282407` on ParadeDB 0.25.6 adopted
`unicode-russian-safe-v1` over `unicode-russian-v1`. At `k=5` on 12 frozen final cases, recall, MRR,
span coverage, and intactness each rose from 0.4167 to 0.9167. The paired MRR comparison had 6 wins,
0 losses and 6 ties; its 95% bootstrap interval was +0.25 to +0.75 and its exact sign-test p-value was
0.03125. Exact identifiers, mixed-language text, and the retained successful inflection case did not
regress. One inflection case remains missed and prevents a perfect result.

ICU/Russian tied normalized Unicode on all 12 quality readings and received `inconclusive`; their
single-run fixture p95 readings were 2.552 ms and 2.281 ms respectively. All four tiny indexes were
3,022,848 bytes and their covering tables were 3,055,616 bytes, so these costs prove comparative
execution only and do not estimate archive scale. The morphology comparison improved two cases but
was also `inconclusive` under the paired gate.

The adopted profile changes only query processing. Its tokenizer fingerprint remains
`3b277b2329ad0f884d7af43261e195bc8577f8790b40792aaa3b0ac0b62ed47e`, so this adoption requires no
reindex. Selecting ICU or changing any index tokenizer declaration changes that fingerprint and
requires a full lexical projection rebuild before activation. The final manifest fingerprint is
`7731ea19f6f3bc4b86802bc92fd1668631716c51ab8cb5a677b457a97f5016bf`; its registered score and
profile artifacts verify in place. This synthetic held-out run is not the provided-archive relevance
proof. The CUDA device was available but unused because ParadeDB BM25 calibration is CPU/database
work.

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
