# Evaluation Foundation

The production package contains reusable metric functions and an immutable evaluation-result bundle.
It does not contain canned evaluation families, a fixture generator, a self-scoring pipeline stage,
or a capability-proof publication framework. Those milestone scaffolds were retired by
[record 0069](../records/0069-govern-retire-milestone-evaluation-scaffolding.md).

See [record 0033](../records/0033-eval-found-refactor-evaluation-bundle-validation.md),
[record 0036](../records/0036-eval-found-create-evaluation-fixtures-and-metrics.md),
[record 0038](../records/0038-eval-found-review-inference-and-evaluation-boundaries.md), and
[record 0069](../records/0069-govern-retire-milestone-evaluation-scaffolding.md).

## Metrics

`arxiv_int.evaluation.scoring` provides span extraction, hierarchical classification, retrieval,
p95 latency, linkage, paired bootstrap, BOM and financial arithmetic, catalog parity, graph/SQL
parity, anomaly cohort and review-budget, resource cost, ontology evolution, and geotemporal
metrics. Missing or non-finite evidence raises `MissingEvidenceError`; paired comparisons return
only `adopt`, `retain baseline`, or `inconclusive`.

Metric tests construct their cases directly in `tests/evaluation/scoring/`. Real tuning and final
items belong under operator-configured evaluation roots and must be scored against actual pipeline
predictions when the planned `evaluate` stage is implemented. The declared stage remains
unregistered until it consumes those upstream outputs.

## Immutable result bundles

`arxiv_int.evaluation.bundles` publishes one directory per evaluation result. The tree is the
artifact boundary: every named file must be a regular file inside that directory after symlink
resolution. Publication writes `scores.jsonl` and optional extra artifacts, then a canonical
`manifest.json` with run and input identities, configuration, metrics, verdict, and artifact
checksums.

`verify_run_bundle()` hashes artifacts in 1 MiB chunks, caps the manifest at 1 MiB, requires the
exact registered file set and canonical encoding, and returns the SHA-256 fingerprint of the
manifest bytes. Publication refuses to replace an existing destination, including a symlink.
Artifact names reject absolute paths, parent traversal, empty components, null bytes, and the
reserved root names `manifest.json` and `scores.jsonl`.

Publication claims an empty destination with exclusive `mkdir`, writes and verifies a sibling
staging tree, and replaces the claim atomically on the same filesystem. File contents are flushed;
directory fsync and power-loss durability are not claimed. Verification opens regular files with
`O_NOFOLLOW`, checks containment, and streams their hashes.

Deterministic tests under `tests/evaluation/bundles/` cover publication, replay, corruption,
unexpected files, path escape, symlinks, fifos, malformed/noncanonical manifests, invalid artifact
records, occupied destinations, and competing publishers.

## Archive integration

`make test-archive` loads configured roots and runs every test marked `archive`. `make test`,
`make ci`, coverage, and GitHub do not read operator archives. Extra cross-checks live only in
`tests/integration/`; the tests do not publish a second manifest or capability registry.

`tests/integration/corpus/test_archive_pipeline.py` is the explicit provided-archive check for the
currently implemented corpus closure. The test creates an ordinary run through `chunk`, applies the
normal forecast and stage implementations, then independently rechecks attempt and snapshot
checksums, generated contracts, occurrence and quarantine accounting, document hashes, source
anchors, normalization views, offset maps, duplicate representatives, and chunk source
reconstruction. It rehashes physical source files after the run and requires an unchanged replay to
use only cache hits with zero worker calls.

`tests/integration/lexical/test_archive_lexical.py` is the explicit provided-archive check for
lexical load and query. The test creates an ordinary run through `load-lexical`, reconciles the
active covering table, runs declared query kinds against sampled live chunks, requires resolved
citations and honored limits, and requires an unchanged replay to use only cache hits with zero
worker calls. Results and limits are in
[lexical retrieval](lexical-retrieval.md#provided-archive-integration) and
[record 0073](../records/0073-lexical-prove-lexical-retrieval-on-provided-archive.md).
