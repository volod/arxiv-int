# Stage DAG, run ledger, forecast, inspect, and prune.
##@ Pipeline
.PHONY: pipeline run-create stage resume update rebuild invalidate prune \
	run-status forecast run-finalize inspect

pipeline: ## Run the selected profile DAG; allocates a unique run id
	@$(require_cli)
	@$(load_env) && \
		"$(CLI)" pipeline run \
		$(if $(FROM),--from "$(FROM)",) \
		$(if $(TO),--to "$(TO)",) \
		$(if $(ARCHIVE_DIR),--archive-dir "$(ARCHIVE_DIR)",) \
		$(if $(RESULTS_DIR),--results-dir "$(RESULTS_DIR)",) \
		$(if $(PIPELINE_PROFILE),--profile "$(PIPELINE_PROFILE)",)

forecast: ## Read-only time/storage forecast (RUN_ID= from make run-create)
	@$(require_cli)
	@$(load_env) && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(CLI)" pipeline forecast --run-id "$(RUN_ID)" \
		$(if $(filter 1,$(FORCE)),--force,) \
		$(if $(FROM),--from "$(FROM)",) \
		$(if $(TO),--to "$(TO)",)

run-finalize: ## Seal knowledge-base generation (RUN_ID= from make run-create)
	@$(require_cli)
	@$(load_env) && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(CLI)" run finalize "$(RUN_ID)"

run-create: ## Allocate a unique run id and freeze .env configuration
	@$(require_cli)
	@$(load_env) && \
		"$(CLI)" run create \
		$(if $(ARCHIVE_DIR),--archive-dir "$(ARCHIVE_DIR)",) \
		$(if $(RESULTS_DIR),--results-dir "$(RESULTS_DIR)",) \
		$(if $(PIPELINE_PROFILE),--profile "$(PIPELINE_PROFILE)",)

stage: ## Run one registered stage (STAGE= and RUN_ID= from make run-create)
	@$(require_cli)
	@test -n "$(STAGE)" || { echo "ERROR: set STAGE=<registered stage>"; exit 1; }
	@$(load_env) && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(CLI)" stage "$(STAGE)" --run-id "$(RUN_ID)" \
		$(if $(filter 1,$(FORCE)),--force,)

resume: ## Resume a halted run (RUN_ID= from make run-create)
	@$(require_cli)
	@$(load_env) && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(CLI)" run resume "$(RUN_ID)" \
		$(if $(filter 1,$(FORCE)),--force,)

run-status: ## Show per-stage progress (RUN_ID= from make run-create)
	@$(require_cli)
	@$(load_env) && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(CLI)" run status "$(RUN_ID)"

inspect: ## Summarize published stage artifacts (RUN_ID= from make run-create)
	@$(require_cli)
	@$(load_env) && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(CLI)" inspect "$(RUN_ID)" \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(filter 1,$(JSON)),--json,)

update: ## Incremental DAG update from the current archive
	@$(require_cli)
	@$(load_env) && \
		"$(CLI)" pipeline update \
		$(if $(filter-out local,$(RUN_ID)),--run-id "$(RUN_ID)",) \
		$(if $(FROM),--from "$(FROM)",) \
		$(if $(TO),--to "$(TO)",) \
		$(if $(ARCHIVE_DIR),--archive-dir "$(ARCHIVE_DIR)",) \
		$(if $(RESULTS_DIR),--results-dir "$(RESULTS_DIR)",)

rebuild: ## Fresh generation without cache reuse
	@$(require_cli)
	@$(load_env) && \
		"$(CLI)" pipeline rebuild \
		$(if $(filter-out local,$(RUN_ID)),--run-id "$(RUN_ID)",) \
		$(if $(FROM),--from "$(FROM)",) \
		$(if $(TO),--to "$(TO)",) \
		$(if $(ARCHIVE_DIR),--archive-dir "$(ARCHIVE_DIR)",) \
		$(if $(RESULTS_DIR),--results-dir "$(RESULTS_DIR)",)

invalidate: ## Mark STAGE and descendants stale (STAGE= RUN_ID=)
	@$(require_cli)
	@test -n "$(STAGE)" || { echo "ERROR: set STAGE=<registered stage>"; exit 1; }
	@$(load_env) && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(CLI)" pipeline invalidate "$(STAGE)" --run-id "$(RUN_ID)" \
		$(if $(DOCUMENT_ID),--document-id "$(DOCUMENT_ID)",)

prune: ## Plan stale derived deletion (APPLY=1 PLAN_ID=... to apply)
	@$(require_cli)
	@$(load_env) && \
		"$(CLI)" artifacts prune --stale \
		$(if $(filter 1,$(APPLY)),--apply --plan "$(PLAN_ID)",)

