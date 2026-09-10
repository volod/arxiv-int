# Retire Milestone Evaluation Scaffolding

## Task and scope

- Id: `retire-milestone-evaluation-scaffolding`; capability: `governance`.
- State: accepted.
- Source: ad hoc user request at revision `d237db2`; clean working tree at start.
- Initial count: 61 tasks (51 agent, 10 human).
- Accepted task:

```text
In src/arxiv_int/evaluation/proof we have wording "proof identity published under", "proof
manifest" etc. Also in evaluation package we have e.g. fixtures that looks like tests or temporary
artifacts. Analyse code base. If some unused code in the main pipeline can serve as integration
tests, create a separate integration test in the tests directory if needed. e.g., to check integrity
and correctness against the provided file archive, using the working pipeline code and including
only integration test logic and extra cross-checks to prove integrity and result correctness.
Remove code that was used only as temporary milestone checks or a disposable run and can't be
reused in integration tests.  Remove code that was used as an intermediate end-to-end experiment
for specific tasks, integration, or artifact testing and is now obsolete.
```

Bounded task snapshot:

```markdown
#### retire-milestone-evaluation-scaffolding

Remove obsolete milestone evaluation/proof machinery, retaining only reusable evaluation code and
archive checks that belong in an explicit integration test.

- Serves: `governance` --
[Provided-archive integration runs](../../design/spec.md#provided-archive-integration-runs)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Corpus proof record](0068-corpus-prove-corpus-foundation-on-provided-archive.md);
[pipeline-control proof record](0053-pipeline-prove-pipeline-control-on-provided-archive.md);
[repaired control proof record](0056-pipeline-reprove-pipeline-control-after-reconciliation-repair.md).
- User-visible outcome: The shipped package exposes working evaluation primitives and one honest
archive integration path, without test-fixture scoring or a parallel proof publication product.
- Scope boundary: Review evaluation production code, tests, fixtures, CLI/Make/DAG wiring, runtime
paths, and owning docs. Preserve reusable metrics/bundles and accepted historical records.
- Data and artifact paths: `src/arxiv_int/evaluation/`, `tests/evaluation/`,
`tests/integration/corpus/`, Make/runtime wiring, and evaluation/corpus/control documentation.
- Execution path: Trace callers; delete disposable publication/self-scoring paths; move independent
corpus cross-checks into an archive-marked test that runs the ordinary production DAG.
- Acceptance gates: The provided archive passes source/artifact/accounting/offset integrity and an
unchanged zero-worker replay; focused tests and `make ci` pass; active docs expose no retired path.
- Documentation target: `docs/impl/current/evaluation-foundation.md`
- Review checkpoint: none.
```

- Amendments: none.

## Implementation

The review traced `src/arxiv_int/evaluation/` through its CLI, Make targets, production registry,
tests, packaged configuration, accepted records, current state, specification, and remaining plan.
It separated three kinds of code:

- Immutable result bundles and direct scoring primitives remain reusable evaluation code. Shared
  constants and `MissingEvidenceError` now live with those primitives instead of depending on the
  deleted fixture/evaluate packages.
- The canned evaluation families, frozen positive/negative fixture catalog, fixture generator, and
  `EvaluateStage` were a self-scoring scaffold. The runner ignored declared upstream artifacts and
  scored fixture predictions that were already labelled as positive or negative. The package, CLI,
  Make target, packaged thresholds, tests, and production runner binding were removed. The declared
  future `evaluate` stage remains in the DAG without a runner so unavailable work stays explicit.
- `evaluation/proof` was a parallel publication system for milestone runs. Its control scenario
  copied an archive into disposable roots, and its corpus branch republished ordinary corpus
  artifacts under a second manifest/identity scheme. The package, proof config, result-root setup,
  test-only inspection branch, and historical publisher tests were removed.

The independent checks that add evidence beyond producer validation now live only in
`tests/integration/corpus/`. `make test-archive` runs the ordinary production registry from
`inventory` through `chunk`, validates attempt and quality records, re-executes generated batch and
snapshot contracts, rehashes physical source bytes, reconciles occurrence/document/quarantine and
duplicate accounting, replays normalized views and offset maps, reconstructs every chunk from its
canonical/source bounds, and requires an unchanged zero-worker replay. The default test and
coverage targets exclude the explicit `archive` marker.

The specification and planning rules now require ordinary stage manifests plus integration-only
cross-checks for current and future archive runs. Current-state and operator documentation remove
the retired CLI, Make, results-tree, and publisher claims while retaining accepted records as
historical evidence.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Production boundary | `rg` scan for deleted evaluation/proof imports, commands, configs, and result paths | Pass: no production/test reference remains; accepted record names and stable future task ids remain historical |
| Archive integrity and correctness | `make test-archive` | Pass: 1 test in 83.41 s against the configured archive through the ordinary DAG |
| Ordinary run evidence | `run-4a6ed1bbe12d440e8d381b362ebf3a4e` | Pass: 568 inventory rows; 414 documents; 48,986 spans; 121 extraction quarantines; 414 normalized documents; 87 duplicate groups/252 memberships/37 suppressions; 70,550 chunks across 377 documents; replay cache-hit every stage and invoked zero workers |
| Ordinary manifest integrity | inventory/extract/normalize/dedupe/chunk manifest SHA-256 | Pass: `b03a636f...a7f0`, `ed44cc10...df49`, `fb8ae494...6465`, `ed6f0148...0f6a`, `a80bf453...ac9` checked in place; shortened here to avoid treating the record as an alternate registry |
| Relevant deterministic tests | focused evaluation/CLI/runtime tests; affected CI regressions | Pass: 55 tests, then 51 tests after correcting stale runner/marker expectations |
| Formatting/static checks | `make format`; Ruff; focused MyPy; `git diff --check` | Pass: 767 files formatted/unchanged; no lint, type, or whitespace findings |
| Required repository gate | `make ci` | Pass: 1,250 tests, 51 declared heavy/archive exclusions, plus all required static/data/schema/doc gates |
| Quality diagnostics | `make quality`; `make lint-md`; `make build` | Coverage run passed 1,250 tests at 86%; the first composite ended on four Markdown line-length findings, all fixed; focused Markdown lint and source/wheel build then passed |
| Documentation gates | `make lint-doc-links`; `make lint-spec-plan` | Pass: 0 broken links; 0 specification/plan findings |

## Audit handoff

`none identified`. Self-review covered deleted-code callers, DAG availability, Make/test selection,
runtime result directories, archive artifact/accounting/offset invariants, packaged files, active
documentation, and stable historical links. Reusable metrics and bundle publication remain owned by
the evaluation foundation; actual future evaluators must consume ordinary upstream artifacts.

## Close or resume

Accepted. The required archive and CI gates pass; every `make quality` subgate passes after the
record/document line wrapping repair. Current-state indexes and planning policy link this record.
The plan remains 61 tasks (51 agent, 10 human) before and after because the request was ad hoc.

Capability changes: `evaluation-foundation` now exposes reusable metrics/bundles only;
`corpus-foundation` has a repeatable provided-archive integration gate; `pipeline-control` and
future archive capability tasks use ordinary manifests rather than a parallel proof publisher.
