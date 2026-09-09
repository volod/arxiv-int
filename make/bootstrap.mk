# Environment, identity, readiness, and retryable setup.
##@ Bootstrap
.PHONY: bootstrap venv lock package-check features config readiness \
	setup setup-config setup-env setup-models setup-wait setup-schema

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
	@$(require_cli)
	@"$(CLI)" info

features: ## List optional feature groups, licences, and install commands (STAGE=... to filter)
	@$(require_cli)
	@"$(CLI)" features $(if $(STAGE),--stage $(STAGE),)

config: ## Resolve, validate, and redact runtime configuration
	@$(require_cli)
	@"$(CLI)" config show --redact

readiness: ## Audit configuration, storage, tools, services, models, and system readiness
	@$(require_cli)
	@$(load_env) && \
		status=0; "$(CLI)" readiness $(PROFILE_ARGS) || status=$$?; \
		if [ "$$status" -eq 2 ] && [ "$(READINESS_ALLOW_DEGRADED)" -eq 1 ]; then exit 0; fi; \
		exit "$$status"

setup-config: ## Create or append .env, name required edits, and check host tools
	@source "$(COMMON_SH)"; arxiv_int_setup_config

setup-env: ## Sync the locked extra union into .venv (honors SETUP_DOWNLOADS=0)
	@source "$(COMMON_SH)"; arxiv_int_setup_env $(SYNC_EXTRAS)

setup-models: ## Prefetch or verify configured inference and extraction model caches
	@$(require_setup)
	@"$(CLI)" setup --phase models

setup-wait: ## Wait for service transport and model health without requiring a schema
	@$(require_setup)
	@"$(CLI)" setup --phase wait

setup-schema: ## Apply eligible Alembic revisions to the configured service only
	@$(require_setup)
	@"$(CLI)" setup --phase schema

setup: ## Retryable environment, model, service and schema preparation
	@source "$(COMMON_SH)"; arxiv_int_setup_config
	@source "$(COMMON_SH)"; arxiv_int_setup_env $(SYNC_EXTRAS)
	@"$(CLI)" setup

