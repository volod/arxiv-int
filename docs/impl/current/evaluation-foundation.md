# Evaluation Foundation

Frozen evaluation fixtures, paired metrics, the `evaluate` stage, and a shared proof dispatcher
are available now. Human gold review and provided-archive proofs remain later tasks.

See [record 0033](../records/0033-eval-found-refactor-evaluation-bundle-validation.md),
[record 0035](../records/0035-eval-found-implement-committed-proof-identity-obfuscation.md),
[record 0036](../records/0036-eval-found-create-evaluation-fixtures-and-metrics.md), and
[record 0038](../records/0038-eval-found-review-inference-and-evaluation-boundaries.md).

## Frozen fixtures

Committed families live under `tests/fixtures/evaluation/`. Each item has a tuning or final split,
`gold_ref`, dataset identity, provenance, gold, and paired positive/negative predictions.
`index.json` is the replayable item ledger. Families:

extraction, classification, russian-retrieval, semantic, entity, fact, ontology, graph,
domain-artifact, catalog, anomaly, reporting, geotemporal, domain-negative.

Split leakage refuses shared item ids, gold refs, or gold content. Missing provenance refuses
the ledger. Bootstrap seed `13` replays the same fingerprint. These are synthetic fixtures with
no real identities; Git-bound source-derived copies still use the
[identity exporter](#git-bound-identity-export). Local gold originals and human-review packets
are not rewritten.

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

Threshold defaults live in `configs/evaluation/thresholds.json` and do not auto-adopt.

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

`configs/proofs/capabilities.json` maps each capability to usable stages and required
validators. `arxiv-int evaluation proof discover` lists them. Unknown capabilities fail.
`evaluation-foundation` can publish a fixture proof; other capabilities refuse until their
usable stages are validated.

A typed `proof-manifest.json` records fingerprints, stage statuses, validators, and artifact
checksums. Publication claims the destination with exclusive `mkdir` and refuses to replace an
existing proof directory. Check rejects stale code/fixture fingerprints, missing checksums,
unvalidated usable stages, private paths, `identities.json`, unobfuscated corpus text, and
nonregular entries in the Git-bound proof tree.

```text
arxiv-int evaluation proof discover
arxiv-int evaluation proof publish --capability evaluation-foundation --run-id ID \
    --results-dir DIR --runs-dir DIR
arxiv-int evaluation proof check --proof-dir DIR
make proof CAPABILITY=evaluation-foundation RUN_ID=...
make evaluation-fixtures-check
```

Proofs for this capability write `$RESULTS_DIR/proofs/evaluation-foundation/<proof-id>/`.
Tool diagnostics stay under `$DATA_DIR/evaluation/<run-id>/`.

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
| `evaluation/export_*.py`, `exporter.py` | Git-bound identity obfuscation from a verified bundle |

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

## Git-bound identity export

`export_proof_bundle()` copies selected artifacts from a verified run bundle to explicit Git-bound
paths. It does not mutate the source bundle, archive silos, local proofs, or human-review packets,
and it does not commit. Policy version 1 uses public namespace `arxiv-int/proof-identity/v1` and
SHA-256; there is no secret key or rotation service.

The source bundle may include `identities.json` declaring person, company and product entities,
aliases, typed email/phone/address/account fields, and character spans. Empty catalogs are valid
for synthetic fixtures with no real identities. Entity labels hash stable ids so same-name entities
stay distinct. Shared contacts hash normalized field values so repeats stay comparable. Phone,
address and account substitutes keep required shape and replacement check digits. Colliding
substitutes and residual source identities refuse export. Unsupported binaries are refused rather
than copied raw. `identities.json` itself cannot be exported.

Text, JSON and JSONL are rewritten together, including queries, labels, expected answers, graph
references and remapped spans. Dates, coordinates, quantities and units are not independently
hashed. Exported manifests record `data_class=transformed` so metrics are not labelled raw-archive
results. The complete source-to-substitute map stays under `$DATA_DIR/proof-export/<run-id>/`.
The identity-free receipt carries policy, source-bundle and export fingerprints.

Commands:

```text
arxiv-int evaluation export-proof --source-bundle DIR --map ARTIFACT=DEST --run-id ID
arxiv-int evaluation identity-policy generate|check
make proof-export SOURCE_BUNDLE=... MAP="a=b" RUN_ID=...
make identity-policy-check
```

Relative destinations resolve against `--destination-root` or the project root. Repeated runs from
different roots and mapping order produce the same export fingerprint and bytes.

## Tests and verification

Deterministic tests under `tests/evaluation/` cover happy-path publication, fingerprint replay,
corruption, unregistered files, reserved names, path escape, an external symlink with matching
bytes, a symlinked artifact directory, a fifo, a symlinked manifest, a destination symlink,
malformed and non-canonical manifests, missing identities, invalid digests, and competing
publishers. Export tests cover cross-root/order determinism, same-name nonmatch, alias and shared
contact consistency, graph joins, span remap, phone/address/account check digits, collision and
leak refusal, original-byte preservation, local-only files, binary refusal, and transformed
manifest marking. Fixture tests cover split leakage, ledger replay, positive/negative polarity,
missing-evidence and non-finite metric refusal, ontology/geotemporal/domain negatives after
identity export, proof discovery, unknown capability, stale fingerprints, missing checksums,
unvalidated stages, evaluate/proof no-replace publication, leaking proof trees, and retired
`PROOF_ARCHIVE_DIR` isolation from evaluation roots.
Fixture coverage does not prove real-archive quality.

The inference/evaluation checkpoint also covers cross-process GPU leases, requested-model
identity mismatch, and parser registration without optional HTTP extras. See
[record 0038](../records/0038-eval-found-review-inference-and-evaluation-boundaries.md).

Disposable synthetic bundle evidence lives under `$DATA_DIR/bundle-validation/<run-id>/`.
Synthetic export evidence lives under `$DATA_DIR/proof-export/<run-id>/`. Synthetic evaluate and
fixture-proof evidence lives under `$DATA_DIR/evaluation/<run-id>/`. Those trees are not
provided-archive proofs.

Local proof and human-review packets retain original identities. Fixture builders must use this
exporter for any Git-bound source-derived copy. See the
[export policy](../../design/spec.md#identity-obfuscation-for-committed-proof-artifacts).
