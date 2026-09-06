# Canonical Store

The local database service is a project-owned ParadeDB Community derivative that keeps one
PostgreSQL major, `pg_search`, pgvector, and a pinned Apache AGE build together. Relational
schema application, dbt transforms, and projection lifecycle remain later tasks; this page
documents the image and extension coexistence gate that those tasks consume.

Accepted record:
[0018 Build pinned ParadeDB + AGE image](../records/0018-store-build-pinned-paradedb-age-image.md).

## Image identity

| Pin | Value |
| --- | --- |
| Local image | `arxiv-int/postgres:17-0.25.6-age1.7.0` |
| Base | `paradedb/paradedb:0.25.6-pg17@sha256:044b8cc5b40159714e88e3f546fc74de11cf215c030190cc82c6627015d728ea` |
| PostgreSQL | 17.11 |
| `pg_search` | 0.25.6 |
| `vector` | 0.8.4 |
| Apache AGE | 1.7.0 (`e1467f12e0b1`, tag `PG17/v1.7.0-rc0`) |

Pins live in `docker/postgres/pins.env`. The Dockerfile derives from the ParadeDB digest, compiles
AGE for the same major, merges `age` into `shared_preload_libraries` without dropping
`pg_search`/`pg_cron`/`pg_stat_statements`, and ships `docker/postgres/NOTICE` plus upstream AGE
license files under `/usr/share/arxiv-int/`. ParadeDB Community remains AGPL-3.0 and does not claim
Enterprise HA or read-replica guarantees.

Research note: the design-table AGE commit `0e305662` (master, 1.8.0) does not compile against
PostgreSQL 17 (`index_beginscan` arity). The image therefore pins the PG17 release tag above.

## Operator commands

```text
make postgres-image            # build; add NO_CACHE=1 for a clean cache
make postgres-image-probe      # disposable PGDATA probes; WRITE_GATE=1 records the AGE gate
```

CLI equivalents: `arxiv-int store build-image` and `arxiv-int store probe-image`. Default probe data
lands under `$DATA_DIR/postgres-image-probe/<run-id>/pgdata`. Probe containers and Compose database
runs use the invoking host UID/GID so that tree stays operator-owned. Compose `database` uses the
local image tag; build the image before `make services-up`.

## Initialization and upgrade seam

`docker/postgres/initdb/20_arxiv_int_extensions.sh` runs after ParadeDB bootstrap and creates
`vector`, `pg_search`, then `age` in `template1`, `paradedb`, and `$POSTGRES_DB`. Existing clusters
initialized without AGE need: image upgrade, merge `age` into `shared_preload_libraries` (the
`merge_preload.sh` helper), restart, then `CREATE EXTENSION age` in each database that needs it.

## AGE compatibility gate

`docker/postgres/age-compatibility.json` records whether graph mode may require AGE. When
`age_enabled` is false, `make graph-up` / `arxiv-int services up --profiles graph` refuses, readiness
reports a degraded extension finding for graph selections, and extension requirements stay
`pg_search` + `vector` only. Relational graph work is unaffected. A successful
`make postgres-image-probe WRITE_GATE=1` sets `age_enabled` true after SQL, BM25, vector, Cypher,
transaction, restart, and dump/restore probes pass.

## Modules and tests

- `arxiv_int.stores.postgres_image` -- pins, build, probes, compatibility gate, CLI helpers
- `tests/integration/extensions/` -- pin/NOTICE/gate unit coverage; live probes when
  `ARXIV_INT_RUN_EXTENSION_PROBES=1`
- Compose profile rendering accepts the project image tag without a registry digest, matching
  other `arxiv-int/*` images
