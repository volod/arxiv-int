#!/usr/bin/env bash
# Shared environment bootstrap. Source this file; do not execute it.
# The dotenv subset resolved here matches src/arxiv_int/runtime/dotenv.py exactly.

arxiv_int_project_root() {
  (cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
}

PROJECT_ROOT="${PROJECT_ROOT:-$(arxiv_int_project_root)}"
export PROJECT_ROOT

# shellcheck source=scripts/shared/dotenv.sh
. "$(dirname "${BASH_SOURCE[0]}")/dotenv.sh"
# shellcheck source=scripts/shared/setup.sh
. "$(dirname "${BASH_SOURCE[0]}")/setup.sh"

arxiv_int_sync_dotenv() {
  local example_file="$PROJECT_ROOT/.env.example"
  local env_file="$PROJECT_ROOT/.env"
  local key
  local line
  local appended=0
  local -A present=()

  if [ ! -f "$example_file" ]; then
    printf '%s\n' "ERROR: missing $example_file" >&2
    return 1
  fi
  if [ ! -e "$env_file" ]; then
    cp -- "$example_file" "$env_file"
    printf '%s\n' "Created .env from .env.example"
    return 0
  fi
  if [ ! -f "$env_file" ]; then
    printf '%s\n' "ERROR: $env_file is not a regular file" >&2
    return 1
  fi

  while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^[[:space:]]*#?[[:space:]]*(export[[:space:]]+)?([A-Z][A-Z0-9_]*)= ]]; then
      present["${BASH_REMATCH[2]}"]=1
    fi
  done < "$env_file"

  while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^[[:space:]]*#?[[:space:]]*(export[[:space:]]+)?([A-Z][A-Z0-9_]*)= ]]; then
      key="${BASH_REMATCH[2]}"
      if [[ ! -v "present[$key]" ]]; then
        if [ "$appended" -eq 0 ]; then
          printf '\n%s\n' '# Added from .env.example by make bootstrap.' >> "$env_file"
        fi
        printf '%s\n' "$line" >> "$env_file"
        present["$key"]=1
        appended=$((appended + 1))
      fi
    fi
  done < "$example_file"

  if [ "$appended" -gt 0 ]; then
    printf '%s\n' "Added $appended missing variable declaration(s) to .env"
  fi
}

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

arxiv_int_load_env() {
  arxiv_int_resolve_env || return 1
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
