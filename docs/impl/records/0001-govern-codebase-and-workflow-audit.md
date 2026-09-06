# Codebase and Workflow Audit Record

## Identity and state

- Task id: `codebase-and-workflow-audit` (ad hoc documentation/review request).
- Capability: `project-foundation` development governance, with repairs under their owning
  [registered capabilities](../../design/spec.md#capability-registry).
- State: blocked at the repository CI gate; review and requested documentation are present.
- Review checkpoint: Findings route to the specific tasks below; their milestone checkpoints
  review subsequent implementation. This record does not accept those future repairs.
- Source: User request following the specification/architecture audit; full wording retained below.
- Code context: HEAD `67f3e19530012237acc2bd949475ddaeb52d079b`. Existing dirty documentation changes
  to spec, architecture, plan and current governance were preserved. Source/tests matched HEAD.

## Accepted request

User wording, with only line wrapping added:

> a) Please analyze the already implemented codebase. If we need some refactoring, please create a
> separate task in plan.md first,
> b) We will use less effort and a different model for further
> development, and from time to time will perform review tasks for refactoring in case something
> goes wrong and to improve the quality of implementation. Our current development circle based on
> plan.md, if task is implemented agent apdates current with some inforamation lost, update plan.md
> if some specific issue is discavered, and removals are implemented as tasks, so in the future
> only full git commit tree contains all the task descriptions.
> Let's improve task.md with additional refactoring
> and audit tasks in important points to ensure overall arhitecture implementation integrity, and
> update development instruction for weak models to add notes for future audit tasks
> d) please update README.md quickstart with full step-by-step pipeline command (to shorten use
> table ormat), from environment and service setap to final results analysis

This is an ad hoc request, not a task removed from the plan. The review interprets `task.md` as the
existing canonical `docs/impl/plan.md`; it does not create another backlog. The accepted scope is
analysis and documentation, with separate future repair tasks before changing production code.

## Scope amendments

None. Earlier specification/architecture changes remain intact. The new development-integrity
section specifies the workflow before its enforcement task enters the plan. No capability beyond
the existing development foundation and affected product capabilities was registered.

## Decisions and implementation

- Retain cohesive foundation modules; repair demonstrated shared-boundary failures first. Do not
  split files simply for line counts or perform an architectural rewrite during diagnosis.
- Add eight refactoring tasks, one deterministic governance enforcement task, and seven finite
  milestone checkpoints. Amend existing scheduler/telemetry tasks for gaps they already own.
- Keep `plan.md` forward-only while preserving complete task text and amendments in records.
  Current pages describe available behavior and link those records. Records hold evidence, not a
  second actionable backlog. No lost historical task description was fabricated.
- Require bounded execution, acceptance mapping and evidence-bearing audit handoffs from all
  models. Preserve failed/unrun/partial results; model confidence cannot replace gates.
- Gate early integration on deterministic evidence, with private-data promotion separately gated.
  A later integration concern after checkpoint closure gets a new bounded round and its own id.
- Show available setup commands separately from the target pipeline and artifact-only organizer
  in README tables. Use locked extras in contributor examples, with required environment loading.

Changed behavior and plan counts are indexed in
[Codebase review and development handoffs](../current/governance/codebase-review.md). No production,
test, dependency, service configuration, or operator environment changes were made.

## Acceptance evidence

Artifacts below are relative to `.data/codebase-review/20260905/`. This explicit local tooling root
avoids the read-only configured tooling volume. The synthetic script uses fake credentials and
probe transports, reads no private archive, and calls reset only with `apply=False`.

| Requirement/gate | Command or artifact | Result | Limitation or owner |
| --- | --- | --- | --- |
| Analyze implemented code and reproduce concrete issues | `.venv/bin/python .data/codebase-review/20260905/reproduce.py`; `findings.json` | Nine observed cases reproduced | Synthetic boundary cases; no service/CUDA proof |
| Schedule repairs before implementation | `plan.before.md`, `counts-before.json`, forward task blocks | Eight refactors plus one enforcement task | Repairs remain open; no source fix claimed |
| Preserve full task scope and audit context | AGENTS, planning workflow, record template and this request record | Documentation present | Automated validation remains future work |
| Milestone architecture gates | Seven checkpoint tasks, dependency review artifact | Inputs and downstream gates declared | No milestone is accepted by this documentation change |
| Full operator quickstart in tables | README compared with CLI, Makefile, feature groups, Compose and target spec | Available and planned sequences separated | No real setup, download or pipeline run executed |
| Repository quality and documentation | Final gate results below | Docs/typing/tests pass; full CI fails | Baseline failures require the quality repair task |

## Audit handoff

Each row is a stable note, with one actionable owner. A task owner must add a failing regression,
repair and verify it, then link its accepted record here. These notes remain routed until that
evidence exists. Refer to `findings.json` for the nine reproduced case keys.

