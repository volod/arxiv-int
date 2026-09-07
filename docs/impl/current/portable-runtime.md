# Portable Runtime

Runtime configuration and path behavior lives cohesively under `src/arxiv_int/runtime/`. The
top-level package contains only its initializer, CLI entry point, and metadata module; runtime
implementation details do not expand that namespace.

`make setup` is the operator entry for environment, model, service and schema preparation. It
creates a missing `.env`, names required edits, syncs the locked extra union, acquires or
cache-checks selected images and models, starts services, waits for transport and model health,
applies eligible Alembic revisions to the configured service only, and re-probes readiness.
Retries reuse verified fingerprints and still probe services, wait, and readiness. Concurrent
setup against the same targets is refused. Typed stage and artifact interfaces, a generic run
ledger, serialized progress logs, and a fixture DAG CLI exist under
[Pipeline control](pipeline-control.md). Concrete corpus stages and knowledge-base
publication remain [planned](../plan.md#pipeline-control----pipeline-control).
Infrastructure-ready never means an archive-to-report run is available. See the
[operator workflow](../../guide/operator-workflow.md) for the atomic chain and the
[accepted setup record](../records/0022-runtime-implement-retryable-setup-command.md).

`make bootstrap` remains the contributor path that syncs `.env`/`.venv` and audits readiness
without starting services or applying schema.

Make entry points stop on environment-loading or dependency-sync failure before invoking the
requested command. Base CLI help/features and setup argument parsing work before optional extras
are installed; database imports occur when the schema phase executes. Setup validates the complete
initial store before reusing its applied revision;
partial or drifted state is refused. See the
[boundary repair](../records/0028-store-refactor-foundation-store-acceptance-boundaries.md).

## Layered configuration

`arxiv_int.runtime.load_runtime_config()` resolves runtime values with CLI, process environment,
checkout `.env`, and documented defaults in descending precedence. It discovers or accepts an
explicit project root, resolves relative paths and `${VARIABLE}` references from that checkout, and
returns a typed immutable `RuntimeConfig`. Missing operator roots identify every variable the
operator must set. Rendering is stable and masks passwords, tokens, secrets, and database URLs.
`arxiv_int.runtime.config_model` owns the immutable values, `arxiv_int.runtime.config_schema` owns
the documented variable registry -- names, defaults, the service ports and the value rules -- and
`arxiv_int.runtime.dotenv` owns the file grammar and reference expansion, dependency-free.

Resolution order is fixed: precedence, then documented defaults, then reference expansion, then
path resolution. Because references expand last, overriding `RESULTS_DIR` from the process
environment also moves every root that references it, and the same override produces the same roots
through Make, a direct CLI call and readiness. An explicitly empty value selects the documented
default; a required operator root left empty is reported as missing. References expand in `*_DIR`
variables only, so a `$` in a password or URL stays literal. They may nest, and a cycle, an
undefined name or an empty referenced value is refused by variable name. `.env.example` documents
the supported subset and the shell syntax that is deliberately not supported.

`arxiv_int.runtime.project_root` owns the one checkout discovery every entry point uses: an
explicit option, then `PROJECT_ROOT`, then the module's own checkout, then the working directory.
A declared root that is not a checkout is refused rather than silently replaced, so an alternate
checkout invoked from a foreign working directory keeps its own roots. Readiness reports a
non-checkout root as a blocked `config.root` finding instead of failing. `arxiv_int.quality`
reuses the same ancestor walk with its stricter repository markers.

`arxiv_int.runtime.inference_config` owns the backend selection and the local endpoint, so the
readiness probe follows the configured `VLLM_PORT` instead of a fixed one. Service ports resolve
once with the defaults `docker/compose.yaml` declares (`POSTGRES_PORT` 5432, `GRAFANA_PORT` 3000,
`AGE_VIEWER_PORT` 3001, `PROMETHEUS_PORT` 9090, `CADVISOR_PORT` 8080, `VLLM_PORT` 8000); a
non-numeric or out-of-range port is refused before any command runs.

The three required operator placements are one or more archive silos, `RESULTS_DIR`, and
`PGDATA_DIR`. `ARCHIVE_DIR` is the one-silo form with id `default`; additional or alternative silos
use `ARCHIVE_SILO_<ID>_DIR`, with underscores in the variable id rendered as hyphens. `RUNS_DIR`,
`SERVICE_STATE_DIR`, `MODEL_CACHE_DIR`, and `TMP_DIR` derive from `RESULTS_DIR` unless individually
overridden. Optional `PG_WAL_DIR` and `PG_TABLESPACE_<NAME>_DIR` roots remain unset by default.
`DATA_DIR` remains checkout-relative developer-tooling state and is not a runtime output root. There
are no development-only archive aliases or result roots; stage implementations and provided-archive
proof runs use the configured `ARCHIVE_DIR` silos. See
[0029](../records/0029-runtime-retire-separate-proof-archive-root.md).

`scripts/shared/dotenv.sh`, sourced by `scripts/shared/common.sh`, implements the same documented
grammar and the same precedence, defaults and reference order in dependency-free bash, because the
bootstrap runs before the virtual environment exists. It parses the file instead of executing it,
so a value is never run as shell, and it exports the resolved absolute `*_DIR` values the Python
entry points then re-resolve identically. Paired fixtures in `tests/config/test_parity.py` hold the
two implementations to one result for defaults, overrides, nested references, quotes and spaces,
explicit empty values, invalid input and foreign working directories. Only exported shell variables
count as process overrides, matching Python's environment; whitespace is trimmed before unquoting.
Reading resolves without
mutating the process environment or the checkout; `make bootstrap` and `make setup` are the steps
that append missing `.env` declarations.

`make` derives its tool-cache root from the same resolved `DATA_DIR` through
`arxiv_int_data_root`, so linter, type-checker, test and complexity caches follow the operator's
selected location instead of a separate checkout-relative default. `DATA_DIR=` on the command line
still overrides both.

## Path safety and storage evidence

`arxiv_int.runtime.containment` owns one protected-root policy that every destructive or
report-writing action reuses. Containment is symmetric: a candidate is refused when it is a
protected root, lies beneath one, or encloses one. Each root declares whether its strict
descendants stay allowed, so service-data roots derived from `RESULTS_DIR` remain erasable while
`RESULTS_DIR` itself and any ancestor of it do not. The module also owns the fail-closed
`resolve_allowed_path()` resolution used elsewhere in the runtime.

`arxiv_int.runtime.validate_runtime_paths()` operates on resolved real paths, accumulates all
findings, and does not create directories. It refuses filesystem-root targets; source, results,
database, WAL, and tablespace overlaps; two derived roots that alias one tree; output inside or
around the checkout; symlink-resolved escapes; unreadable sources; and unwritable or full
destinations. Archive directories may have host write permission: read-only is a pipeline access
contract, not a filesystem-mode requirement. Database roots on a filesystem without
PostgreSQL-compatible ownership and exclusive-use semantics are blocked. Rotational storage is
accepted for database, scratch, and model placements; its measured flag is informational. Non-owning
service-state placements remain degraded warnings.

`arxiv_int.runtime.inspect_filesystem()` records the resolved path, filesystem type, device id,
rotational flag when the operating system exposes it, accessible free bytes, ownership capability,
and read-only mount state. This evidence is retained with every configured placement and is exposed
to readiness, the pipeline forecast, and later run-manifest work. `arxiv_int.runtime.path_model` owns the typed
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

## Retryable setup

`arxiv-int setup`, wrapped by `make setup`, coordinates independently callable phases under
`src/arxiv_int/runtime/setup/`. Typed settings `PIPELINE_PROFILE` (default `investigation`),
`SERVICE_PROFILES` (default `pipeline`), and `SETUP_DOWNLOADS` (default `1`) live in the shared
schema and `.env`; Make does not default `SERVICE_PROFILES` in a way that shadows `.env`.
`SETUP_DOWNLOADS=0` syncs and pulls only from local caches.

Atomic Make/CLI commands share the same handlers: `setup-config`, `setup-env`, `services-pull`,
`models-pull`, `setup-wait`, and `setup-schema`, plus the existing package, Compose config,
pinned PostgreSQL image, contracts/ontology, services-up, and readiness commands. Schema apply
derives the loopback URL from `POSTGRES_*`, refuses a conflicting `ARXIV_INT_MIGRATION_DATABASE_URL`,
never uses a disposable store, and leaves catalog adoption to `make db-adopt`. Setup does not
install OS packages, reset service data, or start corpus processing.

Redacted per-phase status is printed and written to `$RESULTS_DIR/reports/setup.json`. Tool
fingerprints live under `$DATA_DIR/setup/`. Fixture or already-cached model tags used during
setup smoke do not prove production model fit.

## System readiness

`arxiv-int readiness`, wrapped by `make readiness`, accumulates configuration, tool, RAM/GPU, path,
filesystem, free-space, Compose health, database extension, migration, contract, local inference API,
and configured-model checks into one report for the default `pipeline` selection. Every configured
root in that full audit is represented once with its
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
`RESULTS_DIR`, and `--no-json-report` disables persistence. The destination is resolved through
symlinks and checked against the shared protected roots -- the checkout, every archive silo,
and the database cluster, write-ahead log, and tablespace roots -- so an invalid
roots configuration blocks persistence instead of writing into protected data. The check is
repeated after the report directory is created and immediately before the write, so a link swapped
in between cannot redirect the report.

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

Readiness passes `PGPASSWORD` by name through the Compose process environment, keeping its value
out of argv. Query failures use stable diagnostics; reported versions redact the password. Required
extensions must have installed versions, independently of package availability; graph selection
also requires AGE. The probe does not install extensions.

Local inference HTTP bypasses proxies, refuses all redirects and credential-bearing URLs, and caps
JSON bodies at 1 MiB. Socket timeouts and a remaining-budget socket shutdown bound transport reads;
malformed JSON/model lists and transport failures cannot produce a ready endpoint. Only HTTP/HTTPS
loopback hosts are accepted; query strings, fragments and invalid ports are refused. `localhost`
uses literal IPv4 loopback, including HTTPS certificate identity validation. IPv6 `::1` is supported.
Configured backend ports remain shared with Compose. See the
[accepted probe-safety record](../records/0008-runtime-refactor-readiness-probe-safety.md) for
evidence and limits.

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
explicitly checked when `vllm` is included in `SERVICE_PROFILES`, using the model identity
passed to Compose even when the pipeline backend remains Ollama. `graph`, `vllm`, and privileged
`cadvisor` remain explicit opt-ins.

`runtime/service_plan.py` owns the typed service plan, profile map, alias expansion, extension
requirements and CLI profile help. Rendered Compose fixtures verify that every profile selects the
same services. Explicit profile arguments override ambient `COMPOSE_PROFILES` values. Empty profile
requests retain the `pipeline` default; omitting a profile disables its service-specific checks.
Core-only readiness checks the database without archive, UI or inference availability checks.
vLLM-only readiness checks its cache, GPU, endpoint and served generation model without requiring a
database password, database disks or extensions. Combined requests take the union; the full
`pipeline` topology retains the existing archive, contract and configured-backend audit. All roots
must still resolve in configuration, and all configured containment boundaries remain enforced.

Compose command construction is pure, with an explicit base builder reused by database probing.
`config` and `up` retain the common results skeleton, runs and temporary directories, but prepare
only selected database, model-cache and per-service state directories. Unselected archive mounts
need not be available. `status`, `down` and `logs` perform no disk inspection or layout preparation.
Log service arguments must name services in the selected plan; invalid names and negative tails
are refused before preparation. Reset keeps its existing project-wide root policy. See the
[accepted service-planning record](../records/0007-runtime-refactor-profile-aware-service-planning.md)
for regressions and verification limits.

`runtime/inference_config.py` resolves generation defaults after configuration precedence:
`qwen3.8:27b` for Ollama, or `VLLM_MODEL` and `VLLM_MODEL_REVISION` for vLLM. Explicit
`GENERATION_MODEL` and `GENERATION_MODEL_REVISION` override the active backend defaults. Compose
receives the separate vLLM settings, so the default Ollama tag never replaces its Hugging Face model
identifier. Readiness checks the resolved generation model on the selected backend. Defaults do not
download models or constitute a model quality evaluation. Production chat, structured output,
embeddings, health, identity, timeout, and cancel use the
[local inference client](local-inference.md); `make models-pull` still owns asset acquisition.

`.env.example` shows `GENERATION_MODEL=qwen3.8:27b` for Ollama with the revision left unset.
`GENERATION_MODEL_REVISION` applies only to vLLM and identifies a commit in the selected Hugging Face
model repository; the template includes the paired revision example and backend-switch instructions.

The configured-host bootstrap confirms the Ollama endpoint and the default generation model are
available, recorded in `$RESULTS_DIR/reports/readiness.json`. Overall readiness remains degraded for
stopped Compose services. Rotational storage checks pass. The model-selection refactor passes
`make ci` with 160 tests and `make services-config`; it starts no service or model download.

External images carry both an exact version and an immutable registry digest. The database service
uses the project-owned `arxiv-int/postgres` tag built from a pinned ParadeDB digest plus Apache AGE;
see [Canonical store](canonical-store.md). AGE Viewer carries a project-owned version while its image
build remains downstream work. Every service has a healthcheck
and a bounded stop grace period. Grafana healthchecks allow ten minutes of retries so
first-boot SQLite migrations on `SERVICE_STATE_DIR` can finish before Compose `--wait` marks
the container unhealthy; SQLite WAL is enabled, and plugin preinstall is disabled so startup
does not download Grafana apps
([Grafana first-boot health](../records/0037-runtime-allow-grafana-first-boot-health.md)).
The PostgreSQL exporter healthcheck probes `/metrics` because that
image has no `/health` route, and its `DATA_SOURCE_NAME` stays on one Compose line so YAML folding
cannot insert a space before the host. Every published port binds to `127.0.0.1`; vLLM is absent
unless its profile is selected; cAdvisor does not mount the host root.

The operator entry point loads the same layered runtime configuration and passes Compose an explicit
project directory and `.env` path. It replaces host mount variables in memory with resolved absolute
paths, injects `RUNTIME_UID` and `RUNTIME_GID` from the invoking process (required; Compose refuses
missing values so a bare `docker compose` cannot create inaccessible root or image-default UID
files), performs the runtime
preflight before config validation or startup, and creates only the documented layout plus
per-service state directories. Every service that writes a bind mount -- database, Grafana, Prometheus,
AGE Viewer, postgres-exporter, and vLLM -- runs as that operator UID. Privileged cAdvisor does not.
The database alone mounts `PGDATA_DIR`. A
configured `PG_WAL_DIR` and any `PG_TABLESPACE_<NAME>_DIR` become generated, short-lived Compose
overrides mounted only into the database; the override contains no secrets and is removed after the
command. Grafana, Prometheus, and AGE Viewer each receive only their own writable
`SERVICE_STATE_DIR` child. Grafana provisioning and Prometheus scrape configuration mount read-only
from `docker/`. No current service consumes archive files or pipeline result files, so those roots
are not mounted. Ordinary host write permission on archive silos is accepted; the pipeline access
contract, not Compose mounts, keeps source bytes unmodified.

Disposable image probes under `arxiv-int store probe-image` also pass `docker run --user` with the
same host UID/GID so `$DATA_DIR/postgres-image-probe/.../pgdata` stays erasable by the operator.

A `PGDATA_DIR` initialized under an older image-default UID (typically 999) must be reassigned to
the operator once before `make services-up` can pass the writable-path preflight, for example
`docker run --rm -v "$PGDATA_DIR:/data" alpine chown -R "$(id -u):$(id -g)" /data`.

`make services-up` starts the profiles from `.env` (`SERVICE_PROFILES`, default `pipeline`), waits
for health, and refuses a
database-bearing profile until `POSTGRES_PASSWORD` is configured. `make services-config` validates
without starting containers. The vLLM defaults pin v0.26.0 plus the official Qwen3.8 27B FP8 model
revision, allow 24 GB of CPU offload for a 16 GB GPU host, and cap the initial context at 32,768
tokens; `.env` can tune tensor parallelism, offload, GPU utilization, and context length. `make
services-status`, `make logs`, and `make services-down` remain available without rerunning the
mutating path preflight, so an operator can inspect or stop the project even when a runtime disk is
unavailable. `make services-down` stops Compose containers and keeps bind-mounted roots
(`PGDATA_DIR`, `SERVICE_STATE_DIR`, `MODEL_CACHE_DIR`, and optional WAL or tablespace directories)
intact for the next `make services-up`. `make services-reset` first resolves and accepts every
service-data root, then stops containers and lists those roots; pass `APPLY=1` (or `arxiv-int
services reset --apply`) to erase their contents after stop. An unsafe target is refused before any
service is stopped. Reset refuses a root that is, contains, or lies inside the checkout or an archive
silo, and refuses `RESULTS_DIR` itself or any ancestor of it. Each target is
revalidated immediately before deletion, so a directory replaced by a symlink into protected data
after planning is refused rather than followed. `LOG_SERVICES`, `LOG_TAIL`, and `LOG_FOLLOW=1`
control bounded log selection. `make graph-up` and `make ui-up` are profile shortcuts; additional or
combined profiles use `SERVICE_PROFILES="core ui observability"`.

## Tests and verification

Tests under `tests/config/` cover layer precedence, paired shell/Python resolution and refusal,
project-root selection, service-port defaults and validation, shell precedence, checkout and
current-directory independence, paths containing spaces, named silos, derived overrides, variable references,
redaction, missing values, root and symlink hazards, all root-overlap boundaries, derived-root
aliasing, readable source permissions, writable source directories, free space, distinct
device evidence, results layout creation, and storage-class refusal versus warning fixtures. Tests
under `tests/compose/` render every profile and the supported combined topology through Docker
Compose without starting services. They cover image pins, loopback ports, healthchecks, stop policy,
generated WAL and tablespace mounts, writable state isolation, read-only provisioning, `pipeline`
alias expansion, required-service healthchecks and `up --wait`, password refusal, cleanup, quiet
redaction, and the Make entry points. Reset coverage includes ancestor and descendant containment
for the checkout and archive silos, refusal before the stop command runs, and a
symlink swapped in after planning. Readiness operator scenarios cover ready, degraded, and blocked
aggregation; command timeouts; unavailable services and inference; model presence; unsupported,
non-owning, and rotational storage; consolidated root evidence; report containment and permissions;
distinct exit codes; report refusal inside archive and database roots, around the checkout, and
through a symlink out of `RESULTS_DIR`; and secret redaction without network access. CLI coverage
proves explicit config options and redacted output. Configuration and rendered Compose checks cover
backend defaults, operator model overrides, and separation of Ollama tags from vLLM identifiers.
Tests under `tests/runtime/setup/` cover dotenv create/append, missing edits, Make/CLI wrappers that
do not shadow `.env`, schema binding without a disposable fallback, offline image/model cache
misses, failure propagation, cancellation, concurrent locks, verified-work reuse with a fresh
readiness probe, and redacted reports. The required format, lint, typing, complexity, shell,
documentation, plan-integrity, and deterministic test gates pass.
