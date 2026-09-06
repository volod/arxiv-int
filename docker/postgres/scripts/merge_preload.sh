#!/bin/sh
# Merge one library into shared_preload_libraries without dropping others.
# Usage: merge_preload.sh <postgresql.conf-or-sample> <library>
set -eu

conf="${1:?postgresql.conf path required}"
library="${2:?library name required}"

if [ ! -f "$conf" ]; then
  printf '%s\n' "ERROR: missing conf file: $conf" >&2
  exit 1
fi

if grep -Eq "^[[:space:]]*shared_preload_libraries[[:space:]]*=" "$conf"; then
  current="$(
    sed -n "s/^[[:space:]]*shared_preload_libraries[[:space:]]*=[[:space:]]*'\([^']*\)'.*/\1/p" "$conf" | head -n 1
  )"
  case ",${current}," in
    *,"${library}",*) ;;
    *)
      if [ -z "$current" ]; then
        merged="$library"
      else
        merged="${current},${library}"
      fi
      tmp="$(mktemp)"
      sed "s|^[[:space:]]*shared_preload_libraries[[:space:]]*=[[:space:]]*'[^']*'|shared_preload_libraries = '${merged}'|" \
        "$conf" >"$tmp"
      cat "$tmp" >"$conf"
      rm -f "$tmp"
      ;;
  esac
else
  printf '\nshared_preload_libraries = '\''%s'\''\n' "$library" >>"$conf"
fi
