# Provided-Archive Classification Proof

## Task and scope

- Id / capability / checkpoint: `prove-archive-classification-on-provided-archive` /
  `archive-classification` / `review-investigation-and-report-integrity`
- State: active.
- Source: `docs/impl/plan.md` at `4a6edbb`; clean worktree at task start.
- Initial plan count: 73 tasks (60 agent, 13 human); this task is the next eligible agent task.
- Accepted task:

```markdown
#### prove-archive-classification-on-provided-archive

Classify the supplied archive and validate its complete hierarchical mapping and source references.

- Serves: `archive-classification` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies:
[Hierarchical file classification](records/0079-archive-cls-implement-hierarchical-file-classification.md);
[Pipeline-control provided-archive proof](records/0053-pipeline-prove-pipeline-control-on-provided-archive.md);
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md).
[Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md);
[Retrieval and classification boundaries checkpoint](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md);
[Retrieval and classification identity repair](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md).
- Audit inputs: [AUD-review-retrieval-and-classification-boundaries-8](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff);
[AUD-review-retrieval-and-classification-boundaries-9](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff);
[AUD-repair-retrieval-and-classification-identity-and-evidence-1](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md#audit-handoff);
[AUD-repair-retrieval-and-classification-identity-and-evidence-2](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md#audit-handoff).
- Human review handoff:
[approve-classification-operating-point](#approve-classification-operating-point)
final errors, calibration, coverage and operating-point decision packet.
Packet: `$RUNS_DIR/<run-id>/review/classification/`.
Ready after this proof passes.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`
and `approve-archive-organization-plan`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept/revise the thresholds and exceptional outcomes, or retain unclassified.
- User-visible outcome: Every supplied file has a subject-taxonomy or explicit exceptional result,
with hierarchy, confidence, evidence/failure reasons, and initial source lookup.
- Scope boundary: Run classification and source-manifest validation only; archive placement and its dry-run
are accepted independently under `archive-organization`.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/classifications/`, and
`$RUNS_DIR/<run-id>/classification/`, plus test logs below
`$DATA_DIR/integration/archive-classification/`.
- Execution path: Forecast the closure; classify and validate coverage, hierarchy, evidence, exceptions,
fingerprints, and physical/virtual source accounting; rerun unchanged and record cache hits.
- Acceptance gates: Every physical inventory item has one complete result; virtual members retain container
links; source references and calibration metrics validate; supplied bytes remain unchanged; the
identical rerun invokes no heavy classifier; ordinary artifact manifests and checksums are complete.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-investigation-and-report-integrity`.
```

- Amendments: The execution path now names its integration check and makes the existing
  held-out calibration gate explicit when reviewed archive labels are missing. This clarifies
  evidence/readiness handling without changing the classification or placement scope. The full
  revised task follows; the original block above remains verbatim.

```markdown
#### prove-archive-classification-on-provided-archive

Classify the supplied archive and validate its complete hierarchical mapping and source references.

