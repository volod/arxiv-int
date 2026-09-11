# Store-wide Lexical Load Lock

## Task and scope

- Id / capability / checkpoint: `serialize-concurrent-lexical-loads` / `lexical-retrieval` /
  `review-investigation-and-report-integrity`
- State: accepted; required gates pass.
- Source: user-directed repair of
  [AUD-retract-superseded-lexical-chunks-2](0074-lexical-retract-superseded-lexical-chunks.md#audit-handoff).
  `lexical-retrieval` is shipped. `make plan-status` reported 58 tasks (48 agent, 10 human); this
  repair was not the next eligible agent task. Code revision `c0a714e` plus the uncommitted record
  0074 audit repair.
- Accepted task:

```markdown
#### serialize-concurrent-lexical-loads

Serialize `load-lexical` runs that share one canonical store, so two runs with different snapshots
cannot interleave their load, retraction, projection build and reconciliation.

- Serves: `lexical-retrieval` --
[Data transformations and quality](../design/spec.md#data-transformations-and-quality)
- Agent status: CLEAR
- Dependencies: [Lexical snapshot chunk retraction](0074-lexical-retract-superseded-lexical-chunks.md).
- User-visible outcome: A second concurrent `load-lexical` run against the same store fails promptly
with a named lock error before it writes; the running load publishes a store equal to its snapshot.
- Scope boundary: Lock only the `load-lexical` store phase (load, retract, build, verify). Do not
change the projection-catalog lock, per-run file locks, the chunk stage or other stages. No waiting
queue or retry loop.
- Data and artifact paths: canonical `corpus.chunks`, the active lexical projection,
`$RUNS_DIR/<run-id>/search/lexical.json`.
- Execution path: Take a PostgreSQL session advisory try-lock on a dedicated autocommit connection,
under a key distinct from the projection catalog, before the load transaction; hold it through
build and verify; release it on exit and rely on session close after process death.
- Acceptance gates: A second holder is refused while the first holds the lock; the projection
catalog lock stays available to the build while the load lock is held; the stage runs load, build
and verify inside the lock and loads nothing when refused; the lock is released after a failure.
Deterministic tests and `make ci` pass.
- Documentation target: `docs/impl/current/lexical-retrieval.md`
- Review checkpoint: `review-investigation-and-report-integrity`.
```

- Amendments: none.

## Implementation

`arxiv_int.pipeline.load_lexical.lock.exclusive_lexical_load(url)` opens a dedicated `NullPool`
engine in autocommit mode and takes `pg_try_advisory_lock` on `LOAD_LOCK_KEY` (ASCII `ARXL`, beside
the projection catalog's `ARXP`). `LoadLexicalStage._run` holds it from before the load transaction
until verification ends; manifest publication follows outside it. A refused lock raises
`LexicalLoadBusyError` before any write. Exit runs `pg_advisory_unlock`; a failed unlock is logged,
and closing the non-pooled session releases the lock, as process death does.

Alternatives rejected: a blocking `pg_advisory_lock` would queue runs but cannot be interrupted by
`check_cancelled()` and would hang behind a stuck run; a transaction-scoped lock cannot span the
separate build sessions; a file lock covers only one `$RUNS_DIR`, not a shared store. The fail-fast
policy follows `lock_projection_catalog`. `load-lexical` is the only writer of `corpus.chunks`
today; a future writer must take the same key. `full`-scope reconciliation stays as the backstop.
`pipeline/load_lexical` is in the stage's code paths, so existing attempts re-run once.

Current state: [lexical retrieval](../current/lexical-retrieval.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Refusal, release after failure, distinct keys | `tests/pipeline/load_lexical/test_lock.py` | pass; an owned lock refuses before the body runs; unlock follows a failed body; `LOAD_LOCK_KEY` differs from `PROJECTION_LOCK_KEY` |
| Stage phases inside the lock | `tests/pipeline/load_lexical/test_lock.py` | pass; order is lock, load, build, verify, unlock, then summary and publish; a refused lock loads nothing |
| Live second load, catalog lock, release | `ARXIV_INT_RUN_LEXICAL=1 pytest -m heavy tests/integration/lexical/test_live_load_lock.py` | pass on the disposable pinned store; declared heavy, `make ci` deselects it |
| Live lexical regression | `ARXIV_INT_RUN_LEXICAL=1 pytest -m heavy tests/integration/lexical/test_live_lexical.py` | pass, 2 tests |
| Provided archive | `tests/integration/lexical/test_archive_lexical.py` | not run; the change adds one advisory lock per load and no data path |
| Required CI | `make ci` | pass; 1338 passed, 57 deselected; doc-link and spec-plan lints clean |

## Audit handoff

`none identified` after reviewing key collision with the projection catalog and hashed reuse-key
locks, autocommit (no transaction stays idle during the build), release after failure and process
death, cancellation between load and build, and that no other code writes `corpus.chunks`. A stuck
process holding the lock refuses every later load until its session ends; the error names the lock.

## Close or resume

Required gates pass. Plan tasks unchanged at 58 (48 agent, 10 human). Capability `lexical-retrieval`
remains shipped. [0074](0074-lexical-retract-superseded-lexical-chunks.md) audit note 2 is resolved
and its claim is removed from `review-investigation-and-report-integrity`. Next eligible agent task
remains `establish-versioned-udc-derived-scheme`. Updated
[lexical retrieval](../current/lexical-retrieval.md) and the record index. No human review handoff
applies. Next action: none for this task.
