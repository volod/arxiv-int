# Portable Runtime

Runtime configuration and path behavior lives cohesively under `src/arxiv_int/runtime/`. The
top-level package contains only its initializer, CLI entry point, and metadata module; runtime
implementation details do not expand that namespace.

## Layered configuration

`arxiv_int.runtime.load_runtime_config()` resolves runtime values with CLI, process environment,
checkout `.env`, and documented defaults in descending precedence. It discovers or accepts an
explicit project root, resolves relative paths and `${VARIABLE}` references from that checkout, and
returns a typed immutable `RuntimeConfig`. Missing operator roots identify every variable the
operator must set. Rendering is stable and masks passwords, tokens, secrets, and database URLs.
`arxiv_int.runtime.config_model` owns the immutable values, while `arxiv_int.runtime.dotenv` keeps
file parsing dependency-free.

The three required operator placements are one or more archive silos, `RESULTS_DIR`, and
`PGDATA_DIR`. `ARCHIVE_DIR` is the one-silo form with id `default`; additional or alternative silos
use `ARCHIVE_SILO_<ID>_DIR`, with underscores in the variable id rendered as hyphens. `RUNS_DIR`,
`SERVICE_STATE_DIR`, `MODEL_CACHE_DIR`, and `TMP_DIR` derive from `RESULTS_DIR` unless individually
overridden. Optional `PG_WAL_DIR` and `PG_TABLESPACE_<NAME>_DIR` roots remain unset by default.
`DATA_DIR` remains checkout-relative developer-tooling state and is not a runtime output root. There
are no development-only archive aliases or result roots; stage implementations use the normal
operator paths immediately.

`scripts/shared/common.sh` loads the same checkout `.env` without replacing variables already in
the process environment. This preserves Make and shell overrides while retaining the adaptive uv
link mode and repository-local tool-cache behavior.

## Path safety and storage evidence

`arxiv_int.runtime.validate_runtime_paths()` operates on resolved real paths, accumulates all
findings, and does not create directories. It refuses filesystem-root targets; source, results,
database, WAL, and tablespace overlaps; output inside or around the checkout; symlink-resolved
escapes; unreadable sources; and unwritable or full destinations. Archive directories may have host
write permission: read-only is a pipeline access contract, not a filesystem-mode requirement.
Database roots on a filesystem without PostgreSQL-compatible ownership and exclusive-use semantics
are blocked. Rotational storage is accepted for database, scratch, and model placements; its measured
flag is informational. Non-owning service-state placements remain degraded warnings.

`arxiv_int.runtime.inspect_filesystem()` records the resolved path, filesystem type, device id,
rotational flag when the operating system exposes it, accessible free bytes, ownership capability,
and read-only mount state. This evidence is retained with every configured placement and is exposed
to later readiness, forecast, and run-manifest work. `arxiv_int.runtime.path_model` owns the typed
association between each variable, resolved path, and storage class.

After a report has no blocking findings, `create_results_layout()` creates the fixed
`normalized/`, `quarantine/`, `proofs/`, and `exports/` trees, the four resolved derived roots, and
the configured PostgreSQL, WAL, and tablespace directories. New database-class directories use
owner-only mode even beneath a group-writable storage root. It creates no corpus artifact and
starts no process or container.

## Operator interface

`arxiv-int config show --redact`, wrapped by `make config`, loads and validates configuration,
creates the empty runtime layout, and prints redacted resolved values plus storage class,
filesystem, device, rotational, and free-space evidence. CLI root options override both the process
environment and `.env`. The command exits non-zero on missing or unsafe configuration and never
logs configured secrets.

## System readiness

`arxiv-int readiness`, wrapped by `make readiness`, accumulates configuration, tool, RAM/GPU, path,
filesystem, free-space, Compose health, database extension, migration, contract, local inference API,
and configured-model checks into one report. Every configured root is represented once with its
resolved path, required storage class, filesystem type, device id, rotational flag, accessible free
bytes, and combined placement status. The path check reuses the same validation as runtime startup,
so an unsupported or non-owning database filesystem is blocked and non-owning service state is
degraded. Rotational disks do not degrade readiness.

