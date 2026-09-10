# Task Record

## Task and scope

- Id / capability / checkpoint: `retire-committed-proof-export` / `evaluation-foundation` /
`review-corpus-and-control-integrity`
- State: accepted
- Source: `docs/impl/plan.md` section `retire-committed-proof-export`; code revision `1efc059`,
clean working tree at start.
- Accepted task:

```markdown
#### retire-committed-proof-export

Remove the Git-bound proof export path so no archive-derived artifact can be prepared for a commit.

- Serves: `evaluation-foundation` --
[Published proof and evaluation data](../design/spec.md#published-proof-and-evaluation-data)
- Agent status: CLEAR
- Dependencies: [Committed proof identity obfuscation](records/0035-eval-found-implement-committed-proof-identity-obfuscation.md);
[Inference and evaluation checkpoint](records/0038-eval-found-review-inference-and-evaluation-boundaries.md);
[Pipeline-control re-proof](records/0056-pipeline-reprove-pipeline-control-after-reconciliation-repair.md).
- User-visible outcome: No command, packaged policy or Make target can turn source-derived proof
data into repository files; a proof bundle stays under the configured roots and a reviewer validates
it there.
- Scope boundary: Remove the export path, its packaged identity policy and the bundle fields that
exist only to describe an export; keep everything a proof records about artifacts, checksums, gates
and fingerprints, and keep every secret, path and leak rule that is independent of it. Do not touch
synthetic test fixtures and do not change where proofs are written.
- Data and artifact paths: `src/arxiv_int/evaluation/export/`, `src/arxiv_int/evaluation/cli.py`,
`src/arxiv_int/evaluation/proof/`, `src/arxiv_int/resources/configs/evaluation/proof-identity-policy.json`,
`make/eval.mk`, `tests/evaluation/export/`, `docs/impl/current/evaluation-foundation.md`, and
`docs/guide/development.md`.
- Execution path: Delete the exporter package, its policy asset, the `evaluation export-proof` and
`evaluation identity-policy` commands and the `proof-export` and `identity-policy-check` targets,
and drop that check from `ci-checks`; remove `export.json`, the transformed-fingerprint half of
`policy.json` and the `git_bound` field from published bundles while keeping the bundle's own raw
fingerprint and verdict; delete the export tests and any fixture that only served them; rewrite the
affected current-state sections to describe in-place review against the configured roots.
- Acceptance gates: No module, command, Make target, packaged asset, test or document references a
Git-bound export or an identity-obfuscation policy; a published bundle still records artifacts,
checksums, gates and its fingerprint and still passes `evaluation proof check`; the removed CI check
leaves `make ci` green without weakening a remaining gate; a repository scan finds no
archive-derived file. Record the superseded bundle shape rather than rewriting accepted records.
- Documentation target: `docs/impl/current/evaluation-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

- Amendments: none.

## Implementation

Deleted `src/arxiv_int/evaluation/export/` (catalog, checks, commands, errors, exporter, io, map,
normalize, paths, policy, receipt, render, rewrite) and the packaged asset
`src/arxiv_int/resources/configs/evaluation/proof-identity-policy.json`. No substitute exists: there
is no command, Make target or packaged asset that turns source-derived proof data into repository
files.

Commands and targets. `src/arxiv_int/evaluation/cli.py` now registers only the `evaluate`,
`fixtures` and `proof` subcommands; `export-proof` and `identity-policy` are gone, along with
`parse_export_maps()`. `src/arxiv_int/cli.py` dispatches `evaluation` straight to
`evaluate.commands.run_evaluate_cli` (the deleted `export.commands.run_evaluation_command` was only
a wrapper that chose between export and evaluate). `make/eval.mk` loses `proof-export` and
`identity-policy-check`; `make/quality.mk` drops `identity-policy-check` from `ci-checks`.
`evaluation-fixtures-check`, `eval` and `proof` are unchanged.

Bundle shape. Both publishers now write a `fingerprint.json` holding `data_class` and the
`raw_fingerprint` of their own `proof-manifest.json` bytes, produced by the shared
`fingerprint_document()` in `proof/ops.py`. The pipeline-control publisher writes the control
scenario to its own `scenario.json` instead of nesting it inside an export document.

Superseded shape, for reviewers holding an older bundle (records 0035, 0053, 0056 keep their own
accounts and were not rewritten):

