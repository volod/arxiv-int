# Corpus Foundation Provided-Archive Proof

## Task and scope

- Id: `prove-corpus-foundation-on-provided-archive`; capability: `corpus-foundation`.
- State: accepted; current proof verification and all required gates pass.
- Source: `docs/impl/plan.md`; revision `5163ddd`; clean working tree at selection.
- Initial count: 62 tasks (52 agent, 10 human); selected as the next eligible agent task.
- Accepted task:

```markdown
#### prove-corpus-foundation-on-provided-archive

Run the completed corpus stages against the operator-provided archive and publish their first
current proof bundle.

- Serves: `corpus-foundation` --
[Provided-archive proof runs](../design/spec.md#provided-archive-proof-runs)
- Agent status: RUN NEEDED
- Dependencies: [Checkpoint 0063](records/0063-corpus-review-corpus-and-control-integrity.md);
[Normalization, dedupe and chunking](records/0062-corpus-implement-normalization-dedupe-and-chunking.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md);
[Evidence-based pipeline forecast](records/0044-pipeline-implement-evidence-based-pipeline-forecast.md);
[Evaluation fixtures and metrics](records/0036-eval-found-create-evaluation-fixtures-and-metrics.md);
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md).
- Audit inputs: [AUD-review-corpus-and-control-integrity-6](records/0063-corpus-review-corpus-and-control-integrity.md#audit-handoff);
[AUD-review-corpus-and-control-integrity-8](records/0063-corpus-review-corpus-and-control-integrity.md#audit-handoff);
[AUD-review-corpus-and-control-integrity-9](records/0063-corpus-review-corpus-and-control-integrity.md#audit-handoff).
- User-visible outcome: The supplied file silos have inspectable inventory, extraction,
normalization, duplicate, and chunk artifacts backed by one reproducible proof id.
- Scope boundary: Read `ARCHIVE_DIR` without mutation and stop after `chunk`; do not infer
downstream classification, retrieval, or knowledge quality from this proof.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification, `$RESULTS_DIR`, and
`$RESULTS_DIR/proofs/corpus-foundation/<proof-id>/`; only redacted summaries enter current docs.
- Execution path: Run a passing forecast; execute `inventory` through `chunk`; validate contracts,
counts, spans, offsets, quarantine reasons, and checksums; rerun the identical closure and capture
cache decisions plus resource/timing evidence.
- Acceptance gates: Every usable corpus stage is `passed` or contract-valid `empty`; every inventory
item is accounted for; artifacts and source anchors validate; the unchanged rerun executes no heavy
extraction/normalization work; failures keep the task open.
The bundle stays under the configured roots and nothing source-derived is committed or staged for
commit. Record the artifact roots and the bundle fingerprint so a reviewer can confirm presence,
checksums and contract conformance in place.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`, accepted as
[record 0063](records/0063-corpus-review-corpus-and-control-integrity.md).
```

- Amendments: user confirmed the configured roots and requested resolving access first, then
  executing the full task. A subsequent host check found both mounts available; no configuration
  or permission change was needed. The prior missing-root diagnostic is historical.

- Original execution note: the first attempt paused at unavailable host inputs. No reduced fixture
  substitute or different archive was used when work resumed.

## Implementation

The normal proof dispatcher now supports `corpus-foundation`. It consumes a frozen ordinary run
ending at `chunk`, checks current producer identities and every sealed dataset, reruns the same
closure with a fresh forecast, and refuses publication unless every stage is a validated cache hit
with zero worker invocations. `PROOF_ID` optionally names a new immutable proof over an existing
run; existing bundles are never overwritten. The checker repeats source, contract, accounting,
anchor, offset and checksum validation in place and rejects changed code, models or artifacts.

Modules under `evaluation/proof/corpus_*.py` separate publication, identity, artifact contracts,
accounting, source offsets and read-only verification. They reuse `publish_run_bundle`, the stage
registry and orchestrator, forecast guards, generated Pandera validators, snapshot checksum indexes,
source opening policy and quality evidence. Parquet data is read in batches; document text is
validated one document at a time. Identity/accounting sets remain proportional to occurrence count;
this bounded archive proof does not establish multi-terabyte memory behavior.

`pipeline/control/model_assets.py` hashes the names and bytes of actual Docling cache files.
`stage_identity` binds that digest into extraction's existing `model_fingerprint` before every
lookup, including cache checks. Changing or removing model bytes now invalidates extraction and its
descendants under unchanged CLI versions. No dependency, extraction threshold or grouping policy
changed. Mirrored tests include a failing-before model regression and positive/negative proof cases.
The real proof check exposed integer histogram keys that did not reproduce after JSON loading
when component sizes included both 2 and 10. Keys are now explicit strings, with a regression.
Resource evidence must contain finite nonnegative measurements and a completion sample for every
corpus stage; a present but empty or incomplete log cannot establish a pass.

The first host probe found the source/cache mount absent. After the user confirmed the configured
roots, a repeated host probe found both readable; no mount command, permission change or `.env` edit
was needed. CUDA access requires host execution outside this sandbox. Host: RTX 4060 Ti, 16380 MiB.
No archive writes, alternate input slice, downstream stages, commit or push were performed.
Current-state page: [corpus foundation](../current/corpus-foundation.md).

## Acceptance evidence

Run: `run-77943af6b23e4fb995907fe4c7f072bc`. Stage artifacts remain below `$RESULTS_DIR/normalized/`
and `$RESULTS_DIR/quarantine/`; run manifests and logs remain below `$RUNS_DIR/<run-id>/`.
Tool logs and regression evidence: `$DATA_DIR/corpus-proof/0068/`.
Current proof destination: `$RESULTS_DIR/proofs/corpus-foundation/0068-host-v2/`.
Fingerprint: `9cada31e97b846dd60508d05796ae894c1ff7216b86d85382ef4d0e080539c12`.
Read-only verification passed with the same fingerprint; `proof-check-v2.log` retains the result.
The final bundle checksums 2,667 external artifacts.

The earlier bundle under `$RESULTS_DIR/proofs/corpus-foundation/<run-id>/` is retained as historical
proof development evidence. Its fingerprint is
`b5869fe250c91ec8b3a4e0e4843a26703c4901142ce8ee011039873dd124333f`; it predates the final proof
checker and progress-history additions and is stale. Its `forecast-first.json` retains the original
cold-run forecast. The final bundle retains the entire original progress history plus replay logs.
Intermediate `0068-host`, fingerprint
`135e645b21bcd2889fd1f80a1dc4c77b17bccdf98f8fd2bad9201d61a4781c05`, is also historical: its
read-only verification exposed the histogram-key serialization defect fixed by the final version.
Both prior bundles remain untouched and now fail current-fingerprint validation.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Task selection | `make plan-status` | Pass; 62 tasks, requested task next eligible |
| Runtime inputs | Environment-loaded host path and mount probes | Pass after mounts became available; initial absence retained as historical diagnostic |
| CUDA host | `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader` outside sandbox | Pass; RTX 4060 Ti, 16380 MiB |
| Forecast | `make pipeline TO=chunk`; `forecast-first.json` | Pass; `degraded` conservative forecast permitted the bounded scope, not a resource refusal |
| All usable corpus stages | `make pipeline TO=chunk`; `pipeline-first.log`; producing `stage.json` and `quality.json` | Pass; inventory, extract, normalize, dedupe and chunk all succeeded/produced; `halted=false` |
| Aggregate exit | Same command's investigation finalizer | Exit 2 and `partial` because later investigation stages were intentionally excluded; not a corpus-stage failure or a full-profile completion claim |
| Inventory accounting | Proof source and occurrence checks | Pass; 546 physical files, 14,828,056,574 bytes, 568 occurrences including members; 447 mapped to 414 documents, 121 quarantined |
| Extraction and anchors | Generated document/span validators and proof span checks | Pass; 414 documents, 48,986 spans, all 414 documents anchored; 79 documents contain table cells |
| Normalization and offsets | Generated normalized-document validator; full canonical/search and offset-map replay | Pass; 414 normalized documents, zero normalization quarantines |
| Duplicate accounting | Generated membership checks and representative reconciliation | Pass; 87 groups, 252 memberships, 37 suppressed documents (8.94 percent); largest overall component 10; largest suppressing component 4 |
| Chunks and source offsets | Generated chunk checks and every-row source/canonical offset and repeated-header validation | Pass; 70,550 chunks from 377 retained documents; 1,885 table chunks, 68,665 text chunks; no chunk quarantines |
| Quarantine reasons | `accounting.quarantine` and retained extraction diagnostics | Pass; 65 unsupported-format, 23 input-size-limit, 24 empty-text, 2 encryption-marker, 7 all-extractors-failed |
| Failure inspection | Retained quarantine details | Six pixel-limit refusals and one OOXML parser exception; no evidence of a missing service or model cache. Parser failure remains explicit; no accuracy claim for unreadable material |
| Source integrity | Metadata snapshot checks plus post-run rehash of every hashed physical inventory occurrence | Pass; no observed source changes; changes reverted between observations remain undetectable |
| Unchanged rerun | `make proof CAPABILITY=corpus-foundation RUN_ID=<run-id> PROOF_ID=0068-host-v2` | Pass; every stage cached, zero workers, 1.23 seconds in final proof |
| Model content identity | `tests/pipeline/dag/test_model_identity.py`; `model-regression-before.log` | Regression failed before repair, passes after; changing same-length model bytes or removing weights changes extraction identity without changing inventory identity |
| Synthetic proof coverage | `make test PYTEST_ADDOPTS='-q tests/evaluation/proof/test_corpus_publish.py tests/evaluation/proof/test_corpus_validation.py tests/evaluation/proof/test_corpus_metrics.py tests/pipeline/dag/test_model_identity.py'` | Pass; 12 focused tests including normal publication/replay, valid-empty dedupe, corruption, stale models, accounting, suppression refusals, resource evidence and histogram replay |
| Baseline CI | `make ci` outside sandbox; `ci.log` | Pass before implementation; 1273 tests, 50 deselected |
| Final repository gate | `make format`; `make ci`; `ci-verified.log` | Pass; 1285 tests, 50 heavy tests deselected. Sandbox uv-cache refusal was resolved by host cache access; no gate was weakened |
| Read-only current proof | `arxiv-int evaluation proof check --proof-dir "$RESULTS_DIR/proofs/corpus-foundation/0068-host-v2"` | Pass; current fingerprints, source hashes, 2667 artifact checksums, contracts, resource samples and metrics reproduce |
| Documentation gates | `make lint-md`; `make lint-doc-links`; `make lint-spec-plan` | Pass after transition; zero Markdown, link or spec-plan findings |

## Audit handoff

New unresolved findings: none identified in the reviewed corpus/proof scope.

Incoming checkpoint 0063 notes, resolved for the declared corpus proof scope:

- Note 6: source reads are non-mutating and the archive was observationally quiescent. Frozen
  metadata matched before/after processing and all hashed physical sources matched inventory
  content digests. Host write permission remains acceptable under record 0023; no read-only mount
  or immunity from undetectable transient changes is claimed.
- Note 8: duplicate components and suppression share are measured above and in `report.json`.
  Every suppressing component has a retained representative. No component-bound policy change is
  justified by this slice's measured sizes. The reversible grouping overlay remains proposed;
  this is structural evidence, not human-adjudicated duplicate accuracy or placement approval.
- Note 9: actual Docling file contents now participate in extraction reuse. The proof records the
  aggregate model asset digest alongside each producer's owned model/tool/contract/code identities.
  The cache contained 66 files totaling 701,229,882 bytes; files were hashed without loading models.
  Aggregate asset digest: `c168625d72d9dbedcc31731d8645c1c6fde174c62357ff4ea943fbffda14d2ce`.

No additional out-of-scope repair identified. No database activation, classifier, retrieval, NLP,
knowledge, full-corpus scale, or physical-placement claim follows from this proof.

## Close or resume

Accepted. No required corpus gate remains unrun. The final proof, source hashes, resource samples,
contracts, offsets and cache replay passed; CI passed 1285 tests with 50 heavy tests excluded.
Measured original stage times were approximately 207 seconds inventory, 2753 seconds extraction,
21 seconds normalization, 25 seconds dedupe and 4 seconds chunking. Progress samples recorded at
least 100.92 GiB available host RAM during extraction. These are observed wall times and sampled
host resources, not process peak memory, CUDA capacity or full-corpus throughput guarantees.

Updated corpus/evaluation current-state pages, runtime/control links, record indexes and incoming
checkpoint dispositions. The corpus registry evaluation now explicitly describes synthetic corpus
checks and the provided-archive structural proof, consistent with record 0023's approved removal of
item-level gold adjudication from slice acceptance. Held-out quality and human promotion requirements
in the specification remain unchanged; this task does not claim real gold accuracy.

Plan counts: 62 before (52 agent, 10 human), 61 after (51 agent, 10 human). Removed only this
satisfied task. Corpus foundation is shipped for this integrity scope. The next eligible agent task
is `build-paradedb-lexical-load-and-query-path`; no human task is currently eligible. Dependent work
was not started. No human review packet is required for this task.

No services were started; extraction subprocesses and proof/test processes completed. All evidence
is retained under configured tool/run/result roots. No private source content was added or staged,
and no commit or push was made.