Checks have a configurable per-operation timeout and continue after individual failures. Non-ready
findings carry an operator-facing next command or `.env` change. Ready, blocked, and degraded reports
exit `0`, `1`, and `2`, respectively. Console output never renders configuration values marked as
passwords, secrets, tokens, or database URLs. On an interactive terminal, degraded finding lines are
yellow and blocked finding lines are red; redirected output and JSON remain free of terminal escape
codes. An atomic JSON form with mode `0600` is written to
`$RESULTS_DIR/reports/readiness.json`; `--json-report` may select another location beneath
`RESULTS_DIR`, and `--no-json-report` disables persistence.

Console findings are visually separated by environment/tools, host resources, configuration,
storage, services, database, contracts, inference, and report persistence. Bootstrap additionally
labels dependency setup, package identity, and readiness phases. These headings affect presentation
only; JSON finding names and statuses retain their existing interface.

The readiness audit does not create runtime layouts, install packages, pull models, start or alter
services, enable extensions, or apply migrations. Its only write is the requested readiness report.
Contract and migration checks describe not-yet-shipped registries as not applicable, allowing the
audit to remain accurate as later capabilities add those assets. When the database is healthy, the
extension check connects with the configured `POSTGRES_USER` / `POSTGRES_DB` role rather than peer
auth as the container OS UID, because Compose runs the database as `RUNTIME_UID`. The setup and
remediation workflow is in the [workstation setup guide](../../guide/setup.md).

## Local service topology

`docker/compose.yaml` defines one loopback-only bridge topology with explicit profiles. `core` runs
the database, `graph` adds the project-owned AGE Viewer image, `ui` adds Grafana,
`observability` adds Prometheus and its PostgreSQL exporter, `vllm` adds the NVIDIA-backed OpenAI
server, and the separate `cadvisor` profile opts into privileged host-container metrics. Database
consumers activate the same database service; Ollama remains a host service reachable through the
`host.docker.internal` host-gateway alias. vLLM receives all host NVIDIA devices and configurable
tensor parallelism; services without CUDA work remain CPU-only.

The operator alias `pipeline` expands to `core ui observability`. It is the default for readiness and
service Make/CLI commands. The normal inference check targets a running host Ollama service. vLLM is
an alternate only when `vllm` is explicitly included in `SERVICE_PROFILES` and
`INFERENCE_BACKEND=vllm` is configured. `graph`, `vllm`, and privileged `cadvisor` remain explicit
opt-ins.

`runtime/inference_config.py` resolves generation defaults after configuration precedence:
`qwen3.8:27b` for Ollama, or `VLLM_MODEL` and `VLLM_MODEL_REVISION` for vLLM. Explicit
`GENERATION_MODEL` and `GENERATION_MODEL_REVISION` override the active backend defaults. Compose
receives the separate vLLM settings, so the default Ollama tag never replaces its Hugging Face model
identifier. Readiness checks the resolved generation model on the selected backend. Defaults do not
download models or constitute a model quality evaluation.

`.env.example` shows `GENERATION_MODEL=qwen3.8:27b` for Ollama with the revision left unset.
`GENERATION_MODEL_REVISION` applies only to vLLM and identifies a commit in the selected Hugging Face
model repository; the template includes the paired revision example and backend-switch instructions.

The configured-host bootstrap confirms the Ollama endpoint and the default generation model are
available, recorded in `$RESULTS_DIR/reports/readiness.json`. Overall readiness remains degraded for
stopped Compose services. Rotational storage checks pass. The model-selection refactor passes
`make ci` with 160 tests and `make services-config`; it starts no service or model download.

External images carry both an exact version and an immutable registry digest. AGE Viewer carries a
project-owned version while its image build remains downstream work. Every service has a healthcheck
and a bounded stop grace period. The PostgreSQL exporter healthcheck probes `/metrics` because that
image has no `/health` route, and its `DATA_SOURCE_NAME` stays on one Compose line so YAML folding
cannot insert a space before the host. Every published port binds to `127.0.0.1`; vLLM is absent
unless its profile is selected; cAdvisor does not mount the host root.

