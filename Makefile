# arxiv-int developer entrypoints.
SHELL := /bin/bash
PROJECT_ROOT := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
VENV := $(PROJECT_ROOT)/.venv
PY := $(VENV)/bin/python
PYTHON_VERSION ?= 3.12
DATA_DIR ?=
LOG_SERVICES ?=
LOG_TAIL ?= 200
LOG_FOLLOW ?= 0
READINESS_ALLOW_DEGRADED ?= 0
MESSAGE ?= contract schema change
REVISION ?= head
DOWN_REVISION ?= -1
DATASET ?= documents
RUN_ID ?= local
APPLY ?= 0
NO_CACHE ?= 0
WRITE_GATE ?= 0
COMMON_SH := $(PROJECT_ROOT)/scripts/shared/common.sh
# One extra set for every syncing target so consecutive targets cannot uninstall each other.
SYNC_EXTRAS := --extra dev --extra contracts --extra graph --extra store --extra lake --extra data-quality --extra inference --extra transform
PROFILE_ARGS := $(if $(SERVICE_PROFILES),--profiles "$(SERVICE_PROFILES)",)
DATA_ROOT := $(shell $(if $(DATA_DIR),DATA_DIR='$(DATA_DIR)') bash -c '. "$$0"; arxiv_int_data_root' '$(COMMON_SH)')
PYTEST_CACHE := -o "cache_dir=$(DATA_ROOT)/cache/pytest"

export RUFF_CACHE_DIR := $(DATA_ROOT)/cache/ruff
export MYPY_CACHE_DIR := $(DATA_ROOT)/cache/mypy

.DEFAULT_GOAL := help

KIND ?= all

.PHONY: help bootstrap venv lock package-check features config readiness setup setup-config setup-env \
	setup-wait setup-schema services-pull models-pull services-config services-up \
	services-status services-down services-reset logs graph-up ui-up postgres-image postgres-image-probe \
	format format-check lint typecheck test test-heavy \
	coverage complexity-gate shell-lint-gate lint-md lint-doc-links lint-spec-plan plan-status \
	contracts contracts-gen contracts-check contracts-evolution contracts-evolution-live \
	db-revision db-check db-status db-upgrade \
	db-downgrade db-adopt db-apply-schema ontology ontology-gen ontology-check data-quality \
	transform-parse transform-compile transform-build transform-test \
	projections-build projections-status projections-cleanup \
	proof-export identity-policy-check evaluation-fixtures-check inference-schemas-check \
	eval proof \
	pipeline run-create stage resume update rebuild invalidate prune run-status \
	ci-checks ci ci-github build quality code-quality quality-report

help: ## List available targets
	@awk 'BEGIN {FS = ":.*## "; print "Usage: make <target>\n"} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## Sync .env and .venv, then audit readiness
	@printf '\n=== Environment and dependencies ===\n'
	@command -v uv >/dev/null 2>&1 || { echo "ERROR: uv is required"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_sync_dotenv && \
		arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)"
	@printf '\n=== Package identity ===\n'
	@$(MAKE) --no-print-directory package-check
	@printf '\n=== Workstation readiness ===\n'
	@$(MAKE) --no-print-directory readiness READINESS_ALLOW_DEGRADED=1

venv: bootstrap ## Alias for bootstrap

lock: ## Refresh uv.lock after dependency changes
	@source "$(COMMON_SH)" && arxiv_int_load_env && uv lock

package-check: ## Verify the installed package identity
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" info

features: ## List optional feature groups, licences, and install commands (STAGE=... to filter)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" features $(if $(STAGE),--stage $(STAGE),)

contracts: ## Lint product ODCS contracts (schema, integrity, Data Contract CLI)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" contracts lint

contracts-gen: ## Generate committed physical schemas under contracts/generated
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" contracts generate

contracts-check: ## Fail when contracts/generated drifts from regeneration
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" contracts check

