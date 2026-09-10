# Evaluation Foundation

Frozen evaluation fixtures, paired metrics, the `evaluate` stage, and a shared proof dispatcher
are available now. Human gold review and remaining provided-archive proofs stay later tasks.
`pipeline-control` and `corpus-foundation` can publish provided-archive proofs;
`evaluation-foundation` can publish a
fixture proof.

See [record 0033](../records/0033-eval-found-refactor-evaluation-bundle-validation.md),
[record 0035](../records/0035-eval-found-implement-committed-proof-identity-obfuscation.md),
[record 0036](../records/0036-eval-found-create-evaluation-fixtures-and-metrics.md), and
[record 0038](../records/0038-eval-found-review-inference-and-evaluation-boundaries.md), and
[record 0057](../records/0057-eval-found-retire-committed-proof-export.md).

## Frozen fixtures

Committed families live under `tests/fixtures/evaluation/`. Each item has a tuning or final split,
`gold_ref`, dataset identity, provenance, gold, and paired positive/negative predictions.
`index.json` is the replayable item ledger. Families:

extraction, classification, russian-retrieval, semantic, entity, fact, ontology, graph,
domain-artifact, catalog, anomaly, reporting, geotemporal, domain-negative.

Split leakage refuses shared item ids, gold refs, or gold content. Missing provenance refuses
the ledger. Bootstrap seed `13` replays the same fingerprint. These are synthetic fixtures with
no real identities. Gold originals and human-review packets stay under the operator's configured
roots and are never committed.

Ontology fixtures cover add, deprecate-with-successor, draft refusal, and disjoint contradiction.
Geotemporal fixtures keep source-valid time distinct from recorded time, retain unknown CRS,
and pin role intervals and revision/effectivity. Domain negatives cover same-name nonmatches,
invoice-not-delivery, and references-not-part-of. Identity replacement cannot make those
negatives valid.

## Metrics

`arxiv_int.evaluation` extends the existing extraction, linkage, retrieval, and paired-bootstrap
primitives with span extraction, hierarchical classification, p95 latency, BOM/financial
arithmetic, catalog parity, graph/SQL parity, anomaly cohort/false-positive/review-budget
precision, resource cost, ontology evolution, and geotemporal scoring.

Missing predictions, empty metric vectors, empty latency samples, and non-finite metric values
raise `MissingEvidenceError` and cannot produce adopt/retain. Pandera/dbt
`DatasetValidationResult` values stay `structural`; held-out fixture scores stay `held-out`.
Exported metrics carry `data_class=transformed` and are not labelled raw-archive results.
Positive fixtures score strictly above their paired negatives.

Threshold defaults live in `src/arxiv_int/resources/configs/evaluation/thresholds.json` and do not auto-adopt.

## Evaluate stage

`EvaluateStage` is the registered `evaluate` body. It scores frozen polarities, records the
item ledger, and publishes an immutable run bundle under `$RUNS_DIR/<run-id>/evaluation/`
through `publish_run_bundle()`. Setup marks `evaluate` implemented; other pipeline stages
remain unimplemented.

```text
arxiv-int evaluation evaluate --run-id ID --runs-dir DIR
make eval RUN_ID=...
```

## Proof dispatcher

