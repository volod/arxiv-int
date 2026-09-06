# Project rules

Canonical rules for all agents. Tool-specific instruction files link here; do not duplicate rules.
Read only the selected task, relevant code, and linked specification/current-state sections.
Load other guidance when the condition below applies; do not preload the whole documentation tree.

## Guardrails

- Preserve unrelated work. Diagnostic requests do not authorize code changes.
- Do not commit, push, rewrite history, or revert user changes unless explicitly asked.
- Use Python 3.12+, fully typed production code, and no `from __future__ import annotations`.
- Use Make workflows and `uv` with `pyproject.toml`/`uv.lock`; update the lock with dependency changes.
  Before direct `uv`: `source scripts/shared/common.sh`, then `arxiv_int_load_env`.
- Add the smallest justified dependency. Resolve paths from the root; honor `.env` and `DATA_DIR`.
  Never hardcode machine-specific paths or expose secrets in code, logs, fixtures, tests, or docs.
- Put production Python in `src/arxiv_int/` and mirror tests in `tests/`. Keep parsing in `cli.py`
  and domain behavior in focused modules. Reuse shared policy; avoid duplicates or new frameworks.
- Prefer cohesive functions/modules. Aim for <=250 lines per Python/shell file; split at real seams.
  Use named constants and `logging`, not `print()`, in production.
- Share shell logic in `scripts/shared/common.sh`; prefix every shell function with `arxiv_int_`.
- Put tool artifacts in `$DATA_DIR/<method>/<run-id>/`; product outputs use specification-defined
  operator roots, never `DATA_DIR` or `src/`. Use ASCII in code, logs, comments, docs, and output.

## Task cycle

1. Select one bounded task. Check its full dependencies and relevant records/notes before coding.
   Do not start blocked work.
   `make plan-status` reports priority, not readiness; record the starting task count.
2. Save the full task in `docs/impl/records/<task-id>.md` using the
   [record template](docs/impl/records/template.md). Preserve original text and full scope amendments.
   Identify affected files/interfaces and existing code to reuse; do not silently broaden scope.
3. Implement and self-review. Update tests for behavior changes; bugs need failing regressions.
   Tests stay deterministic and network-free unless an external run is explicitly declared.
4. Verify: relevant tests and `make ci` are required. Use `make format`; fix Markdown by hand.
   Use `make quality` for coverage, Markdown and build checks on infrastructure/release changes.
   Fix causes, never weaken gates. Record failures/unrun checks honestly; fixtures do not prove
   real-archive quality or CUDA fit. Failed required acceptance keeps the task open.
5. Before stopping, update the record with evidence, decisions, audit notes and the next action.
   On acceptance, update narrow current-state docs and indexes, link the record, replace removed
   task references with accepted-record links, then remove only satisfied scope from the plan.
   Run `make lint-doc-links` and `make lint-spec-plan`; report task counts and capability changes.
   Inspect `git status`; stop your processes/services, remove temporary scaffolds, and retain evidence.

## Read when needed

- **Adding/amending task scope or capabilities:** use the
  [planning rules](docs/guide/planning-workflow.md#task-shape). Specify new behavior and evaluation
  before planning/code. `docs/impl/plan.md` holds only remaining work; current docs describe what exists.
- **Cross-task concerns or milestone reviews:** use the
  [review rules](docs/guide/planning-workflow.md#audit-notes-and-milestone-reviews).
  Route each concern to one owner; plan blocking repairs before dependent work continues.
- **Dependency/setup changes:** use the relevant [development guide](docs/guide/development.md)
  section. Tool adapters remain links to this file.
