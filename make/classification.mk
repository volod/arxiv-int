# Subject-taxonomy classification scheme freeze, inspection, and gold-label splits.
##@ Classification
.PHONY: classification-scheme classification-check classification-show classification-tree \
	classification-labels

classification-scheme: ## Validate the packaged taxonomy and freeze a snapshot (RUN_ID= from make run-create)
	@$(require_cli)
	@$(load_env) && $(sync_extras) && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(CLI)" classification build-scheme --run-id "$(RUN_ID)"

# A snapshot comes from SCHEME=, else from a created RUN_ID. Make's RUN_ID ?= local default is not a
# run, so the tree reads a run only when RUN_ID is set on the command line or in the environment.
classification_scheme_args = $(if $(SCHEME),--scheme "$(SCHEME)",--run-id "$(RUN_ID)")
classification_require_run = $(if $(SCHEME),,arxiv_int_require_created_run_id "$(RUN_ID)" &&)
classification_explicit_run = $(filter-out file undefined default,$(origin RUN_ID))

classification-check: ## Re-verify checksums, closure, coverage, licence and staleness (RUN_ID= or SCHEME=)
	@$(require_cli)
	@$(load_env) && $(classification_require_run) \
		"$(CLI)" classification check-scheme $(classification_scheme_args)

classification-show: ## Print one class with path, captions, crosswalk (CLASS=; RUN_ID= or SCHEME=)
	@$(require_cli)
	@test -n "$(CLASS)" || { echo "ERROR: set CLASS=<class id or taxonomy code>"; exit 1; }
	@$(load_env) && $(classification_require_run) \
		"$(CLI)" classification show "$(CLASS)" $(classification_scheme_args)

classification-tree: ## Print taxonomy codes and captions (ROOT= DEPTH=; packaged unless RUN_ID=/SCHEME=)
	@$(require_cli)
	@$(load_env) && \
		"$(CLI)" classification tree $(if $(ROOT),--root "$(ROOT)",) \
		$(if $(DEPTH),--depth "$(DEPTH)",) $(if $(SCHEME),--scheme "$(SCHEME)",) \
		$(if $(classification_explicit_run),--run-id "$(RUN_ID)",)

classification-labels: ## Freeze gold-label splits (RUN_ID= LABELS= LABEL_SET=)
	@$(require_cli)
	@test -n "$(LABELS)" || { echo "ERROR: set LABELS=<gold label JSONL>"; exit 1; }
	@test -n "$(LABEL_SET)" || { echo "ERROR: set LABEL_SET=<label set id>"; exit 1; }
	@$(load_env) && $(sync_extras) && \
		arxiv_int_require_created_run_id "$(RUN_ID)" && \
		"$(CLI)" classification freeze-labels --run-id "$(RUN_ID)" \
		--labels "$(LABELS)" --label-set "$(LABEL_SET)"