| Old file / field | Now |
| --- | --- |
| `export.json` `git_bound: []`, `result: "no-export"`, `policy_id` | removed |
| `export.json` `scenario` | `scenario.json` (same payload, unwrapped) |
| `policy.json` `data_class`, `policy_id`, `policy_fingerprint`, `transformed_fingerprint` | removed |
| `policy.json` `raw_fingerprint` | `fingerprint.json` `raw_fingerprint` (same value) |
| manifest validator `identity-export` | removed from the registry and from published manifests |
| gate `no_export` (a hardcoded `"pass"`) | removed from `GATE_NAMES` |

`proof/model.py` drops `VALIDATOR_EXPORT`, so `evaluation-foundation` now requires
`evaluation-bundle`, `split-leakage` and `item-ledger`; `src/arxiv_int/resources/configs/proofs/capabilities.json`
was regenerated through `arxiv-int evaluation proof generate-registry` and stays drift-checked by
`make evaluation-fixtures-check`. `control_gates.py` drops `no_export`, leaving 13 gates that are
all computed from the report rather than asserted.

Kept unchanged: every artifact/checksum/stage/validator record in `proof-manifest.json`, the
verdict, `gates.json`, `forecast-summary.json`, `summary.txt`, and every leak rule in
`proof/checks.py` -- configured-root substitution, private path markers, synthetic identity tokens,
the `identities.json` refusal, and the proof-tree walk. Those rules never depended on the exporter;
only three docstrings and one comment that described them as "Git-bound" were reworded. Synthetic
fixtures under `tests/fixtures/evaluation/` were not touched, and proof destinations are unchanged.

Tests: deleted `tests/evaluation/export/` (7 modules and their support file, all exporter-only).
`tests/evaluation/test_boundary_review.py` loses `test_exported_ontology_and_geotemporal_meanings_survive`
-- its ontology/geotemporal assertions are already covered by
`tests/evaluation/scoring/test_scoring.py` -- and gains
`test_no_command_or_asset_can_export_proof_data_into_the_repository`, which asserts both retired
commands exit, the packaged policy asset is absent, the published bundle is exactly
`fingerprint.json` + `proof-manifest.json` + `summary.txt` with a matching raw fingerprint and no
`identity-export` validator, and that `check_capability_proof()` still passes.
`tests/evaluation/proof/test_pipeline_control.py` asserts the absence of `export.json`/`policy.json`
and reads the scenario counts and raw fingerprint from their new files.

