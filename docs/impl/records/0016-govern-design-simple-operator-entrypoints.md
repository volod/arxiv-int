# Task Record

## Task and scope

- Id / capability / checkpoint: `design-simple-operator-entrypoints` / `governance` /
  `review-foundation-and-store-boundaries`
- State: accepted; design, task creation and documentation gates passed. Runtime implementation
  remains planned.
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
- Resumed at `9760ef2` with a clean working tree after the user's registry fixes and accepted
  records 0017-0021. Resumption count: 81 tasks (70 agent, 11 human); next agent task:
  `implement-dbt-transformation-foundation`. Preserve those records and completed store scope.
- Amendments: the user added the atomic-command/runbook requirement and requested finalization
  of the existing portable-runtime task, not implementation. Full wording:

> detaled step-by-step execution command chain should be provided in separate document with link
> from readme. the end-to-end commands should just reuse underling atomic commands

Latest continuation:

> Continue and finalize spec and task creation. Take into account that, before the limit is hit,
> you have created docs/impl/records/0016-govern-design-simple-operator-entrypoints.md and
> docs/impl/plan.md #### implement-retryable-setup-command task. I have fixed the task registry and
> have implemented some ### Canonical store -- `canonical-store` task; see 0017-0021 task records.
> Finalize ### Portable runtime -- `portable-runtime` task creation

Original task snapshot:

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

Full amended task, retaining the original scope and incorporating the user's continuation:

```markdown
#### design-simple-operator-entrypoints

Finalize the short README workflow, separate atomic-command runbook, specification and remaining
implementation owners after the accepted store work.

- Serves: `governance` -- [Operator commands](../../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: Existing runtime records 0005-0008; accepted contract/store records 0017-0021;
current Make/CLI/configuration behavior and open orchestration, forecast and output tasks.
- User-visible outcome: README shows setup/edit/retry and one default archive-to-report command;
a linked guide provides the equivalent atomic execution chain and current manual commands.
- Scope boundary: Design and documentation only; preserve the user's registry and store changes,
current command availability, explicit roots, resource/authorization gates and private configuration.
- Data and artifact paths: README, specification/architecture, `docs/guide/operator-workflow.md`,
setup guide, plan, current portable runtime, this record/index, and
`$DATA_DIR/operator-entrypoints/<run-id>/`.
- Execution path: Reconcile completed tool adapters; specify shared command handlers and run
context, retry phases, selected-database binding, defaults, publication and failure semantics;
finalize the existing setup task and amend the existing pipeline integration/proof owners.
- Acceptance gates: README setup has at most two logical steps and the normal pipeline path one
command; the separate guide lists atomic commands with availability and equivalent aggregation;
every requirement has an owner and deterministic/live gates; no circular prerequisites or
reopened accepted store scope; format, CI, Markdown, links and spec-plan checks pass.
- Documentation target: `docs/impl/current/portable-runtime.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

## Implementation

Reuse `arxiv_int_sync_dotenv`, the common environment resolver, typed runtime configuration,
feature catalog, `ServicePlan`, protected-path validation, Compose operations and readiness.
The planned stage registry, forecast, manifests and data-tool adapters retain their existing owners.
Aggregate targets and the documented manual chain must call the same atomic command handlers;
neither a second workflow implementation nor another scheduler is needed. The current unified
Make dependency set is retained. Setup must bind schema operations to the configured live service,
never accept the store command's disposable-database fallback as service readiness. Reuse the
accepted SQLAlchemy/Alembic implementation and Pandera checks; do not restore the removed `db/`
tree or duplicate the planned dbt runner.

