# Task Record

## Task and scope

- Id / capability / checkpoint: `refactor-runtime-configuration-parity` / `portable-runtime` /
  `review-foundation-and-store-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `refactor-runtime-configuration-parity`; code revision `2e051d0`
  with a clean working tree at task start.
- Accepted task:

```markdown
#### refactor-runtime-configuration-parity

Resolve the same configuration through Make, direct CLI and readiness without precedence drift.

- Serves: `portable-runtime` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-codebase-08](records/codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Safe runtime root boundaries](records/refactor-safe-runtime-root-boundaries.md).
- User-visible outcome: Operator overrides, referenced roots and selected model/port values agree
across entry
points, including roots containing spaces and an alternate checkout.
- Scope boundary: Consolidate configuration ownership and the supported dotenv subset; preserve documented
precedence, append-sync behavior and local path rules. Do not rewrite the operator environment.
- Data and artifact paths: `src/arxiv_int/runtime/{config,dotenv,inference_config}.py`, shared root discovery,
`scripts/shared/common.sh`, Make cache setup, and `tests/config/`.
- Execution path: Add a paired shell/Python regression for an overridden RESULTS_DIR referenced by RUNS_DIR;
resolve references after precedence, reject cyclic/missing references, document unsupported syntax,
and centralize applicable port/backend settings and project-root discovery without parallel parsers.
- Acceptance gates: Paired fixtures agree for defaults, overrides, nested references, quotes/spaces,
explicit
empty values, invalid inputs and foreign working directories; no environment/file mutation occurs
during reads; cache placement follows the selected DATA_DIR; make ci passes.
- Documentation target: `docs/impl/current/portable-runtime.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

One configuration grammar, precedence order and root discovery now serve Make, the direct CLI and
readiness.

- `src/arxiv_int/runtime/dotenv.py` owns the documented grammar and, new here,
  `expand_references()`. References resolve **after** precedence rather than during file reading,
  recursively, and only in `*_DIR` variables, so a `$` in a password or URL stays literal.
  A cycle, an undefined name and an empty referenced value are each refused by variable name.
  Quote stripping is retried after a trailing `" #"` comment is removed, so
  `ARCHIVE_DIR="source archive"  # note` no longer keeps its quotes.
- `src/arxiv_int/runtime/config_schema.py` is a new module owning the variable registry: names,
  documented defaults, the service ports, `selected()`, `apply_defaults()` and `check_ports()`.
  `ConfigurationError` moved here so the schema can refuse a value; `runtime.config` re-exports it
  and no caller changed. It also keeps `config.py` at 179 lines after the new resolution order.
- `src/arxiv_int/runtime/config.py` now resolves in a fixed order: precedence, documented defaults,
  port validation, backend defaults, required roots, symbolic derived defaults
  (`${RESULTS_DIR}/runs`), reference expansion, then path resolution. An explicitly empty value for
  a defaulted variable selects the documented default instead of resolving to an empty path; a
  required operator root left empty is still reported as missing.
- `src/arxiv_int/runtime/project_root.py` is a new module owning checkout discovery: explicit
  option, then `PROJECT_ROOT`, then the module's own checkout, then the working directory. It
  replaces the two divergent implementations in `runtime/config.py` (working directory first, no
  environment) and `readiness/run.py` (working directory first, no validation, silent fallback).
  `quality/project_root.py` now reuses its `ascend_to_root()` walk with the stricter repository
  markers. Readiness reports a non-checkout root as a blocked `config.root` finding.
- `src/arxiv_int/runtime/inference_config.py` gained `selected_backend()` and
  `inference_base_url()`; `readiness/inference.py` uses them, so the vLLM probe follows the
  configured `VLLM_PORT` instead of the fixed `http://127.0.0.1:8000`. The six service ports from
  `docker/compose.yaml` are now resolved configuration with the same defaults, and a non-numeric or
  out-of-range port is refused before any command runs.
- `scripts/shared/dotenv.sh` is a new shared script, sourced by `scripts/shared/common.sh`, that
  implements the same grammar, precedence, defaults and reference order in dependency-free bash.
  It replaces `arxiv_int_source_dotenv`, which used `set -a` plus `.` on the file: that executed
  the file as shell, expanded references in file order **before** the process environment was
  restored, and expanded them in every variable. It now parses instead of executing and exports
  resolved absolute `*_DIR` values, which the Python entry points re-resolve to the same paths.
  `common.sh` exports `PROJECT_ROOT` so a CLI call from another checkout keeps the Make checkout.
- `Makefile` derives `DATA_ROOT` from the new `arxiv_int_data_root` instead of its own
  `DATA_DIR ?= .data` default, so Ruff, mypy, pytest and complexipy caches follow the selected
  `DATA_DIR`. `make DATA_DIR=...` still overrides. In this checkout the caches move from
  `<checkout>/.data` to the `.env` value, which is the drift this gate names.

Compatibility: shell-exported `*_DIR` values are now absolute (previously raw), matching what
Python resolves; `arxiv_int_source_dotenv` is gone in favor of `arxiv_int_resolve_env`; a `.env`
that relied on shell expansion beyond the documented subset (command substitution, escapes,
`${NAME:-default}`) is now refused by name in both implementations rather than silently executed.
`.env.example` documents the supported subset and the unsupported syntax. No public Python
function was removed.

