# Profile-aware service planning

## Task and scope

- Id: `refactor-profile-aware-service-planning`; capability: `portable-runtime`.
- Checkpoint: `review-foundation-and-store-boundaries`.
- State: accepted.
- Source: `docs/impl/plan.md`; revision `bd3a01a`, initial working tree clean.
- Initial count: 89 tasks (78 agent, 11 human).
- Amendments: none.

```markdown
#### refactor-profile-aware-service-planning

Separate service request planning from filesystem preparation and reuse one profile definition.

- Serves: `portable-runtime` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-codebase-11](records/codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Runtime configuration parity](records/refactor-runtime-configuration-parity.md).
- User-visible outcome: A core or vLLM-only request checks and prepares the selected services and reports
the same
selection in Compose, readiness and CLI help.
- Scope boundary: Keep existing operator commands and documented config/layout effects unless a specified
defect requires a regression fix; no service startup or data reset against operator roots.
- Data and artifact paths: `src/arxiv_int/runtime/compose.py`, `src/arxiv_int/readiness/{checks,run,database}.py`,
`src/arxiv_int/cli.py`, `docker/compose.yaml`, and `tests/compose/`.
- Execution path: Extract a typed service plan and shared profile/service map; derive
applicable path, password,
model and extension checks from it; separate pure command construction from layout creation;
replace positional command slicing in database probing with an explicit Compose base builder.
- Acceptance gates: Fixture cases cover core, vLLM-only, combined and disabled profiles,
non-default ports,
missing unselected archives/services, unavailable disks during status/down, and bounded command
arguments; parity with rendered Compose and existing valid commands is preserved; make ci passes.
- Documentation target: `docs/impl/current/portable-runtime.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

## Implementation

`runtime/service_plan.py` owns typed service selection, aliases, extension applicability, selected
path variables and CLI help. Compose and readiness reuse that policy; fixture rendering binds the
static `docker/compose.yaml` profile declarations to it without adding a YAML runtime dependency.
Compose's base builder is pure and database probes no longer slice an action command. Invalid log
service names, profiles, actions and negative tails fail before layout creation. Explicit profile
arguments override ambient `COMPOSE_PROFILES` values.

Path validation retains every configured containment boundary while inspecting only applicable
disks. `config` and `up` retain the common results skeleton, runs and temporary directories, and now
prepare only selected database, cache and service state roots. This intentional correction prevents
missing unselected archives and database disks from blocking a service-only request. Configuration
still requires resolved root values; it no longer requires their unselected disks to be available.
Status, down and logs remain free of layout writes and disk validation; reset retains its existing
project-wide protection and deletion policy.

The normalized full `pipeline` topology retains the existing complete workstation readiness audit.
Core-only and vLLM-only requests skip unrelated checks. vLLM selection probes its configured port
and actual Compose generation model, including when the configured pipeline backend is Ollama;
embedding/rerank models are not required from that single-model service. Database extension
requirements come from the plan. Probe credential transport and installed-extension interpretation
remain owned by [readiness probe safety](refactor-readiness-probe-safety.md).

Changed production modules: `runtime/{service_plan,compose,paths}.py`,
`readiness/{checks,run,database,inference}.py`, and `cli.py`. No dependencies or operator commands
were added. See [current portable runtime](../current/portable-runtime.md).

## Acceptance evidence

All final Make commands used `DATA_DIR=/tmp/arxiv-int-service-planning`. Build/quality also used
`UV_OFFLINE=1 UV_CACHE_DIR=/tmp/arxiv-int-service-planning/cache/uv`. The configured DATA_DIR and
user uv cache were read-only in this session. A writable cache reused the already installed cache's
setuptools 84.0.0 metadata and archive; no dependency requirement or gate was changed.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Regression before fix | `PYTHONPATH=/tmp/arxiv-int-service-planning/regression/baseline/src .venv/bin/python -m pytest tests/readiness/test_profile_readiness.py -o cache_dir=/tmp/arxiv-int-service-planning/cache/pytest`, using `git archive bd3a01a src` | valid-negative: all four cases fail on unselected archive inspection; baseline source removed after verification |
| Profile parity and disabled services | `tests/compose/test_service_planning.py::test_plan_matches_rendered_compose` | every individual profile, core/vLLM union, pipeline and full topology agree with Docker Compose rendering; no startup |
| Selected layout and missing disks | `test_only_selected_service_layout_is_prepared`, `test_vllm_up_ignores_unselected_database_disk_and_password` | selected database/cache directories only; common layout retained; unselected archive and unavailable database fixtures pass |
| Status/down/logs without disks | `test_observational_commands_do_not_prepare_unavailable_disks` | all three run through a fake runner without modifying unavailable disk fixtures |
| Bounded pure commands and help | `test_log_service_arguments_are_bounded_before_layout`, `test_base_builder_and_log_command_are_pure`, `test_cli_help_uses_shared_profile_policy` | option-like, unknown and unselected service arguments fail before writes; tail zero/follow remain valid; shared CLI help passes |
| Readiness applicability and port | `tests/readiness/test_profile_readiness.py` | core, vLLM-only, union and cadvisor skip unselected disks/services/passwords/models/extensions; vLLM model served on port 8100 agrees with Compose configuration |
| Existing behavior | existing `tests/config/`, `tests/compose/`, `tests/readiness/` | reset protection, default pipeline audit, model/port resolution and root safety regressions remain passing |
| Required CI | `make ci DATA_DIR=/tmp/arxiv-int-service-planning` | pass; 259 tests, formatting, lint, typing, complexity, shell, links and plan integrity |
| Full quality | `UV_OFFLINE=1 UV_CACHE_DIR=/tmp/arxiv-int-service-planning/cache/uv make quality DATA_DIR=/tmp/arxiv-int-service-planning` | pass; 259 tests, 92.43% coverage, Markdown and wheel/sdist build |

Evidence logs are retained under the overridden `$DATA_DIR/regression/`: `baseline-readiness.txt`,
`ci.txt`, `quality.txt`, `build.txt` and `build-offline.txt`. Initial attempts encountered read-only
cache errors, complexity findings, a duplicate test basename and an argparse wrapping assertion;
these were corrected. The first writable-cache build could not resolve PyPI DNS; the offline cache
build passed. Fixtures prove selection and command/layout behavior, not real archive quality,
service health or CUDA fit. No service was started and no reset ran against operator roots.

## Audit handoff

`AUD-codebase-11` is resolved: one typed profile policy drives Compose, readiness, extension
applicability and CLI help; profile matrices reproduce the original coupling and verify its repair.
Self-review covered shared policy, path protection, command purity, selected model identities and
compatibility. `none identified` in the reviewed scope. Existing probe-safety concerns remain
assigned to `refactor-readiness-probe-safety`; this task does not claim to resolve them.

## Close or resume

Required acceptance passed. Current portable-runtime documentation, record index, dependency and
AUD-codebase-11 links now reference this record. Only this task was removed from the plan: 89 to 88
tasks, agent lane 78 to 77, human lane unchanged at 11. No capability added or removed;
`portable-runtime` now has profile-aware service planning and preparation. Next eligible task:
`refactor-readiness-probe-safety`. No process or temporary baseline checkout remains running.
