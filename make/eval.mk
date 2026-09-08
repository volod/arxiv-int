# Frozen evaluation fixtures, scoring, and capability proofs.
##@ Evaluation
.PHONY: evaluation-fixtures-check eval proof

evaluation-fixtures-check: ## Fail when frozen evaluation fixtures or proof registry drift
	@$(require_cli)
	@"$(CLI)" evaluation fixtures check

eval: ## Score frozen evaluation fixtures (RUN_ID=)
	@$(require_cli)
	@$(load_env) && \
		"$(CLI)" evaluation evaluate --run-id "$(RUN_ID)" --runs-dir "$$RUNS_DIR"

proof: ## Publish a capability proof (CAPABILITY= RUN_ID=)
	@$(require_cli)
	@test -n "$(CAPABILITY)" || { echo "ERROR: set CAPABILITY"; exit 1; }
	@$(load_env) && \
		"$(CLI)" evaluation proof publish --capability "$(CAPABILITY)" \
		--run-id "$(RUN_ID)" --results-dir "$$RESULTS_DIR" --runs-dir "$$RUNS_DIR"
