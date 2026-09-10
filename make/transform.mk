# Isolated dbt runs and search/vector/graph projections.
##@ Transform
.PHONY: transform-parse transform-compile transform-build transform-test \
	projections-build projections-status projections-cleanup search-lexical

transform-parse: ## Parse the packaged dbt project for RUN_ID without materializing relations
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" transform parse --run-id "$(RUN_ID)"

transform-compile: ## Compile selected dbt models for RUN_ID
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" transform compile --run-id "$(RUN_ID)"

transform-build: ## Build and test isolated derived models for RUN_ID
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" transform build --run-id "$(RUN_ID)"

transform-test: ## Run dbt data tests for RUN_ID without replacing the active generation
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" transform test --run-id "$(RUN_ID)"

projections-build: ## Build search/vector/graph projections for RUN_ID (KIND=all|lexical|vector|graph)
	@$(require_cli)
	@$(load_env) && "$(CLI)" store projections-build --run-id "$(RUN_ID)" \
		$(if $(filter-out all,$(KIND)),--kind "$(KIND)",) \
		$(if $(filter 1,$(APPLY)),--activate,)

projections-status: ## Show active projection pointers
	@$(require_cli)
	@$(load_env) && "$(CLI)" store projections-status --run-id "$(RUN_ID)"

projections-cleanup: ## Plan retired/failed projection drops (APPLY=1 executes)
	@$(require_cli)
	@$(load_env) && "$(CLI)" store projections-cleanup --run-id "$(RUN_ID)" \
		$(if $(filter 1,$(APPLY)),--apply,)

search-lexical: ## Query the active lexical projection (QUERY= LANGUAGE= DOCUMENT_ID= MODE= EXPLAIN=1 JSON=1)
	@$(require_cli)
	@test -n "$(QUERY)" || { echo "ERROR: set QUERY=<query text>"; exit 1; }
	@$(load_env) && "$(CLI)" search lexical "$(QUERY)" \
		$(if $(MODE),--mode "$(MODE)",) \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(FIELD),--field "$(FIELD)",) \
		$(if $(LANGUAGE),--language "$(LANGUAGE)",) \
		$(if $(DOCUMENT_ID),--document-id "$(DOCUMENT_ID)",) \
		$(if $(FACET),--facet "$(FACET)",) \
		$(if $(filter 1,$(CITATIONS)),--citations,) \
		$(if $(filter 1,$(EXPLAIN)),--explain,) \
		$(if $(filter 1,$(JSON)),--json,)

