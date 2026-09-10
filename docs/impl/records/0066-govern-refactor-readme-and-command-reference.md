# README and Command Reference Refresh

## Task and scope

- Id / capability / checkpoint: `refactor-readme-and-command-reference` / `governance` / none.
- State: accepted; documentation gates and `make ci` pass.
- Source: ad hoc operator request (2026-09-10). Code revision `d413383` plus the accepted
  checkpoint/repair/migration work of records
  [0063](0063-corpus-review-corpus-and-control-integrity.md),
  [0064](0064-corpus-repair-corpus-stage-identity-and-source-offsets.md) and
  [0065](0065-store-refactor-single-initial-store-migration.md) in the working tree.
  `make plan-status` reported 62 tasks (52 agent, 10 human) before and after.
- Accepted task: the operator's request, recorded verbatim, and the bounded task block written for
  it.

> Update README.md - a) "### 2. Archive to analyst results -- orchestration  only" - update with the
> latest changes, and update docs/guide/operator-workflow.md with all the implemented pipeline stage
> commands b) "### 3. Organize an archive -- separate planned utility" should be in the same style
> as other sections: one end-to-end command and a link to the separate document c) "## Available
> commands" - just provide make help entry command and a link to a separate document with available
> command details

```markdown
#### refactor-readme-and-command-reference

Make the README quick start describe what actually runs, and move command and organization detail
into guide documents an operator can follow.

- Serves: `governance` -- [Operator entry points](../design/spec.md#retryable-setup-and-default-pipeline-command)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: [Corpus and control integrity checkpoint](records/0063-corpus-review-corpus-and-control-integrity.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md).
- User-visible outcome: A reader sees one runnable corpus chain, one end-to-end organization
command with a link to its own page, and `make help` plus a command reference instead of a
hand-copied CLI listing.
- Scope boundary: README, the operator workflow guide, two new guide pages and the guide indexes.
No code, contract, command or capability change; do not restate the specification's full
organization design as if it were implemented.
- Data and artifact paths: `README.md`, `docs/guide/operator-workflow.md`,
`docs/guide/commands.md`, `docs/guide/archive-organization.md`, `docs/guide/README.md`,
`docs/README.md`.
- Execution path: Check every documented stage id and command against the stage registry and the
CLI parser; rewrite the quick-start sections; move the command listing and organization table into
their own pages with explicit availability markers; index both pages.
- Acceptance gates: Every documented stage id resolves in `PRODUCTION_DEPENDENCIES`, every command
marked available appears in `--help`, and `make lint-md`, `make lint-doc-links`,
`make lint-spec-plan` and `make ci` pass.
- Documentation target: `docs/guide/commands.md`
- Review checkpoint: none; documentation refresh with no dependent consumer.
```

- Amendments: none.

## Implementation

**(a) Section 2 and the operator workflow.** The heading is now
`### 2. Archive to analyst results -- corpus stages available`. The README shows the corpus chain
that actually runs today -- `run-create`, `forecast`, then `preflight`, `inventory`, `extract`,
`normalize`, `dedupe`, `chunk`, then `inspect` -- and keeps the honest limits: the default
investigation profile still names unregistered later stages, so aggregate `make pipeline` fails
explicitly. The intro paragraph and the post-setup note no longer claim that corpus stages are
unimplemented.

`docs/guide/operator-workflow.md` now leads its atomic chain with the same runnable corpus
sequence, names what each shipped runner produces, and states the forecast-refresh, unchanged-rerun
and interrupted-inventory behavior. Maintenance and aggregate commands moved into their own block.
The planned expansion that follows dropped `validate-facts`, `catalogs` and `anomalies`: those three
were listed as `make stage STAGE=...` lines but are not in `PRODUCTION_DEPENDENCIES`, so they could
never be a stage id. The guide's header now links the command reference.

**(b) Section 3.** Organization matches the other quick-start sections: one preview command in a
fenced block, the reason it stays separate, and a link to the new page. The three-row command table
moved out of the README. The section states plainly that the command is planned and that
`arxiv-int archive` currently offers only `locate` and `import-ledger`, which the previous table did
not.

**(c) Available commands.** The README now shows `make help` and links the reference. The
hand-maintained command listing and its explanatory paragraph moved to the new page, where each
entry is marked available or planned.

New documents:

- `docs/guide/commands.md` -- CLI surface behind `make help`, grouped by area, with an availability
  marker per command and links to the operator workflow and current implementation.
- `docs/guide/archive-organization.md` -- the separate placement utility: why it stays out of the
  pipeline, the end-to-end preview and apply commands, `copy` versus `move`, safety boundaries,
  directory and name policy, and the review required before a real placement, sourced from
  [the specification](../../design/spec.md#separate-archive-organization-utility).

Both are linked from [the contributor guide index](../../guide/README.md); the command
reference is also linked from [the documentation index](../../README.md).
`docs/impl/current/canonical-store.md` was updated for record 0065 in the same session.

No code, contract or command behavior changed. Documentation target:
[current implementation index](../current.md) is unchanged, because no capability changed.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Stage list matches the registry | `PRODUCTION_DEPENDENCIES` and `production_registry()` in `src/arxiv_int/pipeline/dag/stages.py` | Pass; the seven documented shipped runners are exactly those bound by `with_runner`, and every planned stage id documented is a registry key |
| Archive command availability is stated correctly | `.venv/bin/arxiv-int archive --help` | Pass; prints `{locate,import-ledger}` only, as both new pages state |
| Documented corpus chain runs verbatim | the README block executed as written on `run-43b8f2b1d10b4f7594177db1617baa77` against the bounded fixture silo | Pass; forecast `decision=degraded` with a proceed action, all six stages `succeeded`, and `make inspect` reports every stage `produced` with a valid tree and no schema drift. Fixture evidence; see [checkpoint 0063](0063-corpus-review-corpus-and-control-integrity.md#acceptance-evidence) for the full-recompute run |
| Relative links and anchors resolve | `make lint-doc-links` | Pass; 0 broken links |
| Markdown lint | `make lint-md` | Pass; 0 findings |
| Plan and specification structure | `make lint-spec-plan` | Pass; 0 findings |
| Required repository gate | `make ci` | Pass; 1269 tests, 50 deselected |

Documentation evidence only. Nothing here establishes provided-archive quality or promotes a proof.

## Audit handoff

Unresolved task-local audit notes: `none identified`.

Reviewed scope: `README.md`, `docs/guide/operator-workflow.md`, the two new guide pages, and the
guide and documentation indexes, checked against the stage registry, the CLI parser and the
specification. Self-review corrected three inaccuracies inherited from the previous text: the README
presented the unregistered `archive reorganize` as an executable command table; the operator guide
listed three stage ids that do not exist in the registry; and both documents still described the
corpus stages as unimplemented.

The command reference duplicates availability facts that live in code. It is a hand-maintained page
and can drift; no gate enforces it. That is the same standing risk every current-state page carries,
and it is not a new one.

## Close or resume

All acceptance gates pass. Next action: none. Indexed in the [record index](README.md). Plan counts
unchanged at 62 tasks (52 agent, 10 human); next agent task remains
[prove-corpus-foundation-on-provided-archive](../plan.md#prove-corpus-foundation-on-provided-archive).
Capability change: none.