README now contains the planned setup/edit/retry target and one default pipeline command, linked
to [the separate operator workflow](../../guide/operator-workflow.md). That guide retains current
manual setup and analyst commands, adds the explicit target setup phases and baseline stage chain,
and labels availability. The [specification](../../design/spec.md#retryable-setup-and-default-pipeline-command)
and [architecture](../../design/architecture.md#module-ownership-and-durable-interfaces) require
shared atomic handlers, one frozen run context, fresh forecast, quality gates and one finalizer.
The [current runtime page](../current/portable-runtime.md) records this as design only.

Finalized the existing `implement-retryable-setup-command` task with missing atomic wrappers,
offline/cache/failure behavior, selected-database binding, reuse and declared setup smoke gates.
Its fixture requirement seam precedes pipeline implementation, avoiding a dependency cycle through
the foundation checkpoint. Existing local-inference, stage-DAG, forecast, output-manifest and
integration/proof tasks own their respective integration and aggregate/atomic equivalence checks.
No duplicate task, runtime dependency, migration, lockfile or production-code change was needed.
Records 0017-0021, the accepted store implementation and the user's registry fixes are preserved.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Current behavior review | Makefile, `cli.py`, common shell helpers, runtime/readiness and store apply/inspect adapters; records 0017-0021 | Pass: reused current adapters; identified explicit service binding and dependency-sync failure propagation as setup integration requirements |
| Short workflow and detailed chain | README sections 1-2; `docs/guide/operator-workflow.md` | Pass: setup/edit/retry and one pipeline command; separate current/manual and planned atomic commands with shared-handler semantics |
| Specification and task coverage | Spec operator contract; architecture; existing setup and downstream orchestration/proof tasks | Pass: defaults, retries, atomic equivalence, one run context, quality/publication and safe schema binding have owners; no new task or cycle |
| Formatting | `make format` with the verification `DATA_DIR`; `operator-entrypoints/finalize-0016/format.log` | Pass: 266 files unchanged; no production edits |
| Markdown, links and plan | `make lint-md lint-doc-links lint-spec-plan` with the verification `DATA_DIR`; `operator-entrypoints/finalize-0016/docs-close.log` | Pass after correcting line wrapping and blockquote separation; zero link/plan findings |
| Command syntax | ASCII decoding and `bash -n` on README/runbook Bash blocks; `operator-entrypoints/finalize-0016/command-syntax.log` | Pass: 13 blocks; syntax only, no documented setup/pipeline commands executed |
| Required CI | `make ci` with the verification `DATA_DIR`; `operator-entrypoints/finalize-0016/ci-verified.log` | Pass: 617 tests, 9 skips, one upstream Pandera/Polars deprecation warning; disposable PostgreSQL contract evolution passed. Initial sandbox attempt blocked uv cache writes and Docker access, retained in `ci.log`; rerun used approved Docker access and `UV_CACHE_DIR=$DATA_DIR/cache/uv` |
| Runtime acceptance / full quality | No setup/pipeline execution; no `make quality` | Not applicable to this documentation task: no infrastructure/dependency/code changes; implementation tasks retain their deterministic, full-quality, host/CUDA and archive gates |

## Audit handoff

| Note | Observation, evidence and impact | Next check and sole owner | Disposition |
| --- | --- | --- | --- |
| `AUD-operator-entrypoints-1` | Observed / blocking before the short setup workflow can be advertised: README Quick Start requires eleven manual environment steps and no setup coordinator exists. `make bootstrap` syncs `.env`/`.venv` and audits readiness, but dependency sync, model and image acquisition, service start, schema preparation and readiness remain separate operator commands with no shared retry, no resumption of verified work and no per-phase status, so an operator editing `.env` between attempts cannot retry only what still fails. | [Retryable setup command](../plan.md#implement-retryable-setup-command): prove absent `.env`/`.venv`, edited configuration, missing tools, failed sync/download/start, timeouts, cancellation and concurrent attempts, and that an unchanged retry reuses verified work while still probing readiness. | Open; routing complete, no production code changed here |

## Close or resume

Accepted the documentation task; the implementation audit remains open with the existing setup
task as sole owner. README/guides, specification/architecture, current runtime and this record/index
are reconciled. No implementation task was removed or duplicated, and no capability was promoted.
Counts at resumption and closure are both 81 tasks (70 agent, 11 human), with 77 blocked by
prerequisites. The next eligible agent task remains `implement-dbt-transformation-foundation`.
`implement-retryable-setup-command` remains `RUN NEEDED` and awaits its local-inference prerequisite.
The original 84-task count predates the user's intervening accepted work; it is not this turn's
before/after count.

Final review found no additional cross-task concern beyond `AUD-operator-entrypoints-1`. Its
original README observation above is historical: the short design is now documented, while actual
setup retry behavior still requires implementation. Verification evidence is retained under
`$DATA_DIR/operator-entrypoints/finalize-0016/`. No operator services or pipeline were started;
the CI disposable contract database is cleaned up by its runner. Production files, dependencies,
accepted records 0017-0021 and unrelated work are unchanged; no commit or push was performed.

`AUD-operator-entrypoints-1` and this record's index row were added while
[0017](0017-contract-gov-refactor-contract-schema-and-migration-tooling.md) was in progress, at the
user's request, because both were failing `make lint-spec-plan` for every task. Nothing else in this
record or its task scope changed during that earlier registry repair. The resumed design changes
and acceptance evidence above follow the later explicit continuation request.
