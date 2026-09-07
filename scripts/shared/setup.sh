#!/usr/bin/env bash
# Pre-venv setup helpers. Source this file; do not execute it.

arxiv_int_setup_host_tools() {
  local tool
  for tool in uv python3 docker; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      printf '%s\n' "ERROR: missing host tool $tool" >&2
      return 1
    fi
  done
  if ! docker compose version >/dev/null 2>&1; then
    printf '%s\n' "ERROR: Docker Compose is required" >&2
    return 1
  fi
}

arxiv_int_setup_required_edits() {
  local missing=()
  if [ -z "${ARCHIVE_DIR:-}" ]; then
    missing+=("ARCHIVE_DIR (or ARCHIVE_SILO_<ID>_DIR)")
  fi
  if [ -z "${RESULTS_DIR:-}" ]; then
    missing+=("RESULTS_DIR")
  fi
  if [ -z "${PGDATA_DIR:-}" ]; then
    missing+=("PGDATA_DIR")
  fi
  if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    missing+=("POSTGRES_PASSWORD")
  fi
  if [ "${#missing[@]}" -gt 0 ]; then
    printf '%s\n' "edit .env and set ${missing[*]}, then make setup" >&2
    return 1
  fi
}

arxiv_int_setup_config() {
  arxiv_int_sync_dotenv || return 1
  arxiv_int_setup_host_tools || return 1
  if [ -x "$PROJECT_ROOT/.venv/bin/arxiv-int" ]; then
    "$PROJECT_ROOT/.venv/bin/arxiv-int" setup --phase config
    return $?
  fi
  arxiv_int_load_env || return 1
  arxiv_int_setup_required_edits
}

arxiv_int_setup_env() {
  arxiv_int_load_env || return 1
  if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' "ERROR: uv is required" >&2
    return 1
  fi
  local -a extra_args=("$@")
  if [ "${SETUP_DOWNLOADS:-1}" = "0" ]; then
    extra_args+=(--offline)
  fi
  uv sync --locked --python "${PYTHON_VERSION:-3.12}" "${extra_args[@]}"
}
