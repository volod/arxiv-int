# Task Record

## Task and scope

- Id: `exclude-heavy-docker-and-llama-smokes`; capability: `project-foundation`.
- State: accepted after the required gates below passed.
- Source: operator request after
  [0038](0038-eval-found-review-inference-and-evaluation-boundaries.md); not a plan.md task.
- Accepted task:

```markdown
#### exclude-heavy-docker-and-llama-smokes

Keep GitHub and regular CI Docker-free, drop llama3.2:3b pytest smokes, and use Qwen or Gemma.

- Serves: `project-foundation` -- [CLI and Make interface](../design/spec.md#cli-and-make-interface)
- Agent status: CLEAR
- Dependencies: [Inference and evaluation boundary review](0038-eval-found-review-inference-and-evaluation-boundaries.md).
- User-visible outcome: `make ci` / `make test` / GitHub Actions do not start Docker; host CUDA
  checks are operator commands; inference tests and the model registry use Qwen or Gemma families.
- Scope boundary: Remove llama3.2:3b pytest smokes and registry entries. Mark tests that invoke the
  Docker daemon `heavy`. Keep sqlglot and mocked Compose planning in the regular suite. Do not
  change the production Ollama default `qwen3.8:27b` or the pinned vLLM Qwen 27B FP8 revision.
- Data and artifact paths: `configs/models/registry.json`, `pyproject.toml`, `Makefile`,
  `tests/compose/`, `tests/integration/`, `tests/inference/`, `docs/impl/current/`.
- Execution path: Delete host-smoke pytest files; replace llama ids with `gemma3:4b`; add pytest
  marker `heavy` and `-m "not heavy"` on `make test`; skip live SQL in `make contracts-evolution`.
- Acceptance gates: `make test` deselects `heavy` tests; `make contracts-evolution` skips disposable
  Postgres; registry and inference tests contain no llama3.2:3b; `make ci` passes.
- Documentation target: [Developer tooling](../current/developer-tooling.md)
- Review checkpoint: none; ad hoc policy change after 0038.
```

- Amendments: none.

## Implementation

- Deleted `tests/inference/test_host_smoke.py` and `tests/inference/test_host_scheduler_smoke.py`.
  Host CUDA checks stay operator commands (`make inference-fit`, `make inference-schedule`), not
  pytest.
- Replaced registry and test ids `llama3.2:3b` with `gemma3:4b` (latest Gemma family size that
  fits a 16 GB GPU). Production generation remains `qwen3.8:27b` / `Qwen/Qwen3.8-27B-FP8`.
- Size-token fallback treats `<=4b` as the small envelope so unlisted `gemma3:4b` is not estimated
  as an 8 GB mid-size model.
- Registered pytest marker `heavy`. `make test`, `make coverage`, and therefore `make ci` /
  `make ci-github` pass `-m "not heavy"`. `make test-heavy` selects the marker.
- Marked live Docker suites, Compose `docker compose config` tests (including
  `test_plan_matches_rendered_compose`), and disposable baseline-SQL apply `heavy`. Mocked Compose
  planning, image-pin file checks, and disposable-SQL unit stubs stay in the regular suite.
- `make contracts-evolution` (used by `make ci`) now passes `--skip-live-sql`. Disposable Postgres
  apply is `make contracts-evolution-live`.

Current-state: [Developer tooling](../current/developer-tooling.md),
[Local inference](../current/local-inference.md), [Contracts](../current/contracts.md).

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Regular suite excludes heavy | `make test` | 885 passed, 45 deselected; no Docker daemon |
| Evolution without Docker | `.venv/bin/arxiv-int contracts evolution --skip-live-sql` | pass; 20 contracts |
| No llama3.2:3b in tests/registry | `configs/models/registry.json`; `tests/inference` | pass; `gemma3:4b` + `qwen3.8:27b` |
| Heavy Compose/SQL still exist | `pytest --collect-only -m heavy` on compose/sql tests | 17 + 9 + 1 collected |
| Formatting/lint/type/docs | `make format`; ruff; mypy; doc-links; spec-plan; pymarkdown on edited docs | pass |
| Remaining ci-checks via venv | complexity, shell-lint, contracts check, db check, ontology, schemas, identity, fixtures | pass |
| Full `make ci` Make recipe | uv sync inside `contracts-check` | not-run here; PyPI blocked in sandbox. GitHub runs `make ci-github` with network |

## Audit handoff

`none identified` for this policy change. Historical CUDA smoke evidence in 0031/0032/0038 remains
as accepted-record text; those pytest files are no longer the verification path.

## Close or resume

Passed `make test` (885 / 45 deselected) and the ci-check CLIs against the existing venv. Full
`make ci` Make recipe was not executed in this sandbox because `contracts-check` runs `uv sync`
against PyPI. GitHub Actions remains `make ci-github` and will pick up `-m "not heavy"` plus
`--skip-live-sql`. Plan counts unchanged (ad hoc). Next unused record: 0040.
