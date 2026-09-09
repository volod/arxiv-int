# Product contracts, schema revisions, ontology, and dataset quality.
##@ Contracts
.PHONY: contracts contracts-gen contracts-check contracts-evolution \
	contracts-evolution-live db-revision db-check db-status db-upgrade \
	db-downgrade db-adopt db-apply-schema ontology ontology-gen ontology-check \
	data-quality

contracts: ## Lint product ODCS contracts (schema, integrity, Data Contract CLI)
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" contracts lint

contracts-gen: ## Generate committed physical schemas under packaged contracts/generated
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" contracts generate

contracts-check: ## Fail when packaged contracts/generated drifts from regeneration
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" contracts check

contracts-evolution: ## Check reviewed baselines and migrations without disposable Postgres
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" contracts evolution --skip-live-sql

contracts-evolution-live: ## Evolution policy plus disposable Postgres apply of baseline SQL
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" contracts evolution

db-revision: ## Generate a candidate immutable revision from contract changes
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" db revision --message "$(MESSAGE)"

db-check: ## Check the revision graph, checksums, and pending contract changes
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" db check

db-status: ## Report the applied revision of the selected migration database
	@$(require_cli)
	@$(load_env) && "$(CLI)" db status

db-upgrade: ## Upgrade the selected migration database to REVISION
	@$(require_cli)
	@$(load_env) && "$(CLI)" db upgrade --revision "$(REVISION)"

db-downgrade: ## Downgrade the selected migration database to DOWN_REVISION
	@$(require_cli)
	@$(load_env) && "$(CLI)" db downgrade --revision "$(DOWN_REVISION)"

db-adopt: ## Adopt a live database after catalog equivalence, or report why stamping is refused
	@$(require_cli)
	@$(load_env) && "$(CLI)" db adopt

db-apply-schema: ## Apply owned revisions (URL or disposable PGDATA); evidence under DATA_DIR/migrations
	@$(require_cli)
	@$(load_env) && "$(CLI)" store apply-schema --revision "$(REVISION)" \
		--run-id "$(RUN_ID)"

ontology: ontology-check ## Alias for ontology-check

ontology-gen: ## Generate committed ontology.* bindings under packaged ontology/generated
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" ontology generate

ontology-check: ## Parse RDF/SHACL, verify bindings, drift, and ontology evolution
	@$(require_cli)
	@$(load_env) && $(sync_extras) && "$(CLI)" ontology check

data-quality: ## Validate DATASET contents for RUN_ID (INPUT=... required)
	@$(require_cli)
	@test -n "$(INPUT)" || { echo "ERROR: set INPUT to a parquet, arrow, or JSON table"; exit 1; }
	@$(load_env) && $(sync_extras) && "$(CLI)" data-quality check "$(DATASET)" --run-id "$(RUN_ID)" \
		--input "$(INPUT)" $(if $(RELATED),$(foreach item,$(RELATED),--related $(item)),)

