# Task Record

## Task and scope

- Id / capability / checkpoint: `design-simple-operator-entrypoints` / `governance` /
  `review-foundation-and-store-boundaries`
- State: active; documentation and verification pending.
- Source: ad hoc user request at code revision `981c7d3`. Existing dirty scope from the preceding
  data-engineering review is preserved: database README, specification, plan, current contracts,
  record index and record 0015.
- Initial count: 84 tasks (73 agent, 11 human); next agent task:
  `refactor-contract-schema-and-migration-tooling`.
- Original request (wording preserved; line wrapping only):

> In README.md, we have a Quick Start section with 11 steps just to set up the environment, and 11
> for 2. Archive to analyst results. Please provide a single- or two-step target that performs the
> setup for step 1. Environment and services setup (specifics: the user should edit .env, and it
> may take multiple attempts for the infra to be ready to run the pipeline), and a single command
> to run all pipeline steps end-to-end using the default .env settings. Please design and add
> additional tasks if needed.

- Interpretation: This is a design/README/plan task. Both convenience commands remain
  labelled planned until their implementations and acceptance gates pass.
- Amendments: none.

```markdown
#### design-simple-operator-entrypoints

Replace the long README onboarding sequence with a retryable setup target and one default
archive-to-report command, specifying implementation owners and acceptance.

- Serves: `governance` -- [Operator commands](../../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: Existing runtime environment, profile and readiness records 0005-0008;
current Make/CLI/configuration behavior and open orchestration, forecast and output tasks.
- User-visible outcome: Operators can understand setup/edit/retry and one-command execution without
activating the virtual environment, exporting variables or choosing individual pipeline stages.
- Scope boundary: Design and documentation only; preserve current command availability, explicit
operator roots, resource/authorization gates, private configuration and prior work.
- Data and artifact paths: README, specification/architecture, setup/pipeline guides, plan,
current portable runtime, record/index, and `$DATA_DIR/operator-entrypoints/<run-id>/`.
- Execution path: Inspect current wrappers and config/service policy; define defaults, setup phases,
retry/failure outcomes, pipeline completion and ownership; add only missing implementation scope.
- Acceptance gates: README setup has at most two logical steps and the normal pipeline path one
command; all new behavior has task owners and deterministic/live gates; no circular prerequisites;
current docs remain honest; format, CI, Markdown, links and spec-plan checks pass.
- Documentation target: `docs/impl/current/portable-runtime.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

## Implementation

Reuse `arxiv_int_sync_dotenv`, the common environment resolver, typed runtime configuration,
feature catalog, `ServicePlan`, protected-path validation, Compose operations and readiness.
The planned stage registry, forecast, manifests and data-tool adapters retain their existing owners.
Do not duplicate these as shell command chains or introduce another scheduler.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Current behavior review | Makefile, CLI, common shell helpers and runtime/readiness code | Pending |
| Short workflow, specification and task coverage | README, specification and plan | Pending |
| Required verification | `make format`; `make ci`; Markdown/link/plan checks | Pending |

## Audit handoff

| Note | Observation, evidence and impact | Next check and sole owner | Disposition |
| --- | --- | --- | --- |
| `AUD-operator-entrypoints-1` | Observed / blocking before the short setup workflow can be advertised: README Quick Start requires eleven manual environment steps and no setup coordinator exists. `make bootstrap` syncs `.env`/`.venv` and audits readiness, but dependency sync, model and image acquisition, service start, schema preparation and readiness remain separate operator commands with no shared retry, no resumption of verified work and no per-phase status, so an operator editing `.env` between attempts cannot retry only what still fails. | [Retryable setup command](../plan.md#implement-retryable-setup-command): prove absent `.env`/`.venv`, edited configuration, missing tools, failed sync/download/start, timeouts, cancellation and concurrent attempts, and that an unchanged retry reuses verified work while still probing readiness. | Open; routing complete, no production code changed here |

## Close or resume

Next: specify the workflow and integration boundaries, update README/guides and plan, then verify.

`AUD-operator-entrypoints-1` and this record's index row were added while
[0017](0017-contract-gov-refactor-contract-schema-and-migration-tooling.md) was in progress, at the
user's request, because both were failing `make lint-spec-plan` for every task. Nothing else in this
record or its task scope changed.
