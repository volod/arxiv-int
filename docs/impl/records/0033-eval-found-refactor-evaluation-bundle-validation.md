# Task Record

## Task and scope

- Id / capability / checkpoint: `refactor-evaluation-bundle-validation` / `evaluation-foundation` /
  `review-corpus-and-control-integrity`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `refactor-evaluation-bundle-validation`; code revision `866a07e`
  with a clean working tree at task start. Initial count: 74 tasks (64 agent, 10 human).
- Audit input: [AUD-codebase-05](0001-govern-codebase-and-workflow-audit.md#audit-handoff).
- Amendments: none.

```markdown
#### refactor-evaluation-bundle-validation

Make existing evidence-bundle validation honor the claimed immutable local artifact boundary.

- Serves: `evaluation-foundation` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-codebase-05](records/0001-govern-codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Quality baseline repair](records/0003-foundation-restore-quality-gate-baseline.md);
[Evaluation primitives](current/project-foundation.md#evaluation-and-retrieval-primitives).
- User-visible outcome: A bundle cannot pass verification by reading a matching file outside its own
tree, and
malformed manifest identities produce typed failures before reuse.
- Scope boundary: Strengthen the current publisher/verifier; generic pipeline leases and scalable lake
publication remain separate tasks. Do not require loading corpus-scale artifacts into memory.
- Data and artifact paths: `src/arxiv_int/evaluation/bundles.py`,
`tests/evaluation/test_bundles.py`, and
`$DATA_DIR/bundle-validation/<run-id>/` with disposable synthetic bundles.
- Execution path: Reject symlink/nonregular manifest and artifact entries, validate resolved
containment and
required manifest fields, normalize reserved names before publication, and test concurrent/no-replace
publication semantics; declare process-crash versus power-loss durability explicitly.
- Acceptance gates: Regressions reject an external symlink with matching bytes, corrupt/malformed manifests,
missing identities and competing publication; valid bundles replay with stable fingerprints and
no overwrite; documented durability and memory bounds match implementation; make ci passes.
- Documentation target: `docs/impl/current/evaluation-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Implementation

The publisher and verifier now share an explicit local-tree policy. `bundle_layout.py` walks without
following links, refuses symlinks and nonregular files, opens artifacts with `O_NOFOLLOW`, and
checks that the opened path stays under the resolved bundle root. Artifact bytes are hashed in 1 MiB
chunks. `bundle_manifest.py` requires schema-version-1 identities, a canonical encoding, and hex
digests. `publish_run_bundle()` claims the destination with exclusive `mkdir` and replaces that
empty claim with the verified staging tree. `verify_run_bundle()` returns the manifest fingerprint.

Public failures are typed: `BundleExistsError`, `BundleLayoutError`, `BundleManifestError`, and
`BundleIntegrityError`. `manifest.json` and `scores.jsonl` are reserved after posix normalization.
Generic pipeline leases and lake publication were not added.

Process-crash durability: a crash before the claim leaves the destination absent (retry safe, with
possible leftover staging); a crash after `mkdir` and before replace leaves an empty destination
that blocks republish; a crash after replace leaves the verified tree. Power-loss durability is not
claimed: files are flushed, not fsynced.

Current state: [Evaluation foundation](../current/evaluation-foundation.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| External symlink with matching bytes | `tests/evaluation/test_bundle_layout.py::test_verification_rejects_an_external_symlink_with_matching_bytes` | pass; `BundleLayoutError` |
| Nonregular fifo and directory symlink | `test_verification_rejects_a_fifo_in_place_of_an_artifact`, `test_verification_rejects_a_symlinked_artifact_directory` | pass |
| Corrupt / unregistered files | `tests/evaluation/test_bundles.py::test_bundle_verification_detects_corruption_and_unregistered_files` | pass |
| Malformed and missing identities | `tests/evaluation/test_bundle_manifest.py` | pass; JSON, missing `run_id`, non-canonical encoding, invalid digest |
| Competing / no-replace publication | `test_bundle_never_overwrites_published_evidence`, `test_competing_publishers_leave_one_immutable_bundle`, destination-symlink refusal | pass; exactly one winner |
| Stable fingerprint replay | `test_valid_bundle_replays_with_a_stable_fingerprint` | pass |
| Chunked hashing | `test_chunked_artifact_digest_matches_the_full_payload` | pass; payload larger than 1 MiB |
| Synthetic DATA_DIR run | `$DATA_DIR/bundle-validation/0033/summary.json` | pass; fingerprint `5f8f0bf13c758098e61c38b3b90f2cb6e45e1b953c3bec9762a54dbfa246b58a`; symlink, missing identity, and overwrite refused. Fixture tree, not a provided-archive proof |
| Documented durability and memory bounds | [evaluation-foundation.md](../current/evaluation-foundation.md) | matches exclusive mkdir/replace, 1 MiB hash chunks, 1 MiB manifest cap, no fsync |
| Required CI | `make ci` | pass; 855 passed, 20 skipped; format, lint, typing, complexity, doc-links, spec-plan |

## Audit handoff

Incoming `AUD-codebase-05` resolved: a verified bundle cannot satisfy checksums by reading matching
bytes outside its tree; nonregular entries, containment, required identities, and no-replace
publication are tested. none identified as new notes.

## Close or resume

All required gates passed: deterministic layout/identity/concurrency regressions, synthetic
`$DATA_DIR/bundle-validation/0033/` evidence, documentation, `make lint-doc-links`,
`make lint-spec-plan`, and `make ci` (855 passed, 20 skipped). No gate is outstanding.
Next action: none for this task. Plan counts: 74 tasks before, 73 after (agent lane 64 to 63;
human 10 unchanged). Capabilities changed: none added or removed; `evaluation-foundation` remains
planned. Dependents now link this record. Next agent work:
`create-evaluation-fixtures-and-metrics`. No commit or push was made.
