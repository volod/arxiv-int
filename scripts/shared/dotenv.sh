#!/usr/bin/env bash
# Dotenv parsing, precedence and reference expansion for the shared bootstrap.
# Source this file; do not execute it. The supported subset matches
# src/arxiv_int/runtime/dotenv.py: NAME=value lines, optional export, one pair of
# matching quotes, " #" comments outside quotes, and ${NAME}/$NAME references in
# *_DIR variables only. Command substitution, escapes, multiline values and
# ${NAME:-default} are not supported.

declare -gA arxiv_int_values=()
declare -gA arxiv_int_expanded=()
declare -ga arxiv_int_names=()
arxiv_int_trimmed=""
arxiv_int_value=""
arxiv_int_value_found=0
arxiv_int_resolved=""

arxiv_int_fail() {
  printf '%s\n' "ERROR: $1" >&2
  return 1
}

arxiv_int_trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  arxiv_int_trimmed="${value%"${value##*[![:space:]]}"}"
}

arxiv_int_unquote() {
  local value="$1"
  local first="${value:0:1}"
  local last="${value: -1}"
  if [ "${#value}" -ge 2 ] && [ "$first" = "$last" ] &&
    { [ "$first" = '"' ] || [ "$first" = "'" ]; }; then
    arxiv_int_trimmed="${value:1:${#value}-2}"
    return 0
  fi
  arxiv_int_trimmed="$value"
  return 1
}

arxiv_int_dotenv_value() {
  local value="$1"
  arxiv_int_trim "$value"
  value="$arxiv_int_trimmed"
  arxiv_int_unquote "$value" && return 0
  case "$value" in
    *" #"*)
      arxiv_int_trim "${value%%" #"*}"
      arxiv_int_unquote "$arxiv_int_trimmed" || true
      ;;
  esac
}

arxiv_int_read_dotenv() {
  local file="$1"
  local line name value number=0
  arxiv_int_values=()
  arxiv_int_names=()
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    number=$((number + 1))
    arxiv_int_trim "$line"
    line="$arxiv_int_trimmed"
    [ -z "$line" ] && continue
    case "$line" in \#*) continue ;; esac
    if [ "${line:0:7}" = "export " ]; then
      arxiv_int_trim "${line:7}"
      line="$arxiv_int_trimmed"
    fi
    name="${line%%=*}"
    value="${line#*=}"
    arxiv_int_trim "$name"
    name="$arxiv_int_trimmed"
    if [ "$name" = "$line" ] || ! [[ "$name" =~ ^[A-Z][A-Z0-9_]*$ ]]; then
      arxiv_int_fail "$file:$number: expected NAME=value"
      return 1
    fi
    arxiv_int_dotenv_value "$value"
    [[ -v arxiv_int_values["$name"] ]] || arxiv_int_names+=("$name")
    arxiv_int_values["$name"]="$arxiv_int_trimmed"
  done < "$file"
}

arxiv_int_is_exported() {
  local declaration
  declaration="$(declare -p "$1" 2>/dev/null)" || return 1
  [[ "$declaration" =~ ^declare\ -[^[:space:]]*x[^[:space:]]*\  ]]
}

arxiv_int_value_of() {
  local name="$1"
  arxiv_int_value_found=1
  if [[ -v arxiv_int_values["$name"] ]]; then
    arxiv_int_value="${arxiv_int_values[$name]}"
  elif arxiv_int_is_exported "$name"; then
    arxiv_int_value="${!name}"
  else
    arxiv_int_value=""
    arxiv_int_value_found=0
  fi
}

arxiv_int_expand_name() {
  local name="$1"
  local chain="$2"
  local value result rest prefix reference
  if [[ -v arxiv_int_expanded["$name"] ]]; then
    arxiv_int_resolved="${arxiv_int_expanded[$name]}"
    return 0
  fi
  case " $chain " in
    *" $name "*)
      arxiv_int_fail "$name references itself: $chain $name"
      return 1
      ;;
  esac
  arxiv_int_value_of "$name"
  value="$arxiv_int_value"
  case "$name" in
    *_DIR) ;;
    *)
      arxiv_int_expanded["$name"]="$value"
      arxiv_int_resolved="$value"
      return 0
      ;;
  esac
  result=""
  rest="$value"
  while [ -n "$rest" ]; do
    case "$rest" in
      *'$'*)
        prefix="${rest%%\$*}"
        rest="${rest#*\$}"
        ;;
      *)
        result+="$rest"
        rest=""
        continue
        ;;
    esac
    result+="$prefix"
    if [[ "$rest" =~ ^\{([A-Z][A-Z0-9_]*)\}(.*)$ ]] ||
      [[ "$rest" =~ ^([A-Z][A-Z0-9_]*)(.*)$ ]]; then
      reference="${BASH_REMATCH[1]}"
      rest="${BASH_REMATCH[2]}"
    else
      result+='$'
      continue
    fi
    arxiv_int_value_of "$reference"
    if [ "$arxiv_int_value_found" -eq 0 ]; then
      arxiv_int_fail "$name references missing $reference"
      return 1
    fi
    arxiv_int_expand_name "$reference" "$chain $name" || return 1
    arxiv_int_trim "$arxiv_int_resolved"
    if [ -z "$arxiv_int_trimmed" ]; then
      arxiv_int_fail "$name references empty $reference"
      return 1
    fi
    result+="$arxiv_int_resolved"
  done
  arxiv_int_expanded["$name"]="$result"
  arxiv_int_resolved="$result"
}

arxiv_int_absolute_path() {
  local value="$1"
  local home_prefix="~"
  if [ "$value" = "$home_prefix" ]; then
    value="$HOME"
  elif [ "${value:0:2}" = "$home_prefix/" ]; then
    value="$HOME/${value:2}"
  fi
  case "$value" in
    /*) ;;
    *) value="$PROJECT_ROOT/$value" ;;
  esac
  arxiv_int_trimmed="$value"
}

arxiv_int_resolve_env() {
  local env_file="$PROJECT_ROOT/.env"
  local name value
  arxiv_int_expanded=()
  arxiv_int_read_dotenv "$env_file" || return 1
  for name in "${arxiv_int_names[@]}"; do
    if arxiv_int_is_exported "$name"; then
      arxiv_int_values["$name"]="${!name}"
    fi
  done
  for name in "${arxiv_int_names[@]}"; do
    arxiv_int_expand_name "$name" "" || return 1
    value="$arxiv_int_resolved"
    if [ -n "$value" ]; then
      case "$name" in
        *_DIR)
          arxiv_int_absolute_path "$value"
          value="$arxiv_int_trimmed"
          ;;
      esac
    fi
    printf -v "$name" '%s' "$value"
    export "${name?}"
  done
  DATA_DIR="${DATA_DIR:-$PROJECT_ROOT/.data}"
  arxiv_int_absolute_path "$DATA_DIR"
  DATA_DIR="$arxiv_int_trimmed"
  export DATA_DIR
}

arxiv_int_data_root() {
  arxiv_int_resolve_env >/dev/null || return 1
  printf '%s\n' "$DATA_DIR"
}

