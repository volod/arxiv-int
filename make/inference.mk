# Local inference health, schemas, GPU lease, and model assets.
##@ Inference
.PHONY: ollama-check models-list inference-schemas inference-schemas-check \
	inference-resources inference-fit inference-schedule

ollama-check: ## Check the configured local Ollama or vLLM endpoint
	@$(require_setup)
	@"$(CLI)" inference health

models-list: ## List models served by the configured local inference endpoint
	@$(require_setup)
	@"$(CLI)" inference models

inference-schemas: ## Write committed structured-output JSON Schema files
	@$(require_cli)
	@"$(CLI)" inference schemas generate

inference-schemas-check: ## Fail when packaged configs/models/schemas drifts from generation
	@$(require_cli)
	@"$(CLI)" inference schemas check

inference-resources: ## Show host GPU VRAM, power, and RAM
	@$(require_cli)
	@"$(CLI)" inference resources

inference-fit: ## Estimate whether MODEL (default GENERATION_MODEL) fits this host
	@$(require_cli)
	@"$(CLI)" inference fit $(if $(MODEL),--model "$(MODEL)")

inference-schedule: ## Acquire the host GPU lease for MODEL and record telemetry
	@$(require_cli)
	@"$(CLI)" inference schedule --run-id "$(RUN_ID)" \
		$(if $(MODEL),--model "$(MODEL)")

