# Local Compose services and the pinned PostgreSQL image.
##@ Services
.PHONY: services-pull models-pull services-config services-up services-status \
	services-down services-reset logs graph-up ui-up postgres-image \
	postgres-image-probe

services-pull: ## Acquire or cache-check selected service images
	@$(require_setup)
	@"$(CLI)" setup --phase images

models-pull: ## Acquire or cache-check configured model assets
	@$(require_setup)
	@"$(CLI)" setup --phase models

services-config: ## Validate Compose for SERVICE_PROFILES without starting containers
	@$(load_env) && \
		arxiv_int_services config $(PROFILE_ARGS)

services-up: ## Start and wait for healthy SERVICE_PROFILES (default from .env)
	@$(load_env) && \
		arxiv_int_services up $(PROFILE_ARGS)

services-status: ## Show local service and health status
	@$(load_env) && \
		arxiv_int_services status $(PROFILE_ARGS)

services-down: ## Stop the local service project; preserve bind-mounted data
	@$(load_env) && \
		arxiv_int_services down $(PROFILE_ARGS)

services-reset: ## Stop services; erase service data only when APPLY=1
	@$(load_env) && \
		arxiv_int_services reset $(PROFILE_ARGS) \
		$(if $(filter 1,$(APPLY)),--apply,)

logs: ## Show bounded logs (LOG_SERVICES=..., LOG_TAIL=..., LOG_FOLLOW=1)
	@$(load_env) && \
		arxiv_int_services logs $(PROFILE_ARGS) \
		--services "$(LOG_SERVICES)" --tail "$(LOG_TAIL)" \
		$(if $(filter 1,$(LOG_FOLLOW)),--follow,)

graph-up: SERVICE_PROFILES := graph
graph-up: services-up ## Start the graph profile

ui-up: SERVICE_PROFILES := ui
ui-up: services-up ## Start the UI profile

postgres-image: ## Build the pinned ParadeDB+AGE database image (NO_CACHE=1 for clean cache)
	@$(require_cli)
	@$(load_env) && \
		"$(CLI)" store build-image \
		$(if $(filter 1,$(NO_CACHE)),--no-cache,)

postgres-image-probe: ## Probe extensions on a disposable PGDATA_DIR (WRITE_GATE=1 records AGE gate)
	@$(require_cli)
	@$(load_env) && \
		"$(CLI)" store probe-image \
		$(if $(filter 1,$(WRITE_GATE)),--write-gate,)

