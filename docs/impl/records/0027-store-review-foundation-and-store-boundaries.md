# Foundation and Store Boundary Review

## Task and scope

- Id: `review-foundation-and-store-boundaries`; capability: `canonical-store`.
- State: accepted.
- Source: `docs/impl/plan.md` at `2597b531aa3b8622deb745d46de6e655a77f97a1`; clean tree.
- Initial count: 77 tasks (67 agent, 10 human); selected task is eligible.
- Amendments: none.

```markdown
#### review-foundation-and-store-boundaries

Review the integrated milestone before pipeline control and corpus adapters.

- Serves: `canonical-store` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: checkpoint
- Audit inputs: [AUD-safe-runtime-root-boundaries-1](records/0005-runtime-refactor-safe-runtime-root-boundaries.md#audit-handoff);
[AUD-runtime-configuration-parity-1, AUD-runtime-configuration-parity-2](records/0006-runtime-refactor-runtime-configuration-parity.md#audit-handoff).
- Dependencies: [0025](records/0025-store-implement-rebuildable-search-and-graph-projections.md);
[Retryable setup command](records/0022-runtime-implement-retryable-setup-command.md);
[Readiness probe safety](records/0008-runtime-refactor-readiness-probe-safety.md);
[Contract identity and reference validation](records/0009-contract-gov-refactor-contract-identity-and-reference-validation.md);
`enforce-task-record-and-checkpoint-integrity`.
- User-visible outcome: An evidence-based checkpoint decides proceed, proceed-with-nonblocking-notes,
or blocked
for the named consumers; no-refactoring-needed is a valid conclusion.
- Scope boundary: Review the named milestone and routed notes only; no speculative rewrite, automatic
model upgrade, scope expansion or deferred replacement for each producer task's own checks.
Adding tests for important stabilized integrity, correctness, and business-logic cases in this
stage is in scope; concluding that existing tests already cover them is valid. Restoring a
numeric coverage floor is not.
Use deterministic integration evidence and inspect provided-archive proofs when available;
this verdict permits fixture implementation, not real-data or CUDA promotion.
- Data and artifact paths: Accepted producer records under `docs/impl/records/`, current-state pages,
existing test/proof artifacts, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Read full task snapshots and source changes; trace configuration/CLI/service parity,
protected roots and secrets, contract identity/evolution,
Alembic revision/adoption and live catalog evidence, dbt/canonical ownership, Pandera batch versus
global checks, transformation lineage and failure-before-activation,
setup configuration/edit/retry, dependency-sync failure propagation, phase ordering, shared
profile requirements and infrastructure-ready versus pipeline-available reporting,
optional imports, extension coexistence and canonical-versus-projection ownership;
replay representative existing tests/validators; add tests for important integrity, correctness,
and business-logic cases that the stage's now-stable interfaces still miss; reconcile every
routed note; record concrete findings with evidence, severity, affected consumers and one
disposition each.
- Acceptance gates: Every producer requirement and open note has an evidence-backed disposition;
verify the
listed invariants and make ci. Important stabilized cases in this stage have tests or an
evidence-backed conclusion that existing tests already cover them; a coverage percentage is not
a gate. Create a focused prerequisite refactor task for any blocking finding
and keep this checkpoint open until it passes; preserve valid negative results and nonblocking
follow-ups in the checkpoint record without claiming a wider audit.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: none; this task is the bounded checkpoint. Route follow-ups to explicit task ids.

```

## Implementation

Reviewed the integrated runtime, contract and canonical-store milestone against its producer
records and the linked specification/current-state sections. The initial verdict was **refactor
needed**: failed Make prerequisites could be ignored, publication trusted incomplete evidence,
active retries could replace data/evidence, cleanup dispatched into build, and catalog adoption
compared insufficient definitions. Disposable execution also reproduced temporary-server readiness.
The bounded prerequisite [repair 0028](0028-store-refactor-foundation-store-acceptance-boundaries.md)
was planned before implementation. Final review also repaired base-CLI optional imports and physical
catalog checks on setup reuse. The operator explicitly authorized prerelease migration consolidation.
No speculative architectural replacement or new dependency was needed.

