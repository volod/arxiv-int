# Frozen evaluation fixtures, scoring, and Git-bound proof export.
##@ Evaluation
.PHONY: identity-policy-check evaluation-fixtures-check eval proof proof-export

identity-policy-check: ## Fail when packaged evaluation proof-identity policy drifts
	@$(require_cli)
	@"$(CLI)" evaluation identity-policy check

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

proof-export: ## Export identity-obfuscated copies (SOURCE_BUNDLE= MAP="a=b" RUN_ID=)
	@$(require_cli)
	@test -n "$(SOURCE_BUNDLE)" || { echo "ERROR: set SOURCE_BUNDLE to a verified run bundle"; exit 1; }
	@test -n "$(MAP)" || { echo "ERROR: set MAP to ARTIFACT=DEST pairs"; exit 1; }
	@$(load_env) && \
		"$(CLI)" evaluation export-proof --source-bundle "$(SOURCE_BUNDLE)" \
		--run-id "$(RUN_ID)" $(foreach item,$(MAP),--map $(item)) \
		$(if $(DESTINATION_ROOT),--destination-root "$(DESTINATION_ROOT)",) \
		$(if $(RECEIPT),--receipt "$(RECEIPT)",)