contracts-evolution: ## Check reviewed baselines and migrations without disposable Postgres
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" contracts evolution --skip-live-sql

contracts-evolution-live: ## Evolution policy plus disposable Postgres apply of baseline SQL
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" contracts evolution

db-revision: ## Generate a candidate immutable revision from contract changes
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" db revision --message "$(MESSAGE)"

db-check: ## Check the revision graph, checksums, and pending contract changes
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" db check

db-status: ## Report the applied revision of the selected migration database
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" db status

db-upgrade: ## Upgrade the selected migration database to REVISION
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" db upgrade --revision "$(REVISION)"

db-downgrade: ## Downgrade the selected migration database to DOWN_REVISION
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" db downgrade --revision "$(DOWN_REVISION)"

db-adopt: ## Adopt a live database after catalog equivalence, or report why stamping is refused
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" db adopt

db-apply-schema: ## Apply owned revisions (URL or disposable PGDATA); evidence under DATA_DIR/migrations
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" store apply-schema --revision "$(REVISION)" \
		--run-id "$(RUN_ID)"

ontology: ontology-check ## Alias for ontology-check

ontology-gen: ## Generate committed ontology.* bindings under ontology/generated
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" ontology generate

ontology-check: ## Parse RDF/SHACL, verify bindings, drift, and ontology evolution
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" ontology check

data-quality: ## Validate DATASET contents for RUN_ID (INPUT=... required)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@test -n "$(INPUT)" || { echo "ERROR: set INPUT to a parquet, arrow, or JSON table"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" data-quality check "$(DATASET)" --run-id "$(RUN_ID)" \
		--input "$(INPUT)" $(if $(RELATED),$(foreach item,$(RELATED),--related $(item)),)

transform-parse: ## Parse the dbt project for RUN_ID without materializing relations
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" transform parse --run-id "$(RUN_ID)"

transform-compile: ## Compile selected dbt models for RUN_ID
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" transform compile --run-id "$(RUN_ID)"

transform-build: ## Build and test isolated derived models for RUN_ID
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" transform build --run-id "$(RUN_ID)"

transform-test: ## Run dbt data tests for RUN_ID without replacing the active generation
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)" && \
		"$(VENV)/bin/arxiv-int" transform test --run-id "$(RUN_ID)"

projections-build: ## Build search/vector/graph projections for RUN_ID (KIND=all|lexical|vector|graph)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" store projections-build --run-id "$(RUN_ID)" \
		$(if $(filter-out all,$(KIND)),--kind "$(KIND)",) \
		$(if $(filter 1,$(APPLY)),--activate,)

projections-status: ## Show active projection pointers
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" store projections-status --run-id "$(RUN_ID)"

projections-cleanup: ## Plan retired/failed projection drops (APPLY=1 executes)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" store projections-cleanup --run-id "$(RUN_ID)" \
		$(if $(filter 1,$(APPLY)),--apply,)

config: ## Resolve, validate, and redact runtime configuration
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" config show --redact

readiness: ## Audit configuration, storage, tools, services, models, and system readiness
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		status=0; "$(VENV)/bin/arxiv-int" readiness $(PROFILE_ARGS) || status=$$?; \
		if [ "$$status" -eq 2 ] && [ "$(READINESS_ALLOW_DEGRADED)" -eq 1 ]; then exit 0; fi; \
		exit "$$status"

setup-config: ## Create or append .env, name required edits, and check host tools
	@source "$(COMMON_SH)"; arxiv_int_setup_config

setup-env: ## Sync the locked extra union into .venv (honors SETUP_DOWNLOADS=0)
	@source "$(COMMON_SH)"; arxiv_int_setup_env $(SYNC_EXTRAS)

services-pull: ## Acquire or cache-check selected service images
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make setup-env' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" setup --phase images

models-pull: ## Acquire or cache-check configured model assets
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make setup-env' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" setup --phase models

