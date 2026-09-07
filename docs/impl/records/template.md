# Task Record

Copy to `NNNN-<group>-<task-id>.md` using the
[record naming rules](../../guide/planning-workflow.md#record-file-naming), then index it.
Keep evidence concise; keep accepted task text complete.

## Task and scope

- Id / capability / checkpoint:
- State: active, blocked, or accepted only after required gates pass.
- Source: plan path/id/revision or ad hoc request; code revision and relevant dirty scope.
- Accepted task: paste the full original block verbatim in a fenced Markdown block.
- Amendments: none, or each full revised block with reason/authorization; retain the original.

## Implementation

Changed modules/behavior, reuse, decisions/alternatives, compatibility or migration effects,
limitations, and the current-state page link. Mark unavailable historical text explicitly.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Every accepted requirement | Reproducible evidence | pass, fail, not-run, blocked, valid-negative |

Retain outputs at configured artifact roots and relevant code/model/contract/config fingerprints.
Distinguish fixtures from real runs. Missing, mock or old evidence does not prove current acceptance.

## Audit handoff

`none identified` with reviewed scope, or one entry per stable `AUD-task-id-N`:

- Observation or hypothesis; blocking/nonblocking; location, invariant, evidence and impact.
- Next check; exactly one owner task/checkpoint; disposition and resolution evidence link.

For checkpoints: coverage, every incoming note's disposition, refactor/no-refactor verdict and
proceed/proceed-with-nonblocking-notes/blocked decision. Keep unresolved blockers open.

## Close or resume

Passed/remaining gates, next action, current/index/dependency-link updates, plan counts before/after,
and capabilities changed. Replace removed task links with accepted-record links; retain this record.