Documentation: `docs/impl/current/evaluation-foundation.md` replaces the "Git-bound identity export"
section with "Published proof bundles", describing in-place review against `RESULTS_DIR`.
`docs/impl/current/pipeline-control.md` describes the new bundle contents and names the superseded
shape. `docs/impl/current/governance.md` and `docs/impl/current/developer-tooling.md` drop the
pending-removal note and the retired CI check. `docs/guide/development.md` drops both target rows.
`docs/design/spec.md` line 313 listed `export` among the `evaluation/` subpackages; that structural
listing was corrected to match the section it already contained
([published proof and evaluation data](../../design/spec.md#published-proof-and-evaluation-data)),
which states there is no sanctioned export path. No other specification text changed.

Current-state page: [evaluation foundation](../current/evaluation-foundation.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| No module, command, target, asset, test or doc references a Git-bound export or identity policy | `git grep -nI -e export-proof -e identity-policy -e git_bound -e proof-identity -e export_proof_bundle -e identity-export -e no_export -e proof-export -- . ':!docs/impl/records'` | pass; only removal-history prose in three current-state pages and the retirement regression test remain. Accepted records 0035/0036/0038/0050/0051/0053/0056 keep their historical text by design |
| Retired commands and asset are gone | `tests/evaluation/test_boundary_review.py::test_no_command_or_asset_can_export_proof_data_into_the_repository` | pass; both argv forms exit, `configs/evaluation/proof-identity-policy.json` absent |
| Retired targets are gone | `make help` | pass; Evaluation section lists only `evaluation-fixtures-check`, `eval`, `proof` |
| Packaged distribution ships no exporter or policy | `make build`; wheel listing of `arxiv_int/resources/configs/` and `arxiv_int/evaluation/` | pass; sdist and wheel built; no `evaluation/export/`, no `proof-identity-policy.json` |
| Bundle still records artifacts, checksums, gates and its fingerprint | `arxiv-int evaluation proof publish --capability evaluation-foundation --run-id 0057-eval`; `--capability pipeline-control --run-id 0057-ctl` | pass; fixtures bundle `fingerprint.json`/`proof-manifest.json`/`summary.txt`; control bundle adds `gates.json` (13/13 `pass`), `scenario.json`, `forecast-summary.json`; control manifest carries 2 artifact checksums and verdict `adopt` |
| Bundle still passes `evaluation proof check` | `arxiv-int evaluation proof check --proof-dir <each bundle>` | pass; fixtures raw fingerprint `c5303e858e7921d6ca9835b44d02a14e9b2d763aeee1038a958fa6b8a5ad7ff7`; control raw fingerprint `f3e4d73a88215ac0c11a713ee910f7ff188e615baf7e01a202773c966b87a5a6`; each equals its bundle's `fingerprint.json` `raw_fingerprint`. Synthetic fixture tree and a two-file disposable archive, not a provided-archive proof |
| Removed CI check leaves `make ci` green without weakening a remaining gate | `make ci` | pass; 1114 passed, 50 deselected in 112.73s; format, lint, typing (413 files), complexity, shell, doc-links, spec-plan, contracts generation and evolution, `db-check` at head `0001`, ontology (35 classes / 30 predicates), inference schemas, evaluation-fixtures-check. Only `identity-policy-check` was dropped; `evaluate_gates()` kept every gate it actually computes and lost only the hardcoded `no_export: "pass"` |
| Repository scan finds no archive-derived file | `git grep -nI -e /home/ -e /mnt/ -e /Users/`; `git status` | pass; every hit is a leak-rule marker or a synthetic redaction test, and the tree carries no proof, gold or archive artifact. See audit note AUD-retire-committed-proof-export-1 |
| Formatting and documentation checks | `make format`; `make lint-doc-links`; `make lint-spec-plan` (both rerun after the record and its audit routing); `make lint-md` | format and doc-links/spec-plan pass (0 broken links, 0 findings); `lint-md` reports 23 MD013 line-length findings, byte-identical to the pre-change baseline measured with `git stash` -- all in sections this task did not edit |

Evidence trees: `$DATA_DIR/evaluation/0057/results/proofs/evaluation-foundation/0057-eval/` and
`$DATA_DIR/evaluation/0057/results/proofs/pipeline-control/0057-ctl/`. Fixture and disposable-archive
coverage does not prove real-archive quality.

## Audit handoff

| Note | Finding / owner / disposition |
| --- | --- |
| `AUD-retire-committed-proof-export-1` | Nonblocking. The required repository scan surfaced a hardcoded operator home path in two synthetic redaction tests: `tests/inspect/test_summarize.py` and `tests/observability/logging/test_redact.py` each embed a literal operator home path as the string the redactor must remove. The invariant "never hardcode machine-specific paths in tests" is violated even though no archive content leaks and both assertions are correct; a generic literal such as `/home/operator/...` proves the same rule. Predates this task and lies outside its scope boundary. Next check: replace both literals and confirm each assertion still fails when the redactor is disabled. [Owner review-corpus-and-control-integrity](0063-corpus-review-corpus-and-control-integrity.md). Disposition: resolved. Both literals now read `/home/operator/archive/doc.pdf`, and each assertion still fails when path redaction is removed; the finding text above no longer quotes the original operator path. |

Reviewed scope: `src/arxiv_int/evaluation/`, `src/arxiv_int/cli.py`, `make/eval.mk`,
`make/quality.mk`, `src/arxiv_int/resources/configs/`, `tests/evaluation/`, and the five affected
documentation pages.

## Close or resume

All acceptance gates pass; none remain. Next action: none for this task; the next unblocked agent
task is `bind-real-owned-stage-fingerprints` under `pipeline-control`.

Updates: `docs/impl/current/evaluation-foundation.md` (documentation target),
`docs/impl/current/pipeline-control.md`, `docs/impl/current/governance.md`,
`docs/impl/current/developer-tooling.md`, `docs/guide/development.md`, `docs/design/spec.md`
subpackage listing, and `docs/impl/records/README.md` index. The plan's
`retire-committed-proof-export` section was removed and its
`### Evaluation foundation -- evaluation-foundation` heading with it, since it held no other task;
no other plan task referenced this one, so no dangling links needed replacing. The
`review-corpus-and-control-integrity` checkpoint gained one `Audit inputs:` entry routing
`AUD-retire-committed-proof-export-1` to it; no other plan text changed.

Plan counts: 69 tasks before (agent 59, CLEAR 22), 68 after (agent 58, CLEAR 21); human lane
unchanged at 10, `next human: blocked`.

Capabilities changed: `evaluation-foundation` loses the Git-bound proof export and its packaged
identity policy, and both proof publishers move to the `fingerprint.json` / `scenario.json` bundle
shape. No `Human review handoff` applies to this task.