- Serves: `archive-classification` --
[Provided-archive integration runs](../design/spec.md#provided-archive-integration-runs)
- Agent status: RUN NEEDED
- Dependencies:
[Hierarchical file classification](records/0079-archive-cls-implement-hierarchical-file-classification.md);
[Pipeline-control provided-archive proof](records/0053-pipeline-prove-pipeline-control-on-provided-archive.md);
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md).
[Evidence and source location lookup](records/0051-pipeline-implement-evidence-and-source-location-lookup.md);
[Retrieval and classification boundaries checkpoint](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md);
[Retrieval and classification identity repair](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md).
- Audit inputs: [AUD-review-retrieval-and-classification-boundaries-8](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff);
[AUD-review-retrieval-and-classification-boundaries-9](records/0080-archive-cls-review-retrieval-and-classification-boundaries.md#audit-handoff);
[AUD-repair-retrieval-and-classification-identity-and-evidence-1](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md#audit-handoff);
[AUD-repair-retrieval-and-classification-identity-and-evidence-2](records/0081-archive-cls-repair-retrieval-and-classification-identity-and-evidence.md#audit-handoff).
- Human review handoff:
[approve-classification-operating-point](#approve-classification-operating-point)
final errors, calibration, coverage and operating-point decision packet.
Packet: `$RUNS_DIR/<run-id>/review/classification/`.
Ready after this proof passes.
Blocked consumer:
`publish-provided-archive-end-to-end-proof`
and `approve-archive-organization-plan`.
Report readiness using the human-handoff workflow; never self-approve.
Decision: accept/revise the thresholds and exceptional outcomes, or retain unclassified.
- User-visible outcome: Every supplied file has a subject-taxonomy or explicit exceptional result,
with hierarchy, confidence, evidence/failure reasons, and initial source lookup.
- Scope boundary: Run classification and source-manifest validation only; archive placement and its dry-run
are accepted independently under `archive-organization`.
- Data and artifact paths: `$ARCHIVE_DIR` used without modification,
`$RESULTS_DIR/normalized/classifications/`, and
`$RUNS_DIR/<run-id>/classification/`, plus test logs below
`$DATA_DIR/integration/archive-classification/`.
- Execution path: Forecast the closure; classify and validate coverage, hierarchy, evidence, exceptions,
fingerprints, and physical/virtual source accounting with the in-place check under
`tests/integration/classification/`; rerun unchanged and record cache hits. Score a frozen held-out
set of reviewed archive labels for calibration, or leave this gate and packet readiness open when
those labels are unavailable.
- Acceptance gates: Every physical inventory item has one complete result; virtual members retain container
links; source references and calibration metrics validate; supplied bytes remain unchanged; the
identical rerun invokes no heavy classifier; ordinary artifact manifests and checksums are complete.
Only ordinary pipeline artifacts stay under configured roots; nothing source-derived is committed
or staged for commit. Record the run id, artifact roots, manifests, and checksums checked in place.
- Documentation target: `docs/impl/current/archive-classification.md`
- Review checkpoint: `review-investigation-and-report-integrity`.
```

The operator then added this full scope amendment while the task remained active:

<!-- pyml disable MD013 -->

```text
a) The operating-point packet ($RUNS_DIR/<run-id>/review/classification/operating-point.json) has encoded data like "term": "\u0434\u0430\u043d\u043d\u044b\u0445". Provide a user-friendly make command to interactively accept or revise thresholds and exceptional outcomes, or retain unclassified.
b) Provide a user-friendly make command to generate an archive gold label and an interactive review of the archive gold-label JSONL to complete calibration;
```

<!-- pyml enable MD013 -->

The quoted packet path is root-normalized to avoid committing a machine-specific mount path;
the requested behavior and sample encoded term are otherwise retained.

The resulting behavior is specified in the classification section of `docs/design/spec.md` and
added to the task's execution path in `docs/impl/plan.md`. The terminal review must decode Unicode,
show bounded source context, write only explicitly confirmed gold labels, resume without replacing
confirmed rows, freeze and score the held-out set, and record a fingerprint-bound decision without
silently editing policy or authorizing placement. Acceptance remains gated by passing calibration.

The user explicitly requests implementation, execution and fixes on this CUDA host, followed by
documentation and plan updates. Human approval remains a separate task.

## Implementation

Reuse the ordinary DAG, forecast, immutable lake validators, classification evaluator and source
resolver. Add archive cross-checks only under `tests/integration/`; fix task-owned findings in
`classification/stage.py` and mirrored tests. The stale-snapshot regression failed before the fix;
the stage now names differing fingerprints and fresh-run recovery commands.

Synthetic container integration exposed a source-lookup boundary failure: inventory encodes member
addresses as nested JSON strings containing positions and names, while the resolver treated the
encoded string as a plain relative path. It also compared a member content hash against physical
container bytes. Regressions in `tests/query/evidence/test_inventory_members.py` failed first.
`query/evidence/members.py`, `schema.py` and `resolve.py` now validate the inventory encoding, retain
legacy member names, and resolve the physical checksum from a container in the same snapshot while
preserving the member content identity. Missing container checksums remain explicitly unchecked.
This repairs the task's existing source-reference acceptance boundary; it introduces no new
contract, classifier, taxonomy, dependency or placement behavior.

The cache audit found that the shared DAG validated the classify attempt but omitted its external
snapshot from the reuse validators. A failing tampering regression preceded
`classification/reuse.py` and its registration in `pipeline/dag/execute.py`. The validator now
rehashes the complete mapping/scheme snapshot, checks both generation ids and physical-row totals,
and refuses drift before claiming a cache hit. This shared executor edit changes stage-owned code
fingerprints, so the initial interrupted host run cannot supply current archive acceptance.

The integration checks separately validate integrity and calibration. Calibration requires a
checksummed held-out report and frozen label ledger, matching scheme and mapping identities,
actual-content split separation and reproducible metrics. Missing labels fail this gate.
Current state:
[archive classification](../current/archive-classification.md).

Operator feedback led to `classification/review_terminal.py` and
`classification/gold_terminal.py`, backed by `gold_interaction.py` and `review_material.py`.
The first shows decoded packet
evidence, captions, thresholds, outcomes and metrics, refuses premature acceptance, and writes one
exclusive decision tied to the packet, mapping, scheme, classifier and evaluation. The second
interleaves sealed mapping strata, shows bounded decoded previews, stores only human-confirmed
labels in a resumable run-scoped JSONL, then freezes/scores on explicit request. The Make wrappers
are `classification-operating-review` and `classification-calibrate`; neither synthesizes gold or
approves a policy on its own. The archive integration packet now also keeps negative measured
quality gates in `pending` instead of showing ready.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Prerequisites | `make plan-status`; records 0023, 0051, 0053, 0079, 0080 and 0081 | pass; authorized representative slice, no reviewed archive gold established by 0023 |
| CUDA host | `nvidia-smi` outside sandbox | pass; RTX 4060 Ti, 16380 MiB, driver 595.84, CUDA 13.2; CPU classifier selected by existing policy |
| Configured roots | Environment root existence checks and `lsblk` | old mount paths absent after reboot; matching devices remounted with suffixed mount names and ignored `.env` updated; configured source stayed read-only |
| Ordinary closure | `make pipeline TO=classify`; run `run-bf2bfde7672841eb89324c4844f9d436` | preflight, inventory, extract, normalize and classify all sealed succeeded; 568 inventory occurrences, 414 documents, 48,985 extraction spans, 546 physical classifications. Wrapper exit 2 is the expected `partial` whole-profile finalization for a `TO=classify` prefix, not a failed stage. Log: `$DATA_DIR/integration/archive-classification/0082/pipeline-final.log`. |
| Archive integrity | `ARCHIVE_CLASSIFICATION_RUN_ID=<run-id> pytest tests/integration/classification/test_archive_classification.py::test_provided_archive_classification_integrity_and_noop_replay -q` | pass; all 546 physical rows, 22 member links, 414 source-resolved documents, 9 member locations, 695 evidence spans and all physical source bytes checked. 5/5 cache hits; zero workers on unchanged replay. Report: `$DATA_DIR/integration/archive-classification/<run-id>/integrity.json`. |
| Mapping identity | `classify.json` under `$RESULTS_DIR/normalized/classification/contract_version=1.0.0/generation_id=<run-id>/snapshot=c4ffe10cb5f941dfa15dad77f336a466/` | SHA-256 `0ab41dac059d29efd75f2418423d55cadb2ceb4e24bbb80b2fe0311b8e937ce5`; upstream, classes, mapping, generation, contracts, quality evidence and attempt checksums validated in place. |
| Outcomes and resources | Sealed manifest and integrity report | 7 taxonomy, 431 unclassified, 108 unreadable; 25 files truncated by the declared text budget. 76.99 files/s >= 20 required; 317.09 MiB <= 512 required. These are completeness/cost measurements, not semantic accuracy. |
| Held-out calibration | `ARCHIVE_CLASSIFICATION_RUN_ID=<run-id> pytest tests/integration/classification/test_archive_classification.py::test_provided_archive_classification_calibration -q` | fails as required: no independently reviewed archive labels or matching held-out evaluation report. Packet readiness `pending`; acceptance open. |
| Snapshot diagnostics | `pytest tests/classification/test_snapshot_diagnostics.py -q` | failed before fix, passed after; existing snapshot bytes retained |
| Source lookup repair | `pytest tests/query/evidence tests/classification/test_archive_checks.py -q` | pass after reproducing JSON-address failure; nested member/container identities remain distinct |
| Classification cache reuse | `pytest tests/classification/test_reuse_validation.py -q` | failed before implementation; passed after. Parquet tampering and generation mismatch are refused before reuse. |
| Focused deterministic suite | `pytest tests/classification tests/query/evidence -q` | 116 passed |
| Required CI | `make ci` outside the sandbox | 1457 passed, 59 deselected on final implementation. An earlier run had one concurrent timing failure in `test_second_acquirer_waits_then_succeeds`; it passed alone and on rerun. |
| Required quality | `make quality` outside the sandbox | pass; 1457 passed, 59 deselected, 85% diagnostic total coverage; contracts, Markdown links and package builds passed. Coverage is not an acceptance gate. |
| Terminal reviews | `pytest tests/classification/test_operator_review.py tests/classification/test_archive_calibration.py -q` | 11 passed; Unicode presentation, explicit label confirmation/resume, frozen scoring, decision identity and non-overwrite, pending refusal. No real human label or decision was entered. |
| Intermediate terminal-code archive closure | `make pipeline TO=classify`; run `run-5d8677795cef400b979c00f584da5f1e` | selected stages sealed; upstream stages were cache hits and classification rebuilt in 7.01 s, 77.87 files/s, 218.46 MiB. Wrapper exit 2 is expected prefix `partial`. A later terminal prompt refactor changed the classification-package fingerprint, so this is not the final-code mapping. Log: `$DATA_DIR/integration/archive-classification/0082/operator-review-pipeline.log`. |
| Intermediate archive integrity | `ARCHIVE_CLASSIFICATION_RUN_ID=run-5d8677795cef400b979c00f584da5f1e pytest tests/integration/classification/test_archive_classification.py::test_provided_archive_classification_integrity_and_noop_replay -q` | pass at the then-current fingerprint; 546 physical, 22 virtual, 414 resolved documents, 9 member locations, 695 evidence spans, complete source rehash, 5/5 cache hits and zero replay workers. Mapping SHA-256 `b271a4366b1d8debfee8ab46a6adbde3291c5ecc1833a21897893a43373a2741`. |
| Live terminal smoke | `make classification-operating-review RUN_ID=run-5d8677795cef400b979c00f584da5f1e`; `q` | pass; decoded Cyrillic captions, paths and the packet's formerly escaped `данных` term rendered legibly. Prompt reported pending calibration; quit recorded no decision. |
| Follow-up CI | `make ci` outside the sandbox after terminal review refactor | pass; 1464 passed, 59 archive-marked deselected. Formatting, typing, complexity, contracts and standard tests passed. |
| Follow-up quality | `make quality` outside the sandbox after terminal review refactor | pass; 1464 passed, 59 archive-marked deselected, 85% diagnostic coverage; Markdown, contracts, source and wheel builds passed. Coverage is not an acceptance gate. |
| Final-code archive closure | `make pipeline TO=classify`; run `run-0f7aac31db6b4e9c93eda26d8c7e0ffd` | selected stages sealed; upstream cache hits, classification rebuilt in 6.99 s, 78.09 files/s, 218.89 MiB. Wrapper exit 2 is expected prefix `partial`. Log: `$DATA_DIR/integration/archive-classification/0082/operator-review-final-pipeline.log`. |
| Final-code archive integrity | `ARCHIVE_CLASSIFICATION_RUN_ID=run-0f7aac31db6b4e9c93eda26d8c7e0ffd pytest tests/integration/classification/test_archive_classification.py::test_provided_archive_classification_integrity_and_noop_replay -q` | pass; 546 physical, 22 virtual, 414 resolved documents, 9 member locations, 695 evidence spans, complete source rehash, 5/5 cache hits, zero workers. Mapping SHA-256 `f27d8a01e1c5adfcd6f2050f353e9756c795aef07c00a411d72f64a4418ba1a5`; packet pending human labels. |
| Final-code calibration | `ARCHIVE_CLASSIFICATION_RUN_ID=run-0f7aac31db6b4e9c93eda26d8c7e0ffd pytest tests/integration/classification/test_archive_classification.py::test_provided_archive_classification_calibration -q` | fails as required: independently reviewed archive labels and matching held-out report are absent. This is the open task gate, not a mechanical integrity failure. |
| Gold Make pause/resume smoke | `make classification-calibrate RUN_ID=run-0f7aac31db6b4e9c93eda26d8c7e0ffd LABEL_SET=archive-gold-review LIMIT=40`; `q`; rerun and `q` | pass; decoded bounded preview and proposal shown, empty mapping-bound JSONL draft created, second invocation resumed, and intentional pauses exited zero without running the calibration gate. No row was confirmed. |
| Final Make-change CI | `make ci` after the clean-pause wrapper change | Initial run: 1463 passed, 59 deselected, one timing failure in unrelated `test_second_acquirer_waits_then_succeeds` (waiter missed the 2-second join). It passed immediately in isolation; full rerun passed 1464 tests, 59 deselected. |
| Final Make-change quality | `make quality` after the clean-pause wrapper change | pass; 1464 passed, 59 deselected, 85% diagnostic coverage, zero broken links/spec-plan findings, source/wheel builds passed. Log: `$DATA_DIR/integration/archive-classification/0082/operator-review-final-quality.log`. Coverage is not an acceptance gate. |

## Audit handoff

| Incoming note | Disposition and evidence |
| --- | --- |
| `AUD-review-retrieval-and-classification-boundaries-8` | Fixed stale-snapshot refusal to report each differing fingerprint and fresh-run recovery command; failing-before/passing-after regression. No stale scheme was silently reused in the archive run. Disposition: resolved. Owner: [this task](../plan.md#prove-archive-classification-on-provided-archive). |
| `AUD-review-retrieval-and-classification-boundaries-9` | Validated the declared evidence shape and source/document join for all 695 emitted archive spans, including normalized-search, path and title spaces. An additive ODCS shape revision is not needed for this proof: the existing string remains an extensible serialized payload, with strict consumer-boundary validation here. Reconsider if an external contract consumer needs column-level enforcement. Disposition: resolved. Owner: [this task](../plan.md#prove-archive-classification-on-provided-archive). |
| `AUD-repair-retrieval-and-classification-identity-and-evidence-1` | Double scoring remains, but measured 76.99 files/s against the predeclared 20 files/s minimum. No cost-driven change justified for this archive. Disposition: resolved. Owner: [this task](../plan.md#prove-archive-classification-on-provided-archive). |
| `AUD-repair-retrieval-and-classification-identity-and-evidence-2` | Measured 317.09 MiB peak memory against the 512 MiB gate. No memory refactor justified for this archive. Disposition: resolved. Owner: [this task](../plan.md#prove-archive-classification-on-provided-archive). |

Self-review also found two task-owned boundary defects before the first proof run: JSON-encoded member
source lookup and external snapshot reuse validation. Both have failing-before regressions and
focused repairs. The archive integration checker itself needed corrections for shard-bound producer
identity, the inventory pointer's extra `scan_id`, cross-run inventory producer identity and
relative `DATA_DIR` resolution; after those
test-only corrections, every integrity assertion and unchanged replay passed. No source-derived
file was committed or staged. No broader classifier, threshold, taxonomy or placement change was
made.

## Close or resume

Local root references were corrected in ignored `.env` for the devices' new mount names, and
scratch moved off the source device. Inherited environment variables can override `.env`, so the
declared host command clears the five task-specific root overrides before loading configuration.
No source or existing artifact was moved or edited.

The forecast allowed ordinary `make pipeline TO=classify` run
`run-3ef0bb96851f48d89c21db2d0bdcb8da`. Pipeline output is retained at
`$DATA_DIR/integration/archive-classification/0082/pipeline.log`. Inventory sealed; the computer
restarted during extraction, leaving no sealed extraction or completed status. No old attempt was
promoted or removed. Automatic review briefly refused process inspection due a tool usage limit;
the user then confirmed the restart and model change. After remounting the source SSD, the task
started a fresh forecasted closure, `run-bf2bfde7672841eb89324c4844f9d436`, with final-code
fingerprints; its log is
`$DATA_DIR/integration/archive-classification/0082/pipeline-final.log`.

Retained run directories contain no frozen classification labels or classification quality reports.
The user was asked for any separately available reviewed labels while independent work continued.
The new run completed all selected stages and the integrity gate; the review packet is
`$RUNS_DIR/run-bf2bfde7672841eb89324c4844f9d436/review/classification/operating-point.json`,
bound to mapping digest `0ab41dac059d29efd75f2418423d55cadb2ceb4e24bbb80b2fe0311b8e937ce5`.
It includes five assigned, five near-threshold, five ambiguous and five unreadable inspection
cases without declaring any gold answer. Readiness is `pending-reviewed-labels`; the operator can
inspect the taxonomy with
`make classification-tree RUN_ID=run-bf2bfde7672841eb89324c4844f9d436`, then inspect the
packet and independently review a held-out archive label set. Freeze it with
`make classification-labels RUN_ID=<run-id> LABELS=<operator-gold.jsonl> LABEL_SET=<id>` and
evaluate the sealed mapping with `make classification-evaluate RUN_ID=<run-id>
CLASSIFICATION=<classify.json> LABELS=<frozen-labels.jsonl> LABEL_SET=<id> SPLIT=test`; rerun the
archive calibration check afterward. If measured gates fail, investigate and revise the policy
under its declared review process; do not treat fixture metrics as substitute evidence.

After the terminal-review refactor, the final-code run is
`run-0f7aac31db6b4e9c93eda26d8c7e0ffd`, bound to mapping digest
`f27d8a01e1c5adfcd6f2050f353e9756c795aef07c00a411d72f64a4418ba1a5`.
Its packet is at
`$RUNS_DIR/run-0f7aac31db6b4e9c93eda26d8c7e0ffd/review/classification/operating-point.json`.
The operator can start or resume an independently reviewed gold draft with
`make classification-calibrate RUN_ID=run-0f7aac31db6b4e9c93eda26d8c7e0ffd LABEL_SET=<new-id> LIMIT=40`.
Only explicit confirmations add rows; `f` then `freeze` scores and, if scoring passes, runs the
archive gate. After passing calibration, `make classification-operating-review
RUN_ID=run-0f7aac31db6b4e9c93eda26d8c7e0ffd` presents decoded evidence and records the
decision. The implementation run made neither human labels nor an operating decision.
The empty draft at `$RUNS_DIR/<run-id>/review/classification/gold-archive-gold-review.jsonl`
can be resumed with the command above by using `LABEL_SET=archive-gold-review`.

Human review required: `approve-classification-operating-point`.
Status: pending reviewed archive labels and held-out calibration; no operating point is approved.
Review: the current-code packet above, mapping digest, `make classification-calibrate
RUN_ID=<run-id> LABEL_SET=<new-id> LIMIT=40`, and `make classification-operating-review
RUN_ID=<run-id>`.
Decision: accept/revise thresholds and exceptional outcomes, or retain unclassified; record at
`$RUNS_DIR/<run-id>/review/classification/decision.json`.
Blocked next work: `publish-provided-archive-end-to-end-proof` and
`approve-archive-organization-plan`; no archive placement was attempted.

The task remains active in `plan.md` because the calibration acceptance gate failed for missing
human-reviewed inputs. The next action is to obtain independently reviewed archive labels via the
new terminal command, freeze and score their held-out split, inspect errors, and rerun the complete
integration suite before claiming acceptance. Plan count remains 73 (60 agent, 13 human); next
eligible agent task remains this one and the next human task is blocked.
