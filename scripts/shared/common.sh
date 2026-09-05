#!/usr/bin/env bash
# Shared environment bootstrap. Source this file; do not execute it.

arxiv_int_project_root() {
  (cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
}

PROJECT_ROOT="${PROJECT_ROOT:-$(arxiv_int_project_root)}"

arxiv_int_path_device() {
  local path="$1"
  local parent
  while [ -n "$path" ] && [ ! -e "$path" ]; do
    parent="$(dirname "$path")"
    [ "$parent" = "$path" ] && break
    path="$parent"
  done
  [ -e "$path" ] || return 1
  stat -c '%d' "$path" 2>/dev/null || stat -f '%d' "$path" 2>/dev/null
}

arxiv_int_export_uv_link_mode() {
  local mode="${UV_LINK_MODE:-}"
  if [ -n "$mode" ] && [ "${mode,,}" != "auto" ]; then
    export UV_LINK_MODE
    return 0
  fi

  unset UV_LINK_MODE
  command -v uv >/dev/null 2>&1 || return 0
  local cache_device
  local root_device
  cache_device="$(arxiv_int_path_device "$(uv cache dir 2>/dev/null)")" || cache_device=""
  root_device="$(arxiv_int_path_device "$PROJECT_ROOT/.venv")" || root_device=""
  if [ -n "$cache_device" ] && [ -n "$root_device" ] && [ "$cache_device" != "$root_device" ]; then
    export UV_LINK_MODE=copy
  fi
}

arxiv_int_export_tool_caches() {
  export RUFF_CACHE_DIR="${RUFF_CACHE_DIR:-$DATA_DIR/cache/ruff}"
  export MYPY_CACHE_DIR="${MYPY_CACHE_DIR:-$DATA_DIR/cache/mypy}"
}

arxiv_int_source_dotenv() {
  local env_file="$1"
  local key
  local line
  local allexport_was_set=0
  local -A previous_values=()
  local -A previously_set=()

  while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Z][A-Z0-9_]*)= ]]; then
      key="${BASH_REMATCH[2]}"
      if [[ -v "$key" ]]; then
        previously_set["$key"]=1
        previous_values["$key"]="${!key}"
      fi
    fi
  done < "$env_file"

  case "$-" in
    *a*) allexport_was_set=1 ;;
  esac
  set -a
  # shellcheck source=/dev/null
  . "$env_file"
  [ "$allexport_was_set" -eq 1 ] || set +a

  for key in "${!previously_set[@]}"; do
    printf -v "$key" '%s' "${previous_values[$key]}"
    export "${key?}"
  done
}

arxiv_int_load_env() {
  if [ -f "$PROJECT_ROOT/.env" ]; then
    arxiv_int_source_dotenv "$PROJECT_ROOT/.env"
  fi
  DATA_DIR="${DATA_DIR:-$PROJECT_ROOT/.data}"
  case "$DATA_DIR" in
    /*) ;;
    *) DATA_DIR="$PROJECT_ROOT/$DATA_DIR" ;;
  esac
  export DATA_DIR
  arxiv_int_export_tool_caches
  arxiv_int_export_uv_link_mode
}

arxiv_int_services() {
  if [ ! -x "$PROJECT_ROOT/.venv/bin/arxiv-int" ]; then
    printf '%s\n' "ERROR: run 'make bootstrap' first" >&2
    return 1
  fi
  "$PROJECT_ROOT/.venv/bin/arxiv-int" services "$@"
}
