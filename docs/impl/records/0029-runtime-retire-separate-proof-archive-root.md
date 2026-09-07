# Task Record

## Task and scope

- Id / capability / checkpoint: `retire-separate-proof-archive-root` / `portable-runtime` /
  `review-corpus-and-control-integrity`
- State: accepted
- Source: ad hoc operator request to stop treating development proof runs as a second archive
  target; working tree at record start.
- Initial count: 76 tasks (66 agent, 10 human).
- Accepted task:

```markdown
#### retire-separate-proof-archive-root

Remove the extra `PROOF_ARCHIVE_DIR` source root so development proof runs use the same
`ARCHIVE_DIR` silos and ordinary pipeline or stage commands as any other corpus run.

- Serves: `portable-runtime` --
[Configuration and multi-SSD paths](../design/spec.md#configuration-and-multi-ssd-paths)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Root boundaries](records/0005-runtime-refactor-safe-runtime-root-boundaries.md);
[Configuration parity](records/0006-runtime-refactor-runtime-configuration-parity.md);
[Representative corpus approval](records/0023-corpus-approve-representative-corpus-and-gold.md).
- User-visible outcome: Operators configure one file corpus as `ARCHIVE_DIR` (and optional named
silos). During development they point that root at a legally usable representative slice and run
ordinary pipeline or stage commands; there is no second proof-only source variable.
- Scope boundary: Retire `PROOF_ARCHIVE_DIR` from the path model, configuration registry,
containment, readiness, and operator docs. Keep `$RESULTS_DIR/proofs/` as generated evidence.
Do not implement corpus stages, the planned `make proof` dispatcher, or gold fixtures.
- Data and artifact paths: `src/arxiv_int/runtime/`, `.env.example`, mirrored tests under
`tests/config/`, `tests/compose/`, `tests/readiness/`, and `tests/test_cli.py`; spec, remaining
proof tasks, and current-state evaluation and runtime pages.
- Execution path: Amend the path model so proof runs read configured archive silos; drop the
optional proof placement and its overlap and reset special cases; update tests so archive silos
remain the protected source roots; point remaining provided-archive tasks at `$ARCHIVE_DIR`.
- Acceptance gates: Configuration, path, reset, readiness-report, and CLI regressions pass
without `PROOF_ARCHIVE_DIR`; leftover `.env` names are ignored like any undocumented variable;
`make lint-spec-plan`, `make lint-doc-links`, and `make ci` pass.
- Documentation target: `docs/impl/current/portable-runtime.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

- Amendments: none.

## Implementation

`PROOF_ARCHIVE_DIR` is no longer a runtime variable. Proof runs read the same configured archive
silos as ordinary pipeline and stage commands (`ARCHIVE_DIR` and optional `ARCHIVE_SILO_<ID>_DIR`).
During development the operator points `ARCHIVE_DIR` at the authorized representative slice.

Reuse: `runtime_placements()`, `validate_runtime_paths()`, `erase_protected_roots()`, and
`report_protected_roots()` already treated archive silos as `source` roots. The extra optional
placement, pairwise-overlap exception, and reset/readiness special cases were removed rather than
replaced.

Compatibility: a leftover `PROOF_ARCHIVE_DIR=` line in `.env` is dropped with other undocumented
names and does not create a placement. `$RESULTS_DIR/proofs/` remains generated evidence. The
planned `make proof` dispatcher is unchanged remaining work; it will package ordinary runs, not
read a second source root.

Current-state pages: [portable-runtime.md](../current/portable-runtime.md),
[evaluation.md](../current/evaluation.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Retired variable ignored | `uv run pytest tests/config/test_paths.py::test_retired_proof_archive_variable_is_ignored` | pass; leftover `PROOF_ARCHIVE_DIR` is absent from values and placements |
| Path overlap and free space | `uv run pytest tests/config/test_paths.py` | pass; archive silos remain independent source roots; output free space still blocks |
| Empty optional reference | `uv run pytest tests/config/test_parity.py` | pass; empty-reference fixture now uses `PG_WAL_DIR` |
| Reset enclosing a source silo | `uv run pytest tests/compose/test_service_reset.py::test_reset_refuses_a_target_enclosing_an_archive_silo` | pass; nested extra silo under `SERVICE_STATE_DIR` is refused |
| Readiness report containment | `uv run pytest tests/readiness/test_workstation.py::test_report_is_refused_inside_an_archive_or_database_root` | pass; destination inside `ARCHIVE_DIR` or `PGDATA_DIR` is blocked |
| CLI optional roots | `uv run pytest tests/test_cli.py` | pass; ambient `PG_WAL_DIR` still cleared; no `PROOF_ARCHIVE_DIR` option |
| `make lint-spec-plan` | `make lint-spec-plan` | pass; 0 findings; 76 tasks (66 agent, 10 human) |
| `make lint-doc-links` | `make lint-doc-links` | pass; 0 broken links |
| `make ci` | `make ci` | pass; 791 passed, 18 skipped, 1 warning |

## Audit handoff

none identified. Reviewed that archive silos remain protected source roots for reset and readiness
reports, that leftover `PROOF_ARCHIVE_DIR` cannot reintroduce a second placement, and that remaining
provided-archive tasks now name `$ARCHIVE_DIR` without adding a proof-only command in this change.

## Close or resume

Accepted. Plan counts: 76 tasks before and after (ad hoc refactor; remaining provided-archive tasks
were retargeted in place). Capability `portable-runtime` remains shipped. Next agent work is
unchanged: `implement-local-inference-adapters`. No commit or push was made.