The implementation retains one configuration policy, contract-derived metadata and frozen Alembic
DDL, shared batch-quality outcomes, dbt-derived generations, and transactional projection pointers.
A separate Python/shell dotenv parser remains justified because bootstrap runs before the virtual
environment exists; paired behavior tests bind the documented grammar. Current behavior is in
[Canonical store](../current/canonical-store.md), [Contracts](../current/contracts.md), and
[Portable runtime](../current/portable-runtime.md).

## Acceptance evidence

Review evidence is under `$DATA_DIR/architecture-review/20260906-foundation-store/`.
The producer matrix below covers the named milestone requirements; it does not infer current
acceptance from historical test counts or coverage percentages. Final CI reruns deterministic suites;
declared disposable runs exercise the actual pinned database, dbt and projection engines.

| Producer / boundary | Reviewed requirements and current evidence | Disposition |
| --- | --- | --- |
| 0004 task/record/checkpoint integrity; 0026 test policy | `tests/quality/`, `make lint-spec-plan`, `make lint-doc-links`; full task snapshots and amendments retained | policy unchanged; behavior and integrity tests, no numeric coverage gate |
| 0005 protected runtime roots | `tests/config/`, `tests/compose/`, readiness tests: symmetric overlap, aliases, symlinks, refusal before stop/write, redaction | existing positive/main-corner coverage sufficient; residual concurrent swap note routed below |
| 0006 configuration parity | shell/Python precedence, references, empty/missing values, whitespace, export state and foreign checkout fixtures | repaired exported-variable/whitespace mismatch and Make propagation in 0028 |
| 0007 shared service planning; 0008 readiness safety | Compose rendered profile parity and requirements; readiness loopback-only HTTP, redirects/body/time bounds, PostgreSQL password handling and extension selection | existing deterministic coverage sufficient; no service reset or inference request needed |
| 0009 identity/reference validation; 0010 registry | contract lint/canonical/fingerprint/registry tests: uniqueness, reference closure, explicit identity and stable serialization | current contract gate passes; no product semantic change |
| 0011 deterministic generation; 0012 evolution | generation adapter/Avro/SQL tests; `make contracts-check`, `make contracts-evolution`; identical/additive/breaking/reindex/vector/semantic/graph fixtures | requirements retained through later SQLAlchemy/Alembic tooling; old dbmate mechanism is superseded, not restored |
| 0013 ontology; 0014 domain contracts | ontology parsing/bindings, SHACL agreement, disjointness/evolution, domain negative fixtures; `make ontology-check` | existing fixtures cover stabilized meaning/identity boundaries; no real-document extraction claim |
| 0017 migration tooling; 0020 duplicate SQL retirement | `tests/contracts/migrations/`, SQLAlchemy catalog tests, offline SQL, revision checksum/graph/head checks | one authorized initial revision; future revision tooling retained; duplicate runtime DDL removed |
| 0018 pinned extensions | declared extension suite and image identity; transaction/restart/dump-restore coexistence probes | current live fixtures pass; this is not an operational recovery proof for operator data |
| 0019 batch versus whole-relation quality | `tests/data_quality/`, live staging rejection before COPY, dbt attached tests and typed shared results | Pandera validates batches; dbt checks selected whole relations; missing tests cannot publish |
| 0021 canonical schema | live empty/repeat initial apply, interrupted actual DDL rollback/retry, explicit irreversible teardown, fact/provenance/profile constraints, roles, COPY/upsert/buckets and drifted adoption | current live suite passes; previous-release upgrade replaced by operator-authorized prerelease consolidation |
| 0022 setup/edit/retry | `tests/runtime/setup/`: configuration edits, ordering, selected-service target, no disposable fallback, locked extras, reuse with fresh wait/readiness and unavailable pipeline reporting | current deterministic tests plus physical reuse and optional-import regressions; prior isolated host smoke remains historical |
| 0024 dbt ownership/lineage/publication | live full/incremental/delete parity, role isolation, selected model/test evidence, relation counts, sanitized artifacts, active retry refusal and pointer preservation | repaired in 0028; generation artifacts are isolated and active generations immutable |
| 0025 canonical versus projection ownership | live lexical/vector/graph/SQL fallback parity, logical ids, failed build pointer preservation, canonical row preservation and real cleanup | repaired in 0028; advisory lock and active-version refusal protect lifecycle operations |
| Base runtime / optional extras | subprocess `-S` help/setup-help/features regression | failed before 0028; passes with lazy schema execution and separate projection parser |
| Provided archive proof | inspected 0023 approval record and retained redacted `proof-archive-check.json` | approved readable slice exists; no inventory/extraction/gold artifacts were produced by that acceptance; no new corpus proof claimed |
| CUDA host and setup proof | host NVIDIA query; retained `setup/smoke-0022/{setup,readiness}.json` reports ready and pipeline unavailable | RTX 4060 Ti, 16380 MiB, driver 595.84 observed; prior smoke used a small fixture model, not current model-fit evidence |

