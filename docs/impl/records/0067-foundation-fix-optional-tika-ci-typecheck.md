# Task Record

## Task and scope

- Id: `fix-optional-tika-ci-typecheck`
- Capability: `project-foundation`; focused CI repair.
- State: accepted.
- Source: ad hoc user request; revision `b738086`; initially clean working tree.
- Initial task count: 62 (52 agent, 10 human); no plan task removed by this repair.
- Dependencies: accepted extraction implementation in
  [record 0061](0061-corpus-integrate-tiered-text-extraction.md), current worker, optional
  dependency declarations and GitHub CI workflow reviewed.
- Accepted task (verbatim):

<!-- pyml disable MD013 -->

```text
in github environment we have error, fix Run make ci-github PYTHON_VERSION=3.13
794 files already formatted
All checks passed!
src/arxiv_int/extraction/iscc_worker.py:17: error: Unused "type: ignore"
comment  [unused-ignore]
        from iscc_tika import (  # type: ignore[import-untyped]
        ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
src/arxiv_int/extraction/iscc_worker.py:17: error: Cannot find implementation
or library stub for module named "iscc_tika"  [import-not-found]
        from iscc_tika import (  # type: ignore[import-untyped]
        ^
src/arxiv_int/extraction/iscc_worker.py:17: note: Error code "import-not-found" not covered by "type: ignore" comment
src/arxiv_int/extraction/iscc_worker.py:17: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
Found 2 errors in 1 file (checked 492 source files)
make: *** [/home/runner/work/arxiv-int/arxiv-int/make/quality.mk:18: typecheck] Error 1
Error: Process completed with exit code 2.
```

<!-- pyml enable MD013 -->

- Scope clarification (verbatim):

```text
it may be we do not need heavy tika related tests in github env
```

The existing native test already skips when the optional package is absent. Keep GitHub's
dependency selection unchanged; regress only static analysis, without loading the native parser.

- Scope amendment from that clarification: keep extraction excluded throughout `ci-github`,
  including dependency syncs inherited by its prerequisite checks. Preserve full local CI extras
  and all existing gates. Add a Make dry-run regression for both target profiles.
  The full gate exposed that prerequisite syncs otherwise reinstall Tika and Docling on GitHub.

- Scope: repair only the optional worker import typing policy and regress its missing-dependency
  typecheck; retain extraction runtime behavior, dependency groups and global typing gates.

Structured snapshot of the bounded request and clarification above:

```markdown
#### fix-optional-tika-ci-typecheck

Repair hosted CI type checking when the optional native extraction stack is absent, and keep
that stack excluded throughout the GitHub gate.

- Serves: `project-foundation` --
[Repository and package structure](../design/spec.md#repository-and-package-structure)
- Agent status: CLEAR
- Dependencies: [Tiered extraction](records/0061-corpus-integrate-tiered-text-extraction.md).
- User-visible outcome: GitHub CI type-checks the worker and skips native Tika execution without
installing Tika or Docling through later dependency syncs.
- Scope boundary: Optional import typing, inherited GitHub dependency profile, regressions and
tooling documentation; preserve runtime behavior and the full local CI dependency profile.
- Data and artifact paths: Worker, mypy configuration, Make quality targets, mirrored tests,
developer-tooling current state, this record and index; logs at `$DATA_DIR/ci/0067/`.
- Execution path: Reproduce missing-backend mypy errors and GitHub extraction syncs; repair the
module-specific typing policy and target-specific extras; verify both CI profiles.
- Acceptance gates: Failing regressions before repair; relevant tests, `make format`,
`make ci-github PYTHON_VERSION=3.13`, `make ci`, `make quality`, documentation and plan checks pass.
- Documentation target: `docs/impl/current/developer-tooling.md`
- Review checkpoint: Task-local self-review; no dependent consumer or human handoff.
```

## Implementation

