# Task Record

## Task and scope

- Id / capability / checkpoint: `refactor-safe-runtime-root-boundaries` / `portable-runtime` /
  `review-foundation-and-store-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `refactor-safe-runtime-root-boundaries`; code revision `1e0db1d`
  with a clean working tree at task start.
- Accepted task:

```markdown
#### refactor-safe-runtime-root-boundaries

Unify protected-root checks before any reset deletion or readiness-report write.

- Serves: `portable-runtime` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-codebase-01, AUD-codebase-02](records/codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: Runtime and readiness paths documented in [Portable runtime](current/portable-runtime.md).
- User-visible outcome: Archive, proof, checkout and canonical data stay protected even when
configuration is
invalid, a selected reset root contains a source, or a report path enters a protected subtree.
- Scope boundary: Refactor shared containment policy and fix verified refusal gaps first; no real reset,
source mutation, broad runtime rewrite or change to ordinary service-stop behavior.
- Data and artifact paths: `runtime/{paths,service_reset,path_model}.py`, `readiness/run.py` under `src/arxiv_int/`,
`tests/config/`, `tests/compose/`, `tests/readiness/`, and disposable test roots.
- Execution path: Reproduce the non-mutating cases in the codebase review; use symmetric ancestor/descendant
checks for protected roots, action-specific allowed children, derived-root overlap rules and
pre-write revalidation; reject unsafe reset targets before stopping services.
- Acceptance gates: Failing regressions cover a reset root containing an archive/checkout/results tree,
report destinations inside proof/database roots, derived-root aliasing, symlink swaps and invalid
configurations; safe fixture operations retain their semantics and make ci passes.
- Documentation target: `docs/impl/current/portable-runtime.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

`src/arxiv_int/runtime/containment.py` is a new module owning the single protected-root policy.
It exposes `contains()` / `overlaps()` for symmetric ancestor and descendant tests, the typed
`ProtectedRoot` (variable, resolved path, operator-facing detail, and whether strict descendants
remain allowed), `containment_violation()` for the first refusal, and the action-specific root sets
`erase_protected_roots()` and `report_protected_roots()`. The fail-closed `resolve_allowed_path()`
moved here from `runtime/paths.py` so one module owns path containment; `arxiv_int.runtime` still
re-exports it, so no caller changed.

Verified refusal gaps closed:

- `runtime/service_reset.py` previously used `resolve_allowed_path()` for the checkout and archive
  silos, which only detects a target *inside* a protected root, and compared `RESULTS_DIR` by
  equality alone. A reset root that *contains* the checkout, an archive silo, or `RESULTS_DIR` was
  accepted. It now delegates to the shared symmetric policy, and `RESULTS_DIR` declares
  `allow_descendants` so the derived service-data roots that normally live beneath it stay erasable
  while the results root and its ancestors do not.
- The reset planned targets from already resolved paths, so a directory swapped for a symlink into
  protected data between planning and deletion was followed. `_erase()` now revalidates the
  configured (unresolved) path immediately before clearing it, so the swap resolves into a
  protected root and is refused. `_configured_data_paths()` keeps the configured form while
  `service_data_targets()` keeps its resolved public contract.
- `runtime/compose.py` ran `docker compose down` before validating reset targets. `run_compose()`
  now calls the new `validate_service_reset()` first, so an unsafe configuration refuses without
  stopping any service. Ordinary stop behavior for every other action is unchanged.
- `readiness/run.py::_persist_report` checked only containment in `RESULTS_DIR` plus a checkout and
  silo overlap of the results root, so an invalid roots configuration could place the JSON inside a
  proof or database subtree. `_destination_refusal()` now checks the resolved destination and the
  results root against the shared protected roots (checkout, archive silos, proof archive, and the
  `PGDATA_DIR`, `PG_WAL_DIR`, and tablespace roots), and the same check runs again after the report
  directory is created and immediately before the write.
- `runtime/paths.py` did not compare derived roots with each other, so two derived roots could
  alias one tree and a reset of one would erase the other. `_check_derived_aliasing()` blocks that;
  the identical pairwise loop already used for primary roots is now the shared
  `_report_pairwise_overlaps()`.

Compatibility: the reset refusal messages are now uniform
(`refusing to erase <path>; it overlaps <detail> (<VARIABLE>); change that root in .env`); the
readiness `report.json` finding keeps its name, status, and action shape while its detail states the
specific refusal. No public function was removed. Aliased derived roots and a report destination in
a protected subtree, both previously accepted, are now blocked; both were already invalid
configurations under the documented root rules.

Current state: [Portable runtime](../current/portable-runtime.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Reset root containing an archive, checkout or results tree | `uv run pytest tests/compose/test_service_reset.py::test_reset_refuses_a_target_containing_a_protected_root` and `::test_reset_refuses_a_target_enclosing_the_proof_archive` | pass; disposable `tmp_path` roots only, no operator root touched |
| Report destination inside a proof or database root | `uv run pytest tests/readiness/test_workstation.py::test_report_is_refused_inside_a_proof_or_database_root` | pass; asserts the file is absent and the refusal names the variable |
| Report destination around the checkout | `uv run pytest tests/readiness/test_workstation.py::test_report_is_refused_when_results_encloses_the_checkout` | pass |
| Symlink swap out of `RESULTS_DIR` for the report | `uv run pytest tests/readiness/test_workstation.py::test_report_symlinked_out_of_results_is_refused` | pass; nothing written at the link target |
| Symlink swap into a protected root for a reset | `uv run pytest tests/compose/test_service_reset.py::test_reset_refuses_a_symlink_swapped_into_a_protected_root` | pass; the fixture source file survives an `apply=True` run |
| Derived-root aliasing | `uv run pytest tests/config/test_paths.py::test_derived_roots_may_not_alias_one_tree` | pass |
| Unsafe target refused before services stop | `uv run pytest tests/compose/test_service_reset.py::test_run_compose_reset_refuses_unsafe_targets_before_stopping_services` | pass; asserts the fake runner received no command |
| Regressions fail without the fix | `git stash push -- src && uv run pytest tests/readiness/test_workstation.py tests/compose/test_service_reset.py tests/config/test_paths.py -q` | valid-negative; all eight new tests failed at revision `1e0db1d`, then passed after `git stash pop` |
| Safe fixture operations keep their semantics | `uv run pytest tests/compose tests/config tests/readiness -q` | pass; dry-run, apply, mode `0700` on `PGDATA_DIR`, and existing refusals unchanged |
| Required CI | `make ci` | pass; 212 tests, format, lint, typing, doc links, plan integrity |
| Infrastructure/documentation gate | `make quality` | pass; coverage 91.14% against the 90% floor, Markdown lint, wheel and sdist build |

No real reset, service stop, or operator root was exercised: every case ran against disposable
`tmp_path` roots with fake Compose runners and fixture filesystem evidence. Fixture coverage does
not prove behavior against a real archive or a live Compose stack.

## Audit handoff

`AUD-codebase-01` and `AUD-codebase-02` are resolved by this record: reset containment is symmetric
and revalidated before deletion, unsafe targets refuse before any stop, and the readiness report
destination is validated against proof, database and source roots before directories are created.

- `AUD-safe-runtime-root-boundaries-1`, nonblocking, owner [review-foundation-and-store-boundaries](../plan.md#review-foundation-and-store-boundaries):
  observation at `runtime/service_reset.py::_erase`. Invariant: the tree erased is the tree that was
  resolved as safe. Evidence: revalidation re-resolves the configured path immediately before
  `_clear_directory`, which itself refuses a symlink or non-directory, so the remaining window is a
  swap between that final `resolve()` and `iterdir()`. Impact: closing it needs directory file
  descriptors (`os.open` with `O_NOFOLLOW` plus `*at` calls), a wider change than this refactor's
  scope. Next check: evaluate descriptor-based erasure when concurrent operator tooling can run
  during a reset. Disposition: open.

## Close or resume

All required gates passed: `make ci`, `make quality`, and the eight new regressions, each confirmed
to fail at revision `1e0db1d`. No gate is outstanding. Next action: none for this task; the audit
note above is carried to `review-foundation-and-store-boundaries`.

Updates made: `docs/impl/current/portable-runtime.md` describes the shared containment policy, the
new reset and report refusals, derived-root aliasing, and the extended test coverage; this record is
linked from the [record index](README.md); the dependency references in
[Runtime configuration parity](refactor-runtime-configuration-parity.md) and
`review-archive-organization-integrity` now point at
this record. Plan counts: 91 tasks before, 90 after (agent lane 80 to 79). Capabilities changed:
none added or removed; `portable-runtime` gains stricter, unified protected-root refusals.