`src/arxiv_int/resources/configs/proofs/capabilities.json` maps each capability to usable stages and
required
validators. `arxiv-int evaluation proof discover` lists them. Unknown capabilities fail.
`evaluation-foundation` can publish a fixture proof; `pipeline-control` and `corpus-foundation`
can publish provided-archive proofs. Other capabilities refuse until their usable stages are
validated. The [corpus proof](corpus-foundation.md#provided-archive-proof) additionally verifies
external artifact bytes, source accounting, model identities, contracts and source offsets in place.

A typed `proof-manifest.json` records fingerprints, stage statuses, validators, and artifact
checksums. Publication claims the destination with exclusive `mkdir` and refuses to replace an
existing proof directory. Check rejects stale code/fixture fingerprints, missing checksums,
unvalidated usable stages, private paths, `identities.json`, unobfuscated corpus text, and
nonregular entries in the Git-bound proof tree.

```text
arxiv-int evaluation proof discover
arxiv-int evaluation proof publish --capability evaluation-foundation --run-id ID \
    --results-dir DIR --runs-dir DIR
arxiv-int evaluation proof publish --capability pipeline-control --run-id ID \
    --results-dir DIR --runs-dir DIR
arxiv-int evaluation proof check --proof-dir DIR
make proof CAPABILITY=evaluation-foundation RUN_ID=...
make proof CAPABILITY=pipeline-control RUN_ID=...
make evaluation-fixtures-check
```

Proofs for evaluation-foundation write `$RESULTS_DIR/proofs/evaluation-foundation/<proof-id>/`.
Pipeline-control proofs write `$RESULTS_DIR/proofs/pipeline-control/<proof-id>/`.
Tool diagnostics stay under `$DATA_DIR/<capability>/<run-id>/`.

## Run bundles

`arxiv_int.evaluation` publishes one directory per run. The tree is the artifact boundary: every
named file must be a regular file inside that directory after symlink resolution. A matching byte
string reached through a symlink, fifo, or other nonregular entry cannot satisfy verification.

Publication writes `scores.jsonl` and optional extra artifacts, then a canonical `manifest.json`.
`verify_run_bundle()` hashes artifacts in 1 MiB chunks, caps the manifest at 1 MiB, and returns the
SHA-256 fingerprint of the on-disk canonical manifest. Replay of an unchanged tree yields the same
fingerprint. The publisher refuses to replace an existing destination, including a symlink occupying
that name.

Modules:

| Module | Owns |
| --- | --- |
| `evaluation/bundle_errors.py` | Typed publish/verify failures |
| `evaluation/bundle_layout.py` | Names, reserved paths, tree walk, `O_NOFOLLOW` open, exclusive claim |
| `evaluation/bundle_manifest.py` | Schema version 1 identity, canonical JSON, artifact registry |
| `evaluation/bundles.py` | `BundleSpec`, `publish_run_bundle()`, `verify_run_bundle()` |
| `evaluation/families*.py`, `fixture_*.py` | Frozen families, split guards, item ledger |
| `evaluation/accuracy.py`, `domain_eval.py`, `geo_eval.py`, `anomaly_eval.py`, `scoring.py` | Paired metrics and missing-evidence refusal |
| `evaluation/stage.py`, `evaluate_run.py` | Evaluate stage and bundle publication |
| `evaluation/proof_*.py` | Capability registry, freshness, redaction, dispatcher |

`manifest.json` and `scores.jsonl` are reserved root names. Extra artifact names are normalized to
relative posix paths before those reservations are applied. Absolute names, parent traversal, empty
parts, and null bytes are refused.

Required manifest identities are `schema_version`, `run_id`, `kind`, `input_fingerprints`,
`configuration`, `metrics`, `verdict`, and `artifacts`. Missing, padded, or non-canonical encodings
fail as `BundleManifestError` before reuse. Artifact records require a 64-character lowercase
hex digest and a non-negative byte count.

## Durability and memory

The publication point is an exclusive `mkdir` of the destination followed by `os.replace` of the
verified staging tree onto that empty claim. Both names live in the destination parent, so the
replace stays on one filesystem.

| Event | Result |
| --- | --- |
| Process crash before the claim | Destination is absent. A leftover `.name.tmp-*` staging directory may remain. Retry is safe. |
| Process crash after `mkdir` and before replace | An empty destination remains and blocks a later publish. It is not treated as published evidence. |
| Process crash after replace | Destination is the verified tree. Concurrent publishers lose with `BundleExistsError`. |
| Power loss | File data is flushed, not fsynced. Directory fsync is not performed. Power-loss durability is not claimed. Pipeline leases and lake publication remain separate tasks. |

Verify never slurps artifact payloads. It opens each regular file with `O_NOFOLLOW`, confirms the
opened path stays under the resolved bundle root (`/proc/self/fd` on Linux), and hashes in 1 MiB
chunks. Publisher callers still pass extra artifacts as in-memory bytes; scores rows are written
incrementally.

## Published proof bundles

A capability proof is written under `RESULTS_DIR/proofs/<capability>/<proof-id>/` and reviewed
there. Nothing copies it, an excerpt of it, or its location into this repository; there is no
command, Make target or packaged asset that turns source-derived proof data into repository files.

An `evaluation-foundation` bundle holds `proof-manifest.json`, `summary.txt` and
`fingerprint.json`. A `pipeline-control` bundle adds `gates.json`, `scenario.json` and
`forecast-summary.json`. A `corpus-foundation` bundle additionally retains an external artifact
registry, full source/accounting/offset validation metrics and resource histories; its enclosing
immutable bundle manifest checks every payload. The manifest carries the capability, proof and run
ids, `data_class`,
verdict, input fingerprints, stage and validator outcomes, and a sha256/byte record for every
artifact. `fingerprint.json` records `data_class` and the `raw_fingerprint` of the manifest bytes,
so a reviewer can confirm the bundle they hold is the one a record names.

`publish_capability_proof()` refuses an unregistered capability, a capability whose usable stages
have no publisher, and an occupied destination, including a symlink at that name. The fixture and
pipeline-control publishers apply their summary leak rules before writing: configured roots are
replaced by their variable names,
a private path marker refuses publication, synthetic identity labels refuse publication, and an
`identities.json` entry anywhere in the tree refuses both publication and check.

`check_capability_proof()` re-reads a published directory, resolves the capability's expected
fingerprints, enforces the checksum, freshness and usable-stage gates, walks the tree for leaks and
nonregular entries, and returns the manifest fingerprint. The corpus checker additionally checks
the immutable bundle and every referenced external artifact, then replays source, contract,
accounting, offset and resource validation. A new corpus `PROOF_ID` preserves earlier bundles when
re-proving an existing run.

Commands:

```text
arxiv-int evaluation proof discover|publish|check|generate-registry
make proof CAPABILITY=... RUN_ID=...
make evaluation-fixtures-check
```

## Tests and verification

Deterministic tests under `tests/evaluation/` cover happy-path publication, fingerprint replay,
corruption, unregistered files, reserved names, path escape, an external symlink with matching
bytes, a symlinked artifact directory, a fifo, a symlinked manifest, a destination symlink,
malformed and non-canonical manifests, missing identities, invalid digests, and competing
publishers. Fixture tests cover split leakage, ledger replay, positive/negative polarity,
missing-evidence and non-finite metric refusal, ontology/geotemporal/domain negatives, proof
discovery, unknown capability, stale fingerprints, missing checksums, unvalidated stages,
evaluate/proof no-replace publication, leaking proof trees, the published proof-bundle shape with
its refusal of any export or identity-policy command, and retired `PROOF_ARCHIVE_DIR` isolation
from evaluation roots.
Fixture coverage does not prove real-archive quality.

The inference/evaluation checkpoint also covers cross-process GPU leases, requested-model
identity mismatch, and parser registration without optional HTTP extras. See
[record 0038](../records/0038-eval-found-review-inference-and-evaluation-boundaries.md).

Disposable synthetic bundle evidence lives under `$DATA_DIR/bundle-validation/<run-id>/`.
Synthetic evaluate and fixture-proof evidence lives under `$DATA_DIR/evaluation/<run-id>/`. Those
trees are not provided-archive proofs.

Proof and human-review packets stay under the configured roots and a reviewer validates them in
place. The Git-bound exporter, its packaged proof-identity policy, the `identity-export` validator
and the `no_export` gate were retired by
[record 0057](../records/0057-eval-found-retire-committed-proof-export.md); the superseded bundle
shape it removed is recorded there. See
[published proof and evaluation data](../../design/spec.md#published-proof-and-evaluation-data).
