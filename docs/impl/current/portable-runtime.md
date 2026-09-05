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
`DEV_RESULTS_DIR`, `SERVICE_STATE_DIR`, `MODEL_CACHE_DIR`, and `TMP_DIR` derive from
`RESULTS_DIR` unless individually overridden. Optional `PG_WAL_DIR` and
`PG_TABLESPACE_<NAME>_DIR` roots remain unset by default. `DEV_ARCHIVE_DIR` defaults to
`PROOF_ARCHIVE_DIR`, while `DATA_DIR` remains checkout-relative developer-tooling state and is not a
runtime output root.

`scripts/shared/common.sh` loads the same checkout `.env` without replacing variables already in
the process environment. This preserves Make and shell overrides while retaining the adaptive uv
link mode and repository-local tool-cache behavior.

## Path safety and storage evidence

`arxiv_int.runtime.validate_runtime_paths()` operates on resolved real paths, accumulates all
findings, and does not create directories. It refuses filesystem-root targets; source, results,
database, WAL, and tablespace overlaps; output inside or around the checkout; symlink-resolved
escapes; unreadable sources; unwritable or full destinations; and a writable
`PROOF_ARCHIVE_DIR`. Database roots on a filesystem without PostgreSQL-compatible ownership and
exclusive-use semantics are blocked. Rotational database, scratch, and model placements and
non-owning service-state placements are degraded warnings that name the variable to move.

`arxiv_int.runtime.inspect_filesystem()` records the resolved path, filesystem type, device id,
rotational flag when the operating system exposes it, accessible free bytes, ownership capability,
and read-only mount state. This evidence is retained with every configured placement and is exposed
to later doctor, forecast, and run-manifest work. `arxiv_int.runtime.path_model` owns the typed
association between each variable, resolved path, and storage class.

After a report has no blocking findings, `create_results_layout()` creates the fixed
`normalized/`, `quarantine/`, `proofs/`, and `exports/` trees, the five resolved derived roots, and
the configured PostgreSQL, WAL, and tablespace directories. New database-class directories use
owner-only mode even beneath a group-writable storage root. It creates no corpus artifact and
starts no process or container.

## Operator interface

`arxiv-int config show --redact`, wrapped by `make config`, loads and validates configuration,
creates the empty runtime layout, and prints redacted resolved values plus storage class,
filesystem, device, rotational, and free-space evidence. CLI root options override both the process
environment and `.env`. The command exits non-zero on missing or unsafe configuration and never
logs configured secrets.

## Local service topology

`docker/compose.yaml` defines one loopback-only bridge topology with explicit profiles. `core` runs
the database, `graph` adds the project-owned AGE Viewer image, `ui` adds Grafana,
`observability` adds Prometheus and its PostgreSQL exporter, `vllm` adds the NVIDIA-backed OpenAI
server, and the separate `cadvisor` profile opts into privileged host-container metrics. Database
consumers activate the same database service; Ollama remains a host service reachable through the
`host.docker.internal` host-gateway alias. vLLM receives all host NVIDIA devices and configurable
tensor parallelism; services without CUDA work remain CPU-only.

External images carry both an exact version and an immutable registry digest. AGE Viewer carries a
project-owned version while its image build remains downstream work. Every service has a healthcheck
and a bounded stop grace period. Every published port binds to `127.0.0.1`; vLLM is absent unless its
profile is selected; cAdvisor does not mount the host root.

The operator entry point loads the same layered runtime configuration and passes Compose an explicit
project directory and `.env` path. It replaces host mount variables in memory with resolved absolute
paths, performs the runtime preflight before config validation or startup, and creates only the
documented layout plus per-service state directories. The database alone mounts `PGDATA_DIR`. A
configured `PG_WAL_DIR` and any `PG_TABLESPACE_<NAME>_DIR` become generated, short-lived Compose
overrides mounted only into the database; the override contains no secrets and is removed after the
command. Grafana, Prometheus, and AGE Viewer each receive only their own writable
`SERVICE_STATE_DIR` child. Grafana provisioning and Prometheus scrape configuration mount read-only
from `docker/`. No current service consumes archive files or pipeline result files, so those roots
are not mounted. The service preflight consequently excludes `PROOF_ARCHIVE_DIR`; its independent
read-only proof-run contract remains enforced by `make config` and future proof commands.

`make services-up` starts `SERVICE_PROFILES=core` by default, waits for health, and refuses a
database-bearing profile until `POSTGRES_PASSWORD` is configured. `make services-config` validates
without starting containers. The vLLM defaults pin v0.26.0 plus the official Qwen3.8 27B FP8 model
revision, allow 24 GB of CPU offload for a 16 GB GPU host, and cap the initial context at 32,768
tokens; `.env` can tune tensor parallelism, offload, GPU utilization, and context length.
`make services-status`, `make logs`, and `make services-down` remain
available without rerunning the mutating path preflight, so an operator can inspect or stop the
project even when a runtime disk is unavailable. `LOG_SERVICES`, `LOG_TAIL`, and `LOG_FOLLOW=1`
control bounded log selection. `make graph-up` and `make ui-up` are profile shortcuts; additional or
combined profiles use `SERVICE_PROFILES="core ui observability"`.

## Tests and verification

Tests under `tests/config/` cover layer precedence, shell precedence, checkout and current-directory
independence, paths containing spaces, named silos, derived overrides, variable references,
redaction, missing values, root and symlink hazards, all root-overlap boundaries, permissions,
free space, proof read-only enforcement, distinct device evidence, results layout creation, and
storage-class refusal versus warning fixtures. Tests under `tests/compose/` render every profile and
the supported combined topology through Docker Compose without starting services. They cover image
pins, loopback ports, healthchecks, stop policy, generated WAL and tablespace mounts, writable state
isolation, read-only provisioning, profile parsing, password refusal, cleanup, quiet redaction, and
the Make entry points. CLI coverage proves explicit config options and redacted output. The required
format, lint, typing, complexity, shell, documentation, plan-integrity, and deterministic test gates
pass.
