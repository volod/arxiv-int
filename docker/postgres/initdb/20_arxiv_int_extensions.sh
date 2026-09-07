#!/bin/bash
# Install AGE after ParadeDB bootstrap creates vector and pg_search.
# shellcheck disable=SC2154
set -Eeuo pipefail

export PGUSER="${POSTGRES_USER}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# In the image, merge helper lives beside init scripts under /usr/local/lib/arxiv-int.
MERGE_PRELOAD="${SCRIPT_DIR}/../scripts/merge_preload.sh"
if [ ! -x "$MERGE_PRELOAD" ]; then
  MERGE_PRELOAD="/usr/local/lib/arxiv-int/merge_preload.sh"
fi

"$MERGE_PRELOAD" "$PGDATA/postgresql.conf" age

for DB in template1 paradedb "$POSTGRES_DB"; do
  echo "Loading Apache AGE into $DB"
  psql -d "$DB" -v ON_ERROR_STOP=1 <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS pg_search;
    CREATE EXTENSION IF NOT EXISTS age;
EOSQL
done

echo "arxiv-int AGE bootstrap completed"