GitHub installs CI extras without `extraction`; local Make setup installs that extra. The worker's
`import-untyped` suppression handles only the installed native package. Remove that annotation
and reuse the existing module-specific mypy override pattern for `iscc_tika` only. This covers
absent and untyped installations while retaining global missing-import and unused-ignore checks.
The parent `import` suppression was rejected by pinned mypy as insufficiently narrow; the
regression caught it. Add subprocess checks with site packages disabled for Python 3.12 and 3.13.
The GitHub Make target removes `--extra extraction` from the shared sync arguments for its
prerequisites. Local `make ci` retains the full stack. Dry-run regressions exercise both profiles.
Affected files: worker, mypy configuration, Make quality targets, mirrored tests, this record,
record index and [developer tooling](../current/developer-tooling.md).
No dependency version or runtime interface changes.

## Acceptance evidence

Logs: `$DATA_DIR/ci/0067/`. Commands source `scripts/shared/common.sh` and call
`arxiv_int_load_env`. The full GitHub run uses an isolated Python 3.13.15 environment via
`UV_PROJECT_ENVIRONMENT=$DATA_DIR/ci/0067/venv-3.13` and the matching Make `VENV` override;
the local environment is Python 3.12.3 with extraction installed.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Reproduce GitHub failure | `.venv/bin/mypy --no-site-packages --no-incremental --cache-dir=/dev/null --python-version 3.13 src/arxiv_int/extraction/iscc_worker.py` | Failed before repair with the reported two errors |
| Missing-backend regression | `make test PYTEST_CACHE="-o cache_dir=$DATA_DIR/cache/pytest tests/extraction/test_iscc_worker.py"` | Both Python targets failed before repair; pass after repair |
| GitHub sync regression | `make test VENV="$DATA_DIR/ci/0067/venv-3.13" PYTEST_CACHE="-o cache_dir=$DATA_DIR/cache/pytest tests/quality/test_ci_dependencies.py"` | GitHub case failed before target fix; local profile passed; `ci-profile-regression-before.log` |
| GitHub focused checks | `make test VENV="$DATA_DIR/ci/0067/venv-3.13" PYTEST_CACHE="-o cache_dir=$DATA_DIR/cache/pytest tests/extraction tests/quality/test_ci_dependencies.py"` | 23 passed, 1 skipped; native Tika absent; `github-focused-tests.log` |
| Local extraction checks | `make test PYTEST_CACHE="-o cache_dir=$DATA_DIR/cache/pytest tests/extraction"` | 22 passed with native Tika installed; `extraction-tests.log` |
| Formatting | `make format` | Pass; 796 files unchanged; `format.log` |
| GitHub gate | `make ci-github PYTHON_VERSION=3.13 VENV="$UV_PROJECT_ENVIRONMENT"` | Pass on Python 3.13.15: 1,272 passed, 1 skipped, 50 deselected; `ci-github-3.13.log`; Tika and Docling absent in `github-environment.txt` |
| Local required gate | `make ci` | Pass on Python 3.12.3: 1,273 passed, 50 deselected, including native Tika; `ci-3.12.log` |
| Infrastructure quality | `make quality` | Pass: 1,273 passed, 50 deselected; 86% diagnostic coverage; Markdown lint and source/wheel builds passed; `quality.log` |
| Final integrity | `make lint-doc-links lint-spec-plan plan-status`; `git diff --check`; `git status --short` | Pass; 0 link/plan findings; 62 tasks; only task-local files changed |

Initial full-gate attempts reached the repaired typecheck, then stopped on sandbox uv-cache
permissions and network access during dependency sync. Authorized execution with cache/network
access resolved those environment blockers. The original local Python 3.12 environment was
restored before local verification; the Python 3.13 gate runs separately.

## Audit handoff

None identified after reviewing the worker import, global typing gates, inherited Make dependency
profile and regressions for both CI profiles. All required gates passed. The fixtures establish
CI compatibility, not real-archive extraction quality.
No human review handoff applies.

## Close or resume

Accepted on 2026-09-10. Developer-tooling current state and the record index link this repair.
Hosted CI now retains its lightweight dependency profile and type-checks the optional native
worker successfully; extraction runtime behavior is unchanged. No open plan task was removed.
Plan counts before/after: 62 (52 agent, 10 human). The next eligible planned agent task remains
`prove-corpus-foundation-on-provided-archive`; it was not started.

All task processes finished. The temporary Python 3.13 environment was removed after verification;
logs remain under `$DATA_DIR/ci/0067/`. Local Python 3.12 with extraction is restored.
No remaining task-local action; changes are ready for review and were not committed or pushed.