| Note id | Kind / severity and invariant | Location and evidence | Impact / next check | Owner and disposition |
| --- | --- | --- | --- | --- |
| `AUD-codebase-01` | Observed / blocking: protected source roots must not be erasable through an ancestor | `runtime/service_reset.py::_assert_erasable`; `reset_accepts_source_ancestor=true`; Compose reset stops before validation | A misconfigured reset can include source/checkout descendants. Add disposable ancestor/descendant and pre-stop rejection regressions; never reproduce deletion against operator roots. | [Root-boundary refactor](0005-runtime-refactor-safe-runtime-root-boundaries.md), resolved: protected-root containment is symmetric and shared, reset targets are revalidated before deletion and refused before any service stop, and the readiness report destination is checked against proof, database and source roots |
| `AUD-codebase-02` | Observed / blocking: readiness may write only an allowed report destination | `readiness/run.py::_persist_report`; `report_writes_inside_protected_proof_fixture=true` | An invalid roots configuration can place JSON inside a proof source subtree. Validate report destination against proof/database/source exclusions before creating directories. | [Root-boundary refactor](0005-runtime-refactor-safe-runtime-root-boundaries.md), resolved: protected-root containment is symmetric and shared, reset targets are revalidated before deletion and refused before any service stop, and the readiness report destination is checked against proof, database and source roots |
| `AUD-codebase-03` | Observed / blocking: credentials must not enter process arguments | `readiness/database.py::check_database`; `database_credential_is_in_argv=true`; existing test expects that argument | Database probe credentials can be visible in process listings. Pass the secret using the supported process environment/secret interface; invert the test expectation and check error/log redaction. | [Probe-safety refactor](0008-runtime-refactor-readiness-probe-safety.md), resolved: environment-only password transport, installed-extension applicability and bounded local HTTP verified with network-free regressions |
| `AUD-codebase-04` | Observed / blocking: readiness distinguishes available packages from installed extensions | Same database probe; `available_but_uninstalled_extensions_report_ready=true` with synthetic `pg_search=1/-` and `vector=1/-` | Required SQL capabilities may be absent despite a ready result. Parse installation separately and test selected-profile applicability without creating extensions. | [Probe-safety refactor](0008-runtime-refactor-readiness-probe-safety.md), resolved: environment-only password transport, installed-extension applicability and bounded local HTTP verified with network-free regressions |
| `AUD-codebase-05` | Observed / blocking: a verified evidence bundle must contain its artifacts | `evaluation/bundles.py::verify_run_bundle`; `bundle_verifies_external_symlink=true` | Matching bytes outside a bundle can satisfy verification through a symlink. Test nonregular entries, containment, required metadata and immutable publication boundaries. | [Bundle-validation refactor](../plan.md#refactor-evaluation-bundle-validation), routed |
| `AUD-codebase-06` | Observed / blocking: canonical contract references stay in the declared root | `contracts/canonical.py::load_canonical_model`; `canonical_loader_accepts_parent_reference=true` | The canonical loader accepts a parent reference despite registry containment checks. Reuse a rooted validator and cover absolute, parent and symlink escapes. | [Contract identity repair](0009-contract-gov-refactor-contract-identity-and-reference-validation.md), resolved: registry and canonical loaders share `resolve_rooted_reference()`, and regressions refuse parent, absolute and symlink escapes |
| `AUD-codebase-07` | Observed / blocking: schema fields have unambiguous identity | `contracts/evolution.py::schema_snapshot`; `schema_snapshot_collapses_same_field_in_distinct_schemas=true` | Two schemas with an `id` field collapse into one snapshot entry, hiding change information. Qualify identity, reject true duplicates and record fingerprint migration consequences. | [Contract identity repair](0009-contract-gov-refactor-contract-identity-and-reference-validation.md), resolved: snapshots use schema-qualified field identity, reject true duplicates, and document legacy migration plus unmigrated breaking consequences |
| `AUD-codebase-08` | Observed / blocking: configuration precedence agrees across entry points | `scripts/shared/common.sh` and `runtime/dotenv.py`; `shell_python_derived_reference_disagreement=true` | A shell environment override of RESULTS_DIR leaves a dotenv-derived RUNS_DIR inconsistent with Python expansion. Add paired fixtures for the supported dotenv grammar and derived roots. | [Configuration-parity refactor](0006-runtime-refactor-runtime-configuration-parity.md), resolved: one grammar, precedence and reference order is shared by `scripts/shared/dotenv.sh` and `runtime/dotenv.py`, and paired fixtures hold both to one result |
| `AUD-codebase-09` | Observed / blocking: task prerequisites cannot disappear during parsing | `quality/plan_model.py::read_tasks`; `plan_parser_discards_dependency_continuation=true`; `plan_summary.py::_next_task` selects priority only | Multiline dependencies are silently lost; existing tools do not validate cycles or accepted records. Preserve fields, resolve conditional/open/accepted dependencies, and test actual task eligibility. | [Record/checkpoint enforcement](0004-foundation-enforce-task-record-and-checkpoint-integrity.md), resolved: continuation lines are preserved, and dependencies, records, notes and checkpoints resolve in `make lint-spec-plan` with prerequisite-aware `make plan-status` |
| `AUD-codebase-10` | Observed baseline / blocking: required CI must pass before subsequent implementation acceptance | `runtime/__init__.py` import format/order and `tests/compose/test_profiles.py` complex combined topology assertion | Source/tests match HEAD. Repair formatting and split the test at invariant boundaries while retaining all assertions; then run the complete complexity gate and CI. | [Quality baseline repair](0003-foundation-restore-quality-gate-baseline.md), resolved: formatting/import repaired, topology test split at invariant boundaries, complete complexity gate and `make ci`/`make quality` pass |
| `AUD-codebase-11` | Static concern / blocking before service-adapter expansion: one profile policy | `runtime/compose.py`, readiness checks/database/run, and CLI contain related selection/planning logic; no profile-only failure reproduced here | Global path/password checks and command slicing can couple unrelated services. Add profile matrix fixtures and one typed service plan; preserve documented layout preparation effects. | [Service-planning refactor](0007-runtime-refactor-profile-aware-service-planning.md), resolved: shared typed profile policy, selected disk/layout checks, pure Compose base builder and rendered profile/regression matrices |
| `AUD-codebase-12` | Static concern / blocking before probe expansion: local bounded transport | `readiness/probes.py` uses redirect-following `urlopen` and unbounded response reads; inference probing uses a fixed vLLM port | Test redirect refusal, URL credentials, malformed/oversized responses, errors and configured ports with fake transports. No remote endpoint was probed to demonstrate these cases. | [Probe-safety refactor](0008-runtime-refactor-readiness-probe-safety.md), resolved: environment-only password transport, installed-extension applicability and bounded local HTTP verified with network-free regressions |
| `AUD-codebase-13` | Static contract gap / blocking before concrete adapters | `interfaces/pipeline.py`, `stores.py`, `extraction.py`, feature catalog: single archive path, underspecified artifact generation identity and string metadata anchors | Refine existing typed values using canonical contracts for multi-silo occurrence identity, structured evidence coordinates, generation refs and conditional features; avoid another engine framework. | [Stage/artifact interface refactor](../plan.md#refactor-stage-and-artifact-interface-contracts), routed |
| `AUD-codebase-14` | Observed scope limitation / blocking before concurrent heavy workers | `inference/scheduler.py` supplies placement decisions, not a host-wide lease | Extend the existing scheduler task with contention, cancellation and real one-device resource evidence. This is planned implementation, not a reproduced concurrent failure. | [Existing model scheduler task](../plan.md#implement-model-resource-scheduler), routed |
| `AUD-codebase-15` | Static concern / blocking before long pipeline runs | `observability/logging.py` uses `SimpleQueue`; sustained overload was not exercised | Extend existing telemetry work with bounded queue/overload/shutdown behavior and deterministic saturation tests. | [Existing telemetry task](../plan.md#add-progress-logging-and-resource-telemetry), routed |

## Final verification and next action

| Command or review | Result | Evidence and limits |
| --- | --- | --- |
| `make lint-md DATA_DIR=.data` | Pass | `lint-md.log`; includes documentation-link validation |
| `make plan-status DATA_DIR=.data` | Pass | 93 tasks: 82 agent, 11 human; first priority is `restore-quality-gate-baseline` |
| `python3 .data/codebase-review/20260905/review_plan.py` | Pass | `dependency-review.json`, `counts-after.json`, `plan.after.md`: 93 tasks, 241 explicit dependency edges including conditional branches; no cycles, duplicate fields or missing checkpoint ids |
| Manual dependency interpretation | Pass within declared scope | Non-task tokens `apply`/`move` are placement decisions. The four early checkpoint closures contain no human dependencies. No new product dependency checker is claimed. |
| `make -k ci DATA_DIR=.data` | Fail on baseline | `ci.log`: 168 tests pass; typing passes for 57 source files; shell lint, documentation links and spec-plan integrity pass. Formatting/import order and Radon still fail. |
| `git diff --name-only -- src tests scripts Makefile pyproject.toml uv.lock` | Empty | No production, test, build/dependency or script changes; baseline failing files match HEAD |
| `git diff --check` | Pass | No whitespace errors; changed Markdown is ASCII |

The CI failures are the existing import formatting/order in `src/arxiv_int/runtime/__init__.py`
and Radon D (23) for
`tests/compose/test_profiles.py::test_rendered_topology_has_pins_health_stop_and_mount_isolation`.
The complexity target stops at Radon, so the later cognitive-complexity subcheck is not established
by this run. Full `make quality`, real service setup, model/CUDA and provided-archive runs were not
performed. No failure or unrun check is recorded as passed.

Task counts moved from 77 to 93 (66 to 82 agent; 11 human unchanged), with eight refactors, one
enforcement task and seven checkpoint tasks added. The current review page lists the 11 affected
capabilities; none changed shipment status. No future repair or milestone task is removed by this
review. The CI repair is the first implementation prerequisite; this record remains CI-blocked
until the repair is verified and linked. Root/probe and artifact/contract repairs remain explicit
future work. No service, model job, port or external resource was started by the review.