Current state: [Portable runtime](../current/portable-runtime.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| AUD-08 drift reproduced at `2e051d0` | Fixture `.env` with `RESULTS_DIR=dotenv-results`, `RUNS_DIR=${RESULTS_DIR}/journal` and a process `RESULTS_DIR=process-results`, resolved by the stashed `common.sh` and `load_runtime_config` | valid-negative; shell reported `RUNS_DIR=dotenv-results/journal` while Python reported `<root>/process-results/journal` |
| Same fixture after the change | Re-run of the same reproduction | pass; both report `<root>/process-results/journal` |
| Paired defaults, overrides, nested references, quotes/spaces, empty values, environment-only roots | `uv run pytest tests/config/test_parity.py::test_shell_and_python_resolve_the_same_configuration` (6 cases) | pass; each case compares the shell-resolved environment fed back through `load_runtime_config` against a direct load |
| Foreign working directory and an alternate checkout | `uv run pytest tests/config/test_parity.py::test_an_alternate_checkout_keeps_its_own_roots` and the parametrized cases, which all run from an unrelated directory | pass; each checkout keeps its own roots |
| Invalid input refused by both | `uv run pytest tests/config/test_parity.py::test_shell_and_python_refuse_the_same_invalid_configuration` (cyclic, missing, empty, malformed) | pass; the shell exits non-zero with the same message the `ConfigurationError` carries |
| No environment or file mutation during reads | `uv run pytest tests/config/test_parity.py::test_resolution_mutates_neither_the_process_environment_nor_the_checkout` | pass; `os.environ`, the `.env` bytes and the checkout listing are unchanged after both readers |
| Cache placement follows the selected DATA_DIR | `uv run pytest tests/compose/test_make.py::test_make_tool_caches_follow_the_selected_data_dir` | pass; `make --dry-run test` matches `arxiv_int_data_root`, and `DATA_DIR=` on the command line still overrides |
| Selected port and model values agree across entry points | `uv run pytest tests/compose/test_profiles.py::test_rendered_ports_follow_the_resolved_configuration` and `tests/readiness/test_workstation.py::test_inference_probe_follows_the_configured_backend_and_port` | pass; rendered Compose ports equal the resolved configuration and `VLLM_PORT=8100` moves both the rendered port and the readiness probe URL |
| Port and project-root validation | `uv run pytest tests/config/test_layers.py::test_service_ports_carry_documented_defaults_and_reject_invalid_values` and `::test_project_root_comes_from_the_option_then_the_environment` | pass; non-numeric, out-of-range and non-checkout values are refused by name |
| Regressions fail without the fix | `git stash push -- src scripts Makefile && uv run pytest tests/config/test_parity.py tests/compose/test_make.py ...` | valid-negative; all 15 new tests failed at `2e051d0`, then passed after `git stash pop` |
| Operator `.env` still resolves identically | `arxiv_int_resolve_env` and `load_runtime_config()` against this workstation's real `.env` | pass; both report the same `RESULTS_DIR`, `RUNS_DIR` and `DATA_DIR`; read-only, no command was run against a service |
| Required CI | `make ci` | pass; 229 tests, format, lint, typing, complexity, shell lint, doc links, plan integrity |
| Infrastructure/documentation gate | `make quality` | pass; coverage 91.94% against the 90% floor, Markdown lint, wheel and sdist build |

Every fixture ran against disposable `tmp_path` checkouts. The only real-environment evidence is the
read-only resolution of this workstation's `.env`; no service was started, no reset was applied and
no operator root was written. Fixture parity does not prove behavior on another shell than bash or
on a filesystem with different symlink semantics.

## Audit handoff

`AUD-codebase-08` is resolved by this record: the shell no longer executes `.env`, both readers
share one documented grammar and one resolution order, and paired fixtures hold them to one result
for an overridden `RESULTS_DIR` referenced by `RUNS_DIR`.

- `AUD-runtime-configuration-parity-1`, nonblocking, owner [review-foundation-and-store-boundaries](../plan.md#review-foundation-and-store-boundaries):
  observation at `scripts/shared/dotenv.sh` and `src/arxiv_int/runtime/dotenv.py`. Invariant: one
  grammar, two implementations. Evidence: `tests/config/test_parity.py` compares them for the cases
  above, but the fixture list is the only thing binding them; a future grammar change can still be
  made in one file alone. Impact: a silent divergence would return the class of defect AUD-08
  named. Next check: when the bootstrap can assume an interpreter, consider generating the shell
  resolver from the Python grammar, or extend the fixture table with a shared case file both read.
  Disposition: open.
- `AUD-runtime-configuration-parity-2`, nonblocking, owner [review-foundation-and-store-boundaries](../plan.md#review-foundation-and-store-boundaries):
  observation at `scripts/shared/dotenv.sh::arxiv_int_resolve_env`. Invariant: the process
  environment outranks `.env`. Evidence: the shell tests a dotenv name with `[[ -v NAME ]]`, which
  is also true for a non-exported shell variable of that name in an interactive session, while
  Python reads `os.environ`. Impact: an operator who sets an unexported uppercase shell variable
  matching a runtime name would see the shell prefer it and Python not. Next check: compare against
  `declare -p` export state if a real case appears. Disposition: open.

## Close or resume

Every required gate passed: `make ci` and `make quality`, the paired parity and refusal fixtures,
the Make cache-placement test, the port and backend agreement tests, and the valid-negative run at
`2e051d0`. No gate is outstanding. Next action: none for this task; the two audit notes above are
carried to `review-foundation-and-store-boundaries`.

Updates made: `docs/impl/current/portable-runtime.md` describes the fixed resolution order, the
shared root discovery, the centralized ports and backend endpoint, the parsing shell resolver and
the Make cache root; `.env.example` documents the supported and unsupported syntax; this record is
linked from the [record index](README.md); the dependency reference in
`refactor-profile-aware-service-planning` and the `AUD-codebase-08` disposition now point at this
record. Plan counts: 90 tasks before, 89 after (agent lane 79 to 78). Capabilities changed: none
added or removed; `portable-runtime` gains one configuration grammar and one root discovery across
Make, the CLI and readiness.
