# Evaluation Foundation

Immutable local evidence bundles are available now. Frozen evaluation
fixtures, paired metrics, and proof-bundle publication remain planned in
[create-evaluation-fixtures-and-metrics](../plan.md#create-evaluation-fixtures-and-metrics).

See [record 0033](../records/0033-eval-found-refactor-evaluation-bundle-validation.md).

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

## Tests and verification

Deterministic tests under `tests/evaluation/` cover happy-path publication, fingerprint replay,
corruption, unregistered files, reserved names, path escape, an external symlink with matching
bytes, a symlinked artifact directory, a fifo, a symlinked manifest, a destination symlink,
malformed and non-canonical manifests, missing identities, invalid digests, and competing
publishers. Fixture coverage does not prove real-archive quality.

Disposable synthetic evidence for this repair lives under `$DATA_DIR/bundle-validation/<run-id>/`.
That tree is not a provided-archive proof.
