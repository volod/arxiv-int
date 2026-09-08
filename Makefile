# arxiv-int developer entrypoints
SHELL := /bin/bash
PROJECT_ROOT := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))

include $(PROJECT_ROOT)/make/config.mk
include $(PROJECT_ROOT)/make/bootstrap.mk
include $(PROJECT_ROOT)/make/services.mk
include $(PROJECT_ROOT)/make/contracts.mk
include $(PROJECT_ROOT)/make/transform.mk
include $(PROJECT_ROOT)/make/inference.mk
include $(PROJECT_ROOT)/make/eval.mk
include $(PROJECT_ROOT)/make/pipeline.mk
include $(PROJECT_ROOT)/make/quality.mk

.DEFAULT_GOAL := help

##@ General
.PHONY: help
help: ## List available targets
	@awk -f "$(PROJECT_ROOT)/make/help.awk" $(MAKEFILE_LIST)
