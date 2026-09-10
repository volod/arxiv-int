# Shared Make variables and recipe helpers.
VENV := $(PROJECT_ROOT)/.venv
PY := $(VENV)/bin/python
CLI := $(VENV)/bin/arxiv-int
PYTHON_VERSION ?= 3.12
DATA_DIR ?=
LOG_SERVICES ?=
LOG_TAIL ?= 200
LOG_FOLLOW ?= 0
READINESS_ALLOW_DEGRADED ?= 0
MESSAGE ?= contract schema change
REVISION ?= head
DOWN_REVISION ?= -1
DATASET ?= documents
RUN_ID ?= local
APPLY ?= 0
NO_CACHE ?= 0
WRITE_GATE ?= 0
KIND ?= all
COMMON_SH := $(PROJECT_ROOT)/scripts/shared/common.sh
# One extra set for every syncing target so consecutive targets cannot uninstall each other.
SYNC_EXTRAS := --extra dev --extra contracts --extra extraction --extra graph --extra store --extra lake --extra data-quality --extra inference --extra transform
PROFILE_ARGS := $(if $(SERVICE_PROFILES),--profiles "$(SERVICE_PROFILES)",)
DATA_ROOT := $(shell $(if $(DATA_DIR),DATA_DIR='$(DATA_DIR)') bash -c '. "$$0"; arxiv_int_data_root' '$(COMMON_SH)')
PYTEST_CACHE := -o "cache_dir=$(DATA_ROOT)/cache/pytest"

export RUFF_CACHE_DIR := $(DATA_ROOT)/cache/ruff
export MYPY_CACHE_DIR := $(DATA_ROOT)/cache/mypy

require_cli = test -x "$(CLI)" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
require_setup = test -x "$(CLI)" || { echo "ERROR: run 'make setup-env' first"; exit 1; }
load_env = source "$(COMMON_SH)" && arxiv_int_load_env
sync_extras = uv sync --locked $(SYNC_EXTRAS) --python "$(PYTHON_VERSION)"