The operator entry point loads the same layered runtime configuration and passes Compose an explicit
project directory and `.env` path. It replaces host mount variables in memory with resolved absolute
paths, injects `RUNTIME_UID` and `RUNTIME_GID` from the invoking process, performs the runtime
preflight before config validation or startup, and creates only the documented layout plus
per-service state directories. The database, Grafana, Prometheus, AGE Viewer, and vLLM services run as
that operator UID so bind-mounted artifacts remain host-writable; privileged cAdvisor does not.
The database alone mounts `PGDATA_DIR`. A
configured `PG_WAL_DIR` and any `PG_TABLESPACE_<NAME>_DIR` become generated, short-lived Compose
overrides mounted only into the database; the override contains no secrets and is removed after the
command. Grafana, Prometheus, and AGE Viewer each receive only their own writable
`SERVICE_STATE_DIR` child. Grafana provisioning and Prometheus scrape configuration mount read-only
from `docker/`. No current service consumes archive files or pipeline result files, so those roots
are not mounted. The service preflight consequently excludes `PROOF_ARCHIVE_DIR`; its independent
read-without-modification proof-run contract remains enforced by pipeline behavior and future proof
commands; ordinary host write permission is accepted.

A `PGDATA_DIR` initialized under the previous image-default UID (typically 999) must be reassigned to
the operator once before `make services-up` can pass the writable-path preflight, for example
`docker run --rm -v "$PGDATA_DIR:/data" alpine chown -R "$(id -u):$(id -g)" /data`.

`make services-up` starts `SERVICE_PROFILES=pipeline` by default, waits for health, and refuses a
database-bearing profile until `POSTGRES_PASSWORD` is configured. `make services-config` validates
without starting containers. The vLLM defaults pin v0.26.0 plus the official Qwen3.8 27B FP8 model
revision, allow 24 GB of CPU offload for a 16 GB GPU host, and cap the initial context at 32,768
tokens; `.env` can tune tensor parallelism, offload, GPU utilization, and context length.
`make services-status`, `make logs`, and `make services-down` remain
available without rerunning the mutating path preflight, so an operator can inspect or stop the
project even when a runtime disk is unavailable. `make services-down` stops Compose containers and
keeps bind-mounted roots (`PGDATA_DIR`, `SERVICE_STATE_DIR`, `MODEL_CACHE_DIR`, and optional WAL or
tablespace directories) intact for the next `make services-up`. `make services-reset` also stops
containers, then lists those service-data roots; pass `APPLY=1` (or `arxiv-int services reset
--apply`) to erase their contents after stop. Reset refuses the checkout, archive silos,
`PROOF_ARCHIVE_DIR`, and `RESULTS_DIR` itself. `LOG_SERVICES`, `LOG_TAIL`, and `LOG_FOLLOW=1`
control bounded log selection. `make graph-up` and `make ui-up` are profile shortcuts; additional or
combined profiles use `SERVICE_PROFILES="core ui observability"`.

## Tests and verification

Tests under `tests/config/` cover layer precedence, shell precedence, checkout and current-directory
independence, paths containing spaces, named silos, derived overrides, variable references,
redaction, missing values, root and symlink hazards, all root-overlap boundaries, readable source
permissions, writable proof-directory acceptance, free space, distinct device evidence, results
layout creation, and
storage-class refusal versus warning fixtures. Tests under `tests/compose/` render every profile and
the supported combined topology through Docker Compose without starting services. They cover image
pins, loopback ports, healthchecks, stop policy, generated WAL and tablespace mounts, writable state
isolation, read-only provisioning, `pipeline` alias expansion, required-service healthchecks and
`up --wait`, password refusal, cleanup, quiet redaction, and the Make entry points. Readiness
operator scenarios cover ready, degraded, and blocked aggregation; command
timeouts; unavailable services and inference; model presence; unsupported, non-owning, and
rotational storage; consolidated root evidence; report containment and permissions; distinct exit
codes; and secret redaction without network access. CLI coverage proves explicit config options and
redacted output. Configuration and rendered Compose checks cover backend defaults, operator model
overrides, and separation of Ollama tags from vLLM identifiers. The required
format, lint, typing, complexity, shell, documentation, plan-integrity, and deterministic test gates
pass.
