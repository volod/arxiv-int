# Task Record

## Task and scope

- Id / capability / checkpoint: `implement-retryable-setup-command` / `portable-runtime` /
  `review-foundation-and-store-boundaries`
- State: accepted
- Source: [plan](../plan.md) (task removed on acceptance)
- Initial count: 81 tasks (70 agent, 11 human).
- Accepted task: paste the full original block verbatim:

```markdown
#### implement-retryable-setup-command

Replace manual environment, model and service command sequencing with one setup/edit/retry target.

- Serves: `portable-runtime` -- [Operator setup](../design/spec.md#retryable-setup-and-default-pipeline-command)
- Agent status: RUN NEEDED
- Audit inputs: [AUD-operator-entrypoints-1](records/0016-govern-design-simple-operator-entrypoints.md#audit-handoff).
- Dependencies: [Root boundaries](records/0005-runtime-refactor-safe-runtime-root-boundaries.md);
[Configuration parity](records/0006-runtime-refactor-runtime-configuration-parity.md);
[Service planning](records/0007-runtime-refactor-profile-aware-service-planning.md);
[Probe safety](records/0008-runtime-refactor-readiness-probe-safety.md);
[Canonical relational schema](records/0021-store-create-canonical-relational-schema.md);
`implement-local-inference-adapters`.
- User-visible outcome: `make setup` creates missing `.env`, names required edits, and safely retries
dependency/model/service/schema preparation until applicable checks pass, without shell activation.
- Scope boundary: A thin coordinator over independently callable atomic commands and existing
adapters; no corpus processing, alternative scheduler, privileged OS installation, service-data
reset or automatic destructive migration.
Report pipeline implementation availability separately; full default-run acceptance belongs to the
existing directory-to-knowledge-base and provided-archive proof tasks.
- Data and artifact paths: `src/arxiv_int/runtime/setup/`, shared configuration/feature/service policy,
`scripts/shared/common.sh`, Make/CLI, `.env.example`, `tests/runtime/setup/`,
`docs/guide/operator-workflow.md`,
`$DATA_DIR/setup/<attempt-id>/`, and safe `$RESULTS_DIR/reports/{setup,readiness}.json`.
- Execution path: Reuse dotenv append-sync and resolution before `.venv` exists; introduce typed
PIPELINE_PROFILE/SERVICE_PROFILES/SETUP_DOWNLOADS settings with spec defaults and no Make defaults
shadowing `.env`. Resolve setup requirements from declarative profile/feature metadata without
importing workers; use supplied
fixture requirements until concrete profile providers ship; this task owns the lightweight
requirement seam and does not depend on the later pipeline DAG. Expose `setup-config`, `setup-env`,
`services-pull`, `models-pull`, `setup-wait` and `setup-schema` atomic Make/CLI commands. Compose them
with existing package, path/service, pinned PostgreSQL image, contract/ontology and readiness
handlers in the runbook's order; direct and aggregate calls share typed policy and attempt context.
Extend the existing consolidated extra set with the selected requirements, sync once, and propagate
failures; nested commands retain that union and honor offline mode. Do not chain bootstrap's
pre-start readiness as a prerequisite to startup. Prepare safe roots, acquire/cache-check selected
images/models, start services, wait for transport/model health without requiring an initialized
schema, and run eligible Alembic upgrades and
catalog inspection against the configured service only. Derive its connection privately from shared
config, verify target identity and refuse conflicting migration URL overrides, unknown catalogs or
drift; disable the store command's disposable fallback and leave adoption to its explicit workflow.
Reuse accepted store/quality adapters without generating revisions or embedding transformation SQL.
Preserve operator values and verified work; revalidate actual state and fingerprints on each retry,
reject concurrent conflicting setup, handle cancellation, and render redacted per-phase status plus
next action.
- Acceptance gates: Deterministic fakes cover absent `.env`/`.venv`, incomplete/edited configuration,
spaces/foreign checkout, explicit overrides, missing tools/privileges, failed sync/download/start,
timeouts, offline cache misses, model/backend switching, unsafe roots, schema drift, blocked
migrations, cancellation and concurrent attempts. Compare the aggregate and documented atomic phase
traces, reports and failure propagation; prove schema checks hit the selected service and cannot
succeed against scratch or conflicting targets. Fresh shell calls observe `.env` edits; unchanged
retries reuse verified work but probe readiness again. No dependent phase runs after failure.
Declare a setup smoke with isolated configured roots and the pinned store/local endpoint, including
stopped/restarted services, slow health and an edited setting followed by the same `make setup`,
and prove source/data preservation; fixture model acquisition cannot prove production model fit.
Missing mandatory providers remain blocked/unavailable, never successful readiness. The linked
runbook reproduces the setup chain without hidden prerequisites or duplicated business logic.
`make ci` and `make quality` pass; README only advertises the setup outcomes actually proved.
- Documentation target: `docs/impl/current/portable-runtime.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none. Local-inference request adapters remain a later capability; this task reuses
  the accepted readiness HTTP probes and owns model acquisition (`models-pull`) plus the fixture
  requirement seam, matching the task's "until concrete profile providers ship" execution path.

