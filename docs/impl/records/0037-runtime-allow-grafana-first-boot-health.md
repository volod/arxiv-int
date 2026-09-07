# Allow Grafana First-Boot Health

## Task and scope

- Id: `allow-grafana-first-boot-health`; capability: `portable-runtime`;
  checkpoint: `review-foundation-and-store-boundaries`.
- State: accepted after the required gates below passed.
- Source: ad hoc operator request; Grafana container stayed `Waiting` then `unhealthy` during
  `make setup` while SQLite migrations were still running. Code revision is the working tree
  with this Compose healthcheck change; unrelated dirty evaluation-foundation files were left
  untouched.
- Accepted task:

```markdown
#### allow-grafana-first-boot-health

Keep Compose `--wait` from failing while Grafana finishes first-boot SQLite setup.

- Serves: `portable-runtime` -- [Docker and local-service topology](../design/spec.md#docker-and-local-service-topology)
- Agent status: CLEAR
- Dependencies: [Retryable setup](0022-runtime-implement-retryable-setup-command.md).
- User-visible outcome: `make setup` and `make services-up` wait long enough for Grafana to
  become healthy on a fresh `SERVICE_STATE_DIR` bind mount.
- Scope boundary: Adjust the Grafana Compose healthcheck and first-boot SQLite/plugin settings
  only. Do not move Grafana state off `SERVICE_STATE_DIR`, change the Grafana image pin, or
  alter other services.
- Data and artifact paths: `docker/compose.yaml`, `tests/compose/test_profiles.py`,
  `docs/impl/current/portable-runtime.md`.
- Execution path: Recreate Grafana from the updated Compose file after the healthcheck change;
  do not erase existing Grafana state.
- Acceptance gates: Grafana healthcheck start period covers measured first-boot SQLite
  migrations; WAL and disabled plugin preinstall are present in the rendered Compose config;
  `tests/compose/test_profiles.py` and `make ci` pass.
- Documentation target: `docs/impl/current/portable-runtime.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none.

## Implementation

Grafana 12.4 first boot ran 787 SQLite migrations against
`${SERVICE_STATE_DIR}/grafana` and did not bind `:3000` until about six minutes after start.
The previous healthcheck used `start_period: 30s` and 12 retries at 10s, so Compose marked the
container unhealthy at ~150s while `wget` still received connection refused. Plugin preinstall
also downloaded `grafana-metricsdrilldown-app` during that startup.

`docker/compose.yaml` now gives Grafana 60 healthcheck retries at 10s (ten minutes) instead of
`start_period: 10m`, because the Compose YAML language service reports that key as a duplicate
on this service. SQLite WAL is enabled, and `GF_PLUGINS_PREINSTALL_DISABLED=true`. Subsequent
starts reuse `grafana.db` and become healthy without waiting out the retry budget. Grafana
remains on operator UID bind mounts under `SERVICE_STATE_DIR`.

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| First-boot wait | `docker logs` / health inspect on `arxiv-int-grafana-1` | HTTP listen at ~6 minutes; 30s start period marked unhealthy at ~150s |
| Rendered Compose | `tests/compose/test_profiles.py::test_grafana_healthcheck_covers_first_boot_sqlite_migrations` | pass |
| Deterministic tests | `make ci` | pass; 893 passed, 20 skipped |
| Service recreate | `make services-up` | Grafana healthy on existing `grafana.db` |
| Operator setup | `make setup` | `services: selected services started`; Grafana healthy |

## Audit handoff

`none identified` with reviewed scope `docker/compose.yaml` Grafana service, the Compose profile
tests, and portable-runtime current-state text.

## Close or resume

Required gates passed. Next action: none for this request. Plan counts unchanged at 78 tasks
(68 agent, 10 human). Capability `portable-runtime` now waits 10 minutes for Grafana first-boot
SQLite migrations; this was not a planned task.
