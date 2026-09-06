# Canonical Store

The local database service is a project-owned ParadeDB Community derivative that keeps one
PostgreSQL major, `pg_search`, pgvector, and a pinned Apache AGE build together. Relational schema
application is in place: Alembic `0001` owns contract tables, and reviewed revision `0002` overlays
HASH partitions, provenance constraints, roles, staging, and the empty `derived` schema. dbt
transforms and projection lifecycle remain later tasks.

Accepted records:
[0018 Build pinned ParadeDB + AGE image](../records/0018-store-build-pinned-paradedb-age-image.md);
[0021 Canonical relational schema](../records/0021-store-create-canonical-relational-schema.md).

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
make db-apply-schema           # apply owned revisions; URL or disposable PGDATA
make db-adopt                  # stamp after live catalog equivalence, or refuse
arxiv-int store inspect-schema # compare live catalog without applying
```

CLI equivalents: `arxiv-int store build-image`, `arxiv-int store probe-image`, and
`arxiv-int store apply-schema`. Default probe data lands under
`$DATA_DIR/postgres-image-probe/<run-id>/pgdata`. Probe containers and Compose database runs use
the invoking host UID/GID so that tree stays operator-owned. Compose `database` uses the local
image tag; build the image before `make services-up`.

`make db-upgrade` applies the same Alembic history to `ARXIV_INT_MIGRATION_DATABASE_URL`.
`make db-apply-schema` uses that URL when set; otherwise it starts a disposable copy of the pinned
image with PGDATA under `$DATA_DIR/migrations/<run-id>/pgdata` and writes redacted catalog evidence
beside it. Missing image or URL is `not-run`, never a pass.

## Canonical schema overlay

Revision `0001` remains the frozen contract-table baseline. Revision `0002` is a store overlay:
it does not import `arxiv_int.stores.postgres`, and its SHA-256 is pinned in
`revision_manifest.json`. Runtime helpers in `src/arxiv_int/stores/postgres/` are the operator copy
of the same names.

Physical HASH partitions use the logical primary key so foreign keys stay valid. Application
`bucket` is a separate SHA-256 prefix via `ctl.partition_bucket` (first seven hex digits as
`bit(28)::int` modulo 16). Large corpus, knowledge, and search tables have 16 HASH children.

Roles `arxiv_int_migrator`, `arxiv_int_pipeline`, `arxiv_int_dbt`, and `arxiv_int_reader` are
`NOLOGIN` and granted to the connecting user for `SET ROLE`. The dbt role may `USAGE`/`CREATE` in
`derived` and `SELECT` canonical tables; it cannot write canonical rows or `alembic_version`.
`derived` is created empty; this task does not own dbt model tables.

Fact checks require a subject and predicate, object XOR literal, document plus extractor
provenance, and a closed status set. `search.embedding_profiles` plus trigger
`search.enforce_embedding_profile` reject unknown profiles, mixed dimensions/digests, and duplicate
target-plus-profile rows.

Staging tables live in `staging` as `UNLOGGED` copies. `load_canonical_batch` fills `bucket`,
runs shared contract batch quality (with explicit Polars dtypes so omitted nullable strings stay
`Utf8`), binary-COPYs, then bound `INSERT ... ON CONFLICT DO UPDATE`. Quality failures raise
`StagingRejectedError` before COPY so inherited `NOT NULL` on staging cannot mask the gate.

Live adoption relocates `public.<table>` into the owned schema when the destination is missing,
refuses partial or drifted catalogs, and stamps `0001` or `0002` from overlay completeness.
`ctl.runs` ledger tables remain a later task.

## Modules and tests

- `arxiv_int.stores.postgres_image` -- pins, build, probes, compatibility gate, CLI helpers
- `arxiv_int.stores.postgres` -- apply, inspect, adopt, staging load, HASH bucket helper
- `tests/integration/extensions/` -- pin/NOTICE/gate unit coverage; live probes when
  `ARXIV_INT_RUN_EXTENSION_PROBES=1`
- `tests/stores/` -- overlay unit coverage; apply/adopt `not-run` without a URL or image
- `tests/integration/postgres/` -- declared disposable schema run when
  `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1`
- Compose profile rendering accepts the project image tag without a registry digest, matching
  other `arxiv-int/*` images

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