## Implementation

- Coordinator `arxiv_int.runtime.setup` with ordered phases: config, env, package, paths,
  postgres-image, images, models, services, wait, contracts, schema, readiness.
- Atomic CLI/Make: `setup-config`, `setup-env`, `services-pull`, `models-pull`, `setup-wait`,
  `setup-schema`; aggregate `make setup` bootstraps dotenv/uv then runs `arxiv-int setup`.
- Typed `PIPELINE_PROFILE` / `SERVICE_PROFILES` / `SETUP_DOWNLOADS` in the shared schema. Make no
  longer defaults `SERVICE_PROFILES`, so `.env` is not shadowed.
- Schema binds to `POSTGRES_*` on loopback, refuses URL identity mismatch, never calls disposable
  apply, and leaves adoption to `make db-adopt`.
- Child package/contract checks inherit the process environment. CLI setup passes `os.environ` so
  isolated `DATA_DIR` locks and reports follow the operator overlay.
- Pipeline implementation is reported `unavailable` while investigation stages remain unimplemented.
- Docs: [portable-runtime.md](../current/portable-runtime.md).
- Working tree also contains unrelated store/contract files from record 0021; this task did not
  absorb them.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Deterministic fakes | `pytest tests/runtime/setup` | pass; absent dotenv, failed sync, offline miss, drift, cancel, concurrent lock, reuse vs readiness |
| Schema binds to selected service | `tests/runtime/setup/test_schema.py`, `test_schema_cli_coverage.py` | pass; conflicting URL and disposable apply refused |
| Aggregate vs atomic traces | `test_atomic_and_aggregate_share_phase_names` | pass |
| `make ci` | `make ci` | pass; 671 passed, 9 skipped |
| `make quality` | coverage, Markdown, build | pass; coverage 90.91% (floor 90) |
| CUDA host smoke | isolated roots under `$HOME/arxiv-int-setup-smoke`, `SERVICE_PROFILES=core`, `COMPOSE_PROJECT_NAME=arxiv-int-setup-smoke`, `GENERATION_MODEL=llama3.2:3b`, pinned image `arxiv-int/postgres:17-0.25.6-age1.7.0`, host Ollama on RTX 4060 Ti | pass; copy in `.data/setup/smoke-0022/` |
| Stop/restart then same `make setup` | smoke restart attempt `20260906T153919Z` | pass; env/package/paths/images/models/contracts/schema reused; services/wait/readiness re-probed |
| Edited `.env` then `make setup` | `LOG_LEVEL=DEBUG` then restore | pass; attempt `20260906T153953Z` ready |
| Source/data preservation | SHA-256 of archive marker, `AGENTS.md`, operator `PGDATA_DIR` find listing | unchanged |
| Fixture model vs production fit | `llama3.2:3b` already on host Ollama | valid-negative; does not prove `qwen3.8:27b` memory fit |
| Pipeline availability | smoke `pipeline_implementation=unavailable` | pass; stages remain unimplemented |
| Host OS install / service-data reset / auto-adopt | out of scope | not claimed |

## Audit handoff

none identified. Reviewed dotenv/Make non-shadowing, schema binding without disposable fallback,
lock/retry reuse, process-environment inheritance for nested checks, and infrastructure-ready versus
pipeline-unavailable reporting. `AUD-operator-entrypoints-1` is resolved here.
`implement-local-inference-adapters` still owns production request adapters and model-fit.
`make pipeline` stays with pipeline-control.

## Close or resume

Accepted after deterministic setup tests, CUDA-host isolated smoke on the pinned store and local
Ollama endpoint, documentation, `make ci` (671 passed, 9 skipped), and `make quality` (coverage
90.91%). Plan counts: 81 tasks before, 80 after (agent lane 70 to 69; human 11 unchanged).
Capability `portable-runtime` is marked shipped in the specification registry; `make pipeline`
remains planned. Next agent work: `implement-dbt-transformation-foundation`. No commit or push
was made.