Pinned live image: `arxiv-int/postgres:17-0.25.6-age1.7.0`, local image id
`sha256:739355d686e5dc6fb74b0da361d3ecaa03c4c55f47df1fe453a0c1c21f347b5a`.
The original image pins remain unchanged. No model was downloaded or executed by this review.
Fixture verdicts enable subsequent
implementation, not corpus/CUDA promotion or archive placement authorization.

The baseline deterministic suite passed (727 passed, 13 skipped), showing the missing invariants
were not covered. New regressions reproduced the failures before repair. The completed declared
integration run passed **22 tests**; the final catalog run passed **5 tests**, including detached
partition detection during setup reuse. [0028](0028-store-refactor-foundation-store-acceptance-boundaries.md)
contains exact commands, negative results and repaired boundary evidence.
Final `make ci` and `make quality` pass: 791 tests passed and 18 expected live-test skips.
The final projection rerun passes one live test after the CLI and cleanup-kind changes. Coverage
is diagnostic; Markdown, build, format, typing, complexity, shell and documentation gates pass.

## Audit handoff

Incoming note dispositions (the original records retain the single declaration of each note):

`AUD-runtime-configuration-parity-1` is resolved by this review: dependency-free bootstrap still
needs Bash; paired fixtures plus export/whitespace cases enforce the shared grammar. A parser
rewrite has no demonstrated benefit. Resolution owner: this checkpoint.

`AUD-runtime-configuration-parity-2` is resolved by the failing/passing export-state regression in
[0028](0028-store-refactor-foundation-store-acceptance-boundaries.md). Nonexported shell variables
no longer override values unseen by Python. Resolution owner: repair 0028.

`AUD-safe-runtime-root-boundaries-1` remains nonblocking for fixture implementation. Existing checks
refuse unsafe roots and planned symlink swaps; the concurrent final resolve/iteration race remains.
Evaluate descriptor-based deletion before real placement authorization. Its single next owner is
[review-archive-organization-integrity](../plan.md#review-archive-organization-integrity).

New audit notes: none identified beyond these reconciled incoming notes and the repaired blockers.

This routing grants no reset or archive-placement authorization.

Refactor verdict: **refactor needed, repairs accepted**. Final checkpoint decision:
**proceed-with-nonblocking-notes** for pipeline
control and corpus adapter fixture implementation only. No unresolved observed blocker is deferred
into those consumers. Backups/operator recovery and real corpus/model quality retain their separate
planned acceptance owners.

## Close or resume

All required gates pass. Original note links now record the two resolutions and the single future
archive-integrity owner. Current pages and the record index link this checkpoint and repair 0028;
downstream plan dependencies link the accepted record. Only the two satisfied task blocks were
removed. Plan counts: 77 at review start (67 agent, 10 human), temporarily 78, finally 76
(66 agent, 10 human). `canonical-store` changes from planned to shipped for its documented fixture
foundation. No other capability is promoted. Next eligible task: `implement-local-inference-adapters`.
No review-owned service remains running; retained evidence includes source/lock/revision fingerprints.
No commit or push was made.
