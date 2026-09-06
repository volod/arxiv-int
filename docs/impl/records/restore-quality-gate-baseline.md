# Restore Quality Gate Baseline

## Task and scope

- Id: `restore-quality-gate-baseline`; capability: `project-foundation`;
  checkpoint: `review-foundation-and-store-boundaries`.
- State: accepted after the required gates below passed.
- Source: [plan](../plan.md) task `restore-quality-gate-baseline` at revision `099b223`
  ("AI-01 | audited spec and tasks"). Dirty scope at start: the already-edited
  `src/arxiv_int/runtime/__init__.py` and `tests/compose/test_profiles.py` from the same
  repair, preserved and finished here; no other file was dirty.
- Accepted task:

```markdown
#### restore-quality-gate-baseline

Restore a passing baseline before expanding the implementation.

- Serves: `project-foundation` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-codebase-10](records/codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: Existing quality workflows in [Developer tooling](current/developer-tooling.md).
- User-visible outcome: The required CI gate is green and future failures can be attributed
to the next change.
- Scope boundary: Only repair source formatting/import order and decompose the complex
Compose topology test; preserve its assertions and public behavior. Do not weaken checks or skip tests.
- Data and artifact paths: `src/arxiv_int/runtime/__init__.py`, `tests/compose/test_profiles.py`, and
`$DATA_DIR/quality-baseline/<run-id>/`.
- Execution path: Capture current failures; run make format; split the combined topology assertions into
focused parametrized cases or cohesive helpers; review the diff for unrelated formatting changes.
- Acceptance gates: The same profile/mount/pin/health invariants are checked, deterministic tests
pass, and make ci and make quality pass with an explicit writable tooling root.
- Documentation target: `docs/impl/current/project-foundation.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Two repairs, both inside the declared boundary; no production behavior changed.

`src/arxiv_int/runtime/__init__.py` re-exported `arxiv_int.runtime.service_reset` on a
106-character single line that the pinned formatter and the import-order rule both rejected.
The line is now a parenthesized import block. The module's `__all__` and every exported name
are unchanged, so no importer of `arxiv_int.runtime` is affected.

`tests/compose/test_profiles.py` held one function,
`test_rendered_topology_has_pins_health_stop_and_mount_isolation`, that rendered the full
Compose topology once and then asserted four unrelated invariant families over it. Radon scored
it D (23) and the gate stops there, which also prevented the cognitive-complexity subcheck from
running at all. The rendering is now a module-scoped `rendered_topology` fixture built on
`tmp_path_factory`, and the assertions are five focused tests, one per invariant family:

| New test | Invariant retained |
| --- | --- |
| `test_rendered_services_pin_images_and_declare_health_and_stop` | no `latest` tag, digest pin except `age-viewer`, healthcheck test, stop grace period |
| `test_rendered_services_publish_ports_on_loopback_only` | every published port binds `127.0.0.1` |
| `test_rendered_vllm_service_pins_gpu_model_and_revision` | GPU request, pinned generation model and revision |
| `test_rendered_database_root_is_mounted_only_by_the_database` | exact database bind mount and `PGDATA_DIR` isolation from every other service |
| `test_rendered_services_drop_privileges_and_keep_configs_read_only` | read-only Grafana/Prometheus config mounts, host uid:gid for the five services that need it, no `user` for `cadvisor` |

Alternative considered and rejected: `pytest.mark.parametrize` over the invariants. The four
families assert different shapes over different services, so parameters would have carried
branching back into one body. Separate named tests keep each failure self-describing.

The module-scoped fixture also keeps the split from multiplying subprocess work: the split
would otherwise have run `docker compose config` five times instead of once. Test count rises
from 168 to 172 and no assertion was dropped, loosened, skipped or marked expected-failure.

Current state: [Project foundation](../current/project-foundation.md#tests-and-verification).

## Acceptance evidence

Run id `20260906`; artifacts under `.data/quality-baseline/20260906/`. Baseline copies are the
`099b223` versions of the two files, extracted with `git show` so the failures are reproducible
after the repair.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Baseline failures captured | `ruff format --check` and `ruff check --select I` on the HEAD copy of `runtime/__init__.py`; `radon cc -s -n D` on the HEAD copy of `test_profiles.py` | fail as expected: `baseline-format.log`, `baseline-lint.log` (`I001`), `baseline-radon.log` (`D (23)`); revision in `baseline-revision.txt` |
| Same profile/mount/pin/health invariants checked | Diff review of `tests/compose/test_profiles.py`: every assertion of the removed function appears in the five replacements | pass, by inspection; the table above maps each family |
| Deterministic tests pass | `make ci DATA_DIR=.data` | pass, 172 tests, `ci.log`; local `docker compose config` renders only, no service started |
| Required CI gate | `make ci DATA_DIR=.data` (format, lint, typing, complexity, shell lint, doc links, spec-plan, tests) | pass, `ci.log` |
| Full local quality suite | `make quality DATA_DIR=.data` (ci-checks, coverage, `lint-md`, `build`) | pass, `quality.log`: 90.14% total coverage above the 90.0% floor, both sdist and wheel built |
| Explicit writable tooling root | `DATA_DIR=.data` on both runs; caches under `.data/cache/`, complexipy run from `.data/cache/complexipy` | pass |
| Plan integrity after removal | `make lint-doc-links DATA_DIR=.data`, `make lint-spec-plan DATA_DIR=.data`, `make plan-status DATA_DIR=.data` | pass, `plan-status-before.log` / `plan-status-after.log` |

No archive, model, CUDA, GPU or running-service evidence is claimed; this task exercised no
service and no real corpus. The Compose assertions are rendered-configuration fixtures, not a
started stack.

## Audit handoff

`none identified`. Reviewed scope: the two repaired files, the complexity gate wiring in
`Makefile`, and the diff against `099b223` for unrelated formatting churn (none present;
`git diff --check` clean). [AUD-codebase-10](codebase-and-workflow-audit.md#audit-handoff) is
resolved by this record: the required gate is green, so a later failure is attributable to the
next change. The audit's remaining code findings keep their existing owner tasks.

## Close or resume

All required gates passed; none remain. Plan counts: 93 tasks before (82 agent, 11 human),
92 after (81 agent, 11 human); no capability moved lanes. Capability change: none -- this task
restored an existing gate and added no product behavior.

Updated on acceptance: [Project foundation](../current/project-foundation.md#tests-and-verification)
and the [record index](README.md). References to the removed plan task now point at this record.
Next action: the plan's next agent task,
[`enforce-task-record-and-checkpoint-integrity`](../plan.md#enforce-task-record-and-checkpoint-integrity),
which depended on this baseline and is now unblocked. No process, service or temporary scaffold
remains; the baseline copies under `.data/quality-baseline/20260906/` are retained as evidence.