ollama-check: ## Check the configured local Ollama or vLLM endpoint
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make setup-env' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" inference health

models-list: ## List models served by the configured local inference endpoint
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make setup-env' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" inference models

inference-schemas: ## Write committed structured-output JSON Schema files
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" inference schemas generate

inference-schemas-check: ## Fail when configs/models/schemas drifts from generation
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" inference schemas check

identity-policy-check: ## Fail when configs/evaluation proof-identity policy drifts
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" evaluation identity-policy check

evaluation-fixtures-check: ## Fail when frozen evaluation fixtures or proof registry drift
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" evaluation fixtures check

eval: ## Score frozen evaluation fixtures (RUN_ID=)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" evaluation evaluate --run-id "$(RUN_ID)" --runs-dir "$$RUNS_DIR"

proof: ## Publish a capability proof (CAPABILITY= RUN_ID=)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@test -n "$(CAPABILITY)" || { echo "ERROR: set CAPABILITY"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" evaluation proof publish --capability "$(CAPABILITY)" \
		--run-id "$(RUN_ID)" --results-dir "$$RESULTS_DIR" --runs-dir "$$RUNS_DIR"

proof-export: ## Export identity-obfuscated copies (SOURCE_BUNDLE= MAP="a=b" RUN_ID=)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@test -n "$(SOURCE_BUNDLE)" || { echo "ERROR: set SOURCE_BUNDLE to a verified run bundle"; exit 1; }
	@test -n "$(MAP)" || { echo "ERROR: set MAP to ARTIFACT=DEST pairs"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" evaluation export-proof --source-bundle "$(SOURCE_BUNDLE)" \
		--run-id "$(RUN_ID)" $(foreach item,$(MAP),--map $(item)) \
		$(if $(DESTINATION_ROOT),--destination-root "$(DESTINATION_ROOT)",) \
		$(if $(RECEIPT),--receipt "$(RECEIPT)",)

pipeline: ## Run the selected profile DAG; allocates a unique run id
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" pipeline run \
		$(if $(FROM),--from "$(FROM)",) \
		$(if $(TO),--to "$(TO)",) \
		$(if $(ARCHIVE_DIR),--archive-dir "$(ARCHIVE_DIR)",) \
		$(if $(RESULTS_DIR),--results-dir "$(RESULTS_DIR)",) \
		$(if $(PIPELINE_PROFILE),--profile "$(PIPELINE_PROFILE)",)

run-create: ## Allocate a unique run id and freeze .env configuration
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" run create \
		$(if $(ARCHIVE_DIR),--archive-dir "$(ARCHIVE_DIR)",) \
		$(if $(RESULTS_DIR),--results-dir "$(RESULTS_DIR)",) \
		$(if $(PIPELINE_PROFILE),--profile "$(PIPELINE_PROFILE)",)

stage: ## Run one registered stage (STAGE= and RUN_ID= from make run-create)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@test -n "$(STAGE)" || { echo "ERROR: set STAGE=<registered stage>"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(VENV)/bin/arxiv-int" stage "$(STAGE)" --run-id "$(RUN_ID)" \
		$(if $(filter 1,$(FORCE)),--force,)

resume: ## Resume a halted run (RUN_ID= from make run-create)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(VENV)/bin/arxiv-int" run resume "$(RUN_ID)" \
		$(if $(filter 1,$(FORCE)),--force,)

run-status: ## Show per-stage progress (RUN_ID= from make run-create)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(VENV)/bin/arxiv-int" run status "$(RUN_ID)"

update: ## Incremental DAG update from the current archive
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" pipeline update \
		$(if $(filter-out local,$(RUN_ID)),--run-id "$(RUN_ID)",) \
		$(if $(FROM),--from "$(FROM)",) \
		$(if $(TO),--to "$(TO)",) \
		$(if $(ARCHIVE_DIR),--archive-dir "$(ARCHIVE_DIR)",) \
		$(if $(RESULTS_DIR),--results-dir "$(RESULTS_DIR)",)

rebuild: ## Fresh generation without cache reuse
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" pipeline rebuild \
		$(if $(filter-out local,$(RUN_ID)),--run-id "$(RUN_ID)",) \
		$(if $(FROM),--from "$(FROM)",) \
		$(if $(TO),--to "$(TO)",) \
		$(if $(ARCHIVE_DIR),--archive-dir "$(ARCHIVE_DIR)",) \
		$(if $(RESULTS_DIR),--results-dir "$(RESULTS_DIR)",)

invalidate: ## Mark STAGE and descendants stale (STAGE= RUN_ID=)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@test -n "$(STAGE)" || { echo "ERROR: set STAGE=<registered stage>"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(VENV)/bin/arxiv-int" pipeline invalidate "$(STAGE)" --run-id "$(RUN_ID)" \
		$(if $(DOCUMENT_ID),--document-id "$(DOCUMENT_ID)",)

prune: ## Plan stale derived deletion (APPLY=1 PLAN_ID=... to apply)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" artifacts prune --stale \
		$(if $(filter 1,$(APPLY)),--apply --plan "$(PLAN_ID)",)

inference-resources: ## Show host GPU VRAM, power, and RAM
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" inference resources

inference-fit: ## Estimate whether MODEL (default GENERATION_MODEL) fits this host
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" inference fit $(if $(MODEL),--model "$(MODEL)")

inference-schedule: ## Acquire the host GPU lease for MODEL and record telemetry
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" inference schedule --run-id "$(RUN_ID)" \
		$(if $(MODEL),--model "$(MODEL)")

setup-wait: ## Wait for service transport and model health without requiring a schema
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make setup-env' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" setup --phase wait

setup-schema: ## Apply eligible Alembic revisions to the configured service only
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make setup-env' first"; exit 1; }
	@"$(VENV)/bin/arxiv-int" setup --phase schema

setup: ## Retryable environment, model, service and schema preparation
	@source "$(COMMON_SH)"; arxiv_int_setup_config
	@source "$(COMMON_SH)"; arxiv_int_setup_env $(SYNC_EXTRAS)
	@"$(VENV)/bin/arxiv-int" setup

services-config: ## Validate Compose for SERVICE_PROFILES without starting containers
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_services config $(PROFILE_ARGS)

services-up: ## Start and wait for healthy SERVICE_PROFILES (default from .env)
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_services up $(PROFILE_ARGS)

services-status: ## Show local service and health status
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_services status $(PROFILE_ARGS)

services-down: ## Stop the local service project; preserve bind-mounted data
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_services down $(PROFILE_ARGS)

services-reset: ## Stop services; erase service data only when APPLY=1
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_services reset $(PROFILE_ARGS) \
		$(if $(filter 1,$(APPLY)),--apply,)

logs: ## Show bounded logs (LOG_SERVICES=..., LOG_TAIL=..., LOG_FOLLOW=1)
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		arxiv_int_services logs $(PROFILE_ARGS) \
		--services "$(LOG_SERVICES)" --tail "$(LOG_TAIL)" \
		$(if $(filter 1,$(LOG_FOLLOW)),--follow,)

graph-up: SERVICE_PROFILES := graph
graph-up: services-up ## Start the graph profile

ui-up: SERVICE_PROFILES := ui
ui-up: services-up ## Start the UI profile

postgres-image: ## Build the pinned ParadeDB+AGE database image (NO_CACHE=1 for clean cache)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" store build-image \
		$(if $(filter 1,$(NO_CACHE)),--no-cache,)

postgres-image-probe: ## Probe extensions on a disposable PGDATA_DIR (WRITE_GATE=1 records AGE gate)
	@test -x "$(VENV)/bin/arxiv-int" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@source "$(COMMON_SH)" && arxiv_int_load_env && \
		"$(VENV)/bin/arxiv-int" store probe-image \
		$(if $(filter 1,$(WRITE_GATE)),--write-gate,)

format: ## Format production code and tests with Ruff
	@"$(VENV)/bin/ruff" format src tests
	@"$(VENV)/bin/ruff" check --fix src tests

format-check: ## Check Python formatting without changing files
	@"$(VENV)/bin/ruff" format --check src tests

lint: ## Run Ruff lint checks
	@"$(VENV)/bin/ruff" check src tests

typecheck: ## Run mypy over production code
	@"$(VENV)/bin/mypy" --python-version "$(PYTHON_VERSION)"

test: ## Run deterministic unit tests (excludes heavy Docker/host checks)
	@"$(PY)" -m pytest $(PYTEST_CACHE) -m "not heavy"

test-heavy: ## Run Docker and other host-service tests marked heavy
	@"$(PY)" -m pytest $(PYTEST_CACHE) -m heavy

coverage: ## Run tests and report coverage (diagnostic; no percentage floor)
	@"$(PY)" -m pytest $(PYTEST_CACHE) -m "not heavy" --cov=arxiv_int --cov-report=term-missing

complexity-gate: ## Fail on Radon D-or-worse or cognitive complexity above 15
	@output="$$($(VENV)/bin/radon cc src tests -s -n D)"; \
		if [ -n "$$output" ]; then printf '%s\n' "$$output"; exit 1; fi
	@mkdir -p "$(DATA_ROOT)/cache/complexipy"
	@cd "$(DATA_ROOT)/cache/complexipy"; \
		output="$$($(VENV)/bin/complexipy "$(PROJECT_ROOT)/src" "$(PROJECT_ROOT)/tests" \
		--max-complexity-allowed 15 --failed --ignore-complexity --color no --plain --sort desc)"; \
		if [ -n "$$output" ]; then printf '%s\n' "$$output"; exit 1; fi

shell-lint-gate: ## Check every tracked shell script with bash and ShellCheck
	@find scripts -type f -name '*.sh' -print0 | xargs -0 -r -n1 bash -n
	@find scripts -type f -name '*.sh' -print0 | \
		xargs -0 -r "$(VENV)/bin/shellcheck" -x -P SCRIPTDIR -S warning

lint-md: ## Lint repository Markdown and then validate relative links
	@"$(PY)" -m pymarkdown scan -r README.md AGENTS.md CLAUDE.md GEMINI.md docs
	@$(MAKE) --no-print-directory lint-doc-links

lint-doc-links: ## Check that relative Markdown links and anchors resolve
	@"$(PY)" -m arxiv_int.quality.doc_links --root "$(PROJECT_ROOT)"

lint-spec-plan: ## Check capability registry, task structure, status, and ordering
	@"$(PY)" -m arxiv_int.quality.plan_integrity --root "$(PROJECT_ROOT)"

plan-status: ## Count tasks by lane/status and show the next eligible work
	@"$(VENV)/bin/arxiv-int-plan" --root "$(PROJECT_ROOT)"

ci-checks: format-check lint typecheck complexity-gate shell-lint-gate lint-doc-links lint-spec-plan contracts-check contracts-evolution db-check ontology-check inference-schemas-check identity-policy-check evaluation-fixtures-check

ci: ci-checks test ## Run the required local and GitHub CI gate

ci-github: ci ## Explicit GitHub Actions entrypoint

build: ## Build source and wheel distributions
	@source "$(COMMON_SH)" && arxiv_int_load_env && uv build

quality: ci-checks coverage lint-md build ## Run the full local quality suite

code-quality: quality ## Alias for the full local quality suite

quality-report: ## Report Python/shell files over the 250-line soft limit
	@find src tests scripts -type f \( -name '*.py' -o -name '*.sh' \) -print0 | \
		xargs -0 -r wc -l | awk '$$2 != "total" && $$1 > 250 {print}' | sort -nr
