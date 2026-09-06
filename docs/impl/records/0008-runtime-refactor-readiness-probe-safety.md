# Readiness probe safety

## Task and scope

- Id: `refactor-readiness-probe-safety`; capability: `portable-runtime`.
- Checkpoint: `review-foundation-and-store-boundaries`.
- State: accepted.
- Source: `docs/impl/plan.md`; revision `118ea09`, initial working tree clean.
- Initial count: 88 tasks (77 agent, 11 human).
- Amendments: none.

```markdown
#### refactor-readiness-probe-safety

Harden local readiness transport and distinguish installed extensions from available packages.

- Serves: `portable-runtime` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-codebase-03, AUD-codebase-04, AUD-codebase-12](records/codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Profile-aware service planning](records/refactor-profile-aware-service-planning.md).
- User-visible outcome: Readiness keeps credentials out of process arguments and cannot report
absent extension
installation as ready or silently follow an inference probe away from the host.
- Scope boundary: Repair existing read-only probes and tests; no new inference engine, remote service,
implicit extension installation, credential rotation or running database mutation.
- Data and artifact paths: `src/arxiv_int/readiness/{database,inference,probes}.py`,
probe protocols and
`tests/readiness/`; only synthetic credential markers in fixtures.
- Execution path: Pass database credentials through a supported environment/secret boundary without values
in argv; parse available/installed identities separately; reuse resolved backend ports; bound
HTTP response bytes, redirects and time, reject credentials in URLs, and normalize transport errors.
- Acceptance gates: Regression tests assert secret-free command/log/error text, available-but-uninstalled
extensions fail applicability gates, oversized/malformed responses fail safely, nonlocal redirects
are refused and configured endpoint ports are honored; fake transports keep tests network-free.
- Documentation target: `docs/impl/current/portable-runtime.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.

```

## Implementation

Database probing reuses the pure Compose base command and environment, passing `-e PGPASSWORD`
without a value in argv. Compose resolves the value from its process environment, as implemented in
[upstream exec](https://github.com/docker/compose/blob/main/cmd/compose/exec.go).
Available and installed extension identities are parsed separately against shared profile policy;
required missing or uninstalled extensions block readiness. AGE remains optional outside graph.
Version reporting is retained with password redaction; raw query errors are replaced with a stable
failure message so transport diagnostics cannot echo credentials.

`readiness/http_transport.py` owns the bounded local HTTP implementation used by `LocalProbe`.
It accepts HTTP/HTTPS loopback endpoints only, rejects URL credentials, query/fragment components,
control characters and invalid ports, maps localhost to literal IPv4 loopback, and bypasses proxies.
It refuses every redirect without a second request, reads at most 1 MiB plus one detection byte,
and normalizes decoding, HTTP, socket and recursion errors without exception messages. Connect
uses the configured socket timeout; a remaining-budget timer shuts down the connected socket during
headers/body reads and is cancelled/joined on exit. HTTPS retains certificate verification against
the literal loopback host, so localhost-only certificates must include that loopback identity.

Inference reuses local URL validation and the existing resolved backend ports. Invalid model-list
shapes degrade endpoint readiness. Model matching is split from endpoint checking at its existing
behavioral boundary. No dependency, service startup, credential rotation or database mutation was
introduced. See [current portable runtime](../current/portable-runtime.md).

## Acceptance evidence

Commands use `DATA_DIR=/tmp/arxiv-int-probe-safety`; evidence is retained under
`$DATA_DIR/regression/20260906/`. The configured tooling location is outside this session's writable
roots, so this explicit override was used. Offline build reused the writable cache from the
accepted service-planning task: `UV_CACHE_DIR=/tmp/arxiv-int-service-planning/cache/uv`.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Database regressions before repair | `.venv/bin/python -m pytest tests/readiness/test_database.py -o cache_dir=/tmp/arxiv-int-probe-safety/cache/pytest`; `baseline.txt` | Valid-negative: four failures reproduce argv exposure, absent installation and credential-bearing version output |
| HTTP regressions before repair | `.venv/bin/python /tmp/arxiv-int-probe-safety/regression/20260906/reproduce_http.py`; `baseline-http.txt` | Valid-negative against `118ea09`: fake urlopen receives credential URL and returns ready for oversized JSON via an unbounded read |
| Secret-free commands and reports | `tests/readiness/test_database.py` | Environment contains synthetic password; argv, report and captured logs do not; query errors are stable |
| Installed applicability | `test_uninstalled_or_absent_extensions_block`, `test_age_installation_only_required_for_graph` | Missing/uninstalled/empty installation fails; graph requires AGE while core does not |
| HTTP transport safety | `tests/readiness/test_http_transport.py` | URL rejection before connection, redirect/error refusal without body reads, 1 MiB cap, invalid JSON/encoding/depth, timeout validation, deadline shutdown/cleanup, IPv6/HTTPS and error sanitization |
| Inference identity and ports | `tests/readiness/test_inference_safety.py`, `tests/readiness/test_profile_readiness.py`, `test_json_and_nondefault_port` | Invalid model shapes fail safely; URL credentials never reach injected probe; configured vLLM port 8100 retained |
| Formatting and required CI | `make format DATA_DIR=/tmp/arxiv-int-probe-safety`; `make ci DATA_DIR=/tmp/arxiv-int-probe-safety`; `ci.txt` | Pass; 304 deterministic tests and all CI checks |
| Full quality | `UV_OFFLINE=1 UV_CACHE_DIR=/tmp/arxiv-int-service-planning/cache/uv make quality DATA_DIR=/tmp/arxiv-int-probe-safety`; `quality.txt` | Pass; 304 tests, 92.73% coverage, Markdown, typing, complexity, shell, links, plan and wheel/sdist build |

Initial test scaffolding used the wrong report method; corrected before baseline evidence was
retained. Formatting requested `contextlib.suppress`; complexity gates required extracting model
matching and extension interpretation. Final documentation lint found an extra blank line and a
long prose line, which were corrected by hand. These causes
were fixed without weakening gates. Fixtures
are network-free and prove probe behavior, not real service health, archive quality or CUDA fit.

## Audit handoff

AUD-codebase-03 is resolved by environment-only password transport and redaction regressions.
AUD-codebase-04 is resolved by separate available/installed identities and profile applicability.
AUD-codebase-12 is resolved by local-only transport, byte limits, redirects refused, socket time
bounds, sanitized errors and configured-port coverage. The configured vLLM port repair was already
present in the accepted prerequisite and was retained.

Self-review covered command/environment boundaries, profile reuse, HTTP resource cleanup, malformed
responses, compatibility and evidence-to-gate mapping. `none identified` beyond the documented
intentional endpoint restrictions. No real endpoint was contacted and no background process remains.

## Close or resume

All required gates passed. Current portable-runtime documentation, record index, audit dispositions
and dependency links reference this accepted record. Only satisfied task scope was removed from
the plan: 88 to 87 tasks, agent lane 77 to 76, human lane unchanged at 11. No capability added or
removed; existing `portable-runtime` readiness is hardened. The next planned agent task after this
acceptance was contract identity repair; that work is now accepted in
[Contract identity and reference validation](0009-contract-gov-refactor-contract-identity-and-reference-validation.md).
