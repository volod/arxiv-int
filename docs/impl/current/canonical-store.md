# Canonical Store

The local database service is a project-owned ParadeDB Community derivative that keeps one
PostgreSQL major, `pg_search`, pgvector, and a pinned Apache AGE build together. Relational schema
application is in place: the irreversible initial Alembic revision `0001` owns contract tables, HASH
partitions, provenance constraints, roles, staging, the empty `derived` schema, and versioned
projection metadata. Head is `0004`, which adds `ctl.source_tombstone`, `ctl.prune_event`, and
`ctl.artifact_pin` on top of the `0003` progress and `0002` run-ledger overlays. A local dbt project
builds isolated derived generations
and projection inputs. Search, vector, and graph projections are rebuildable and are never
canonical.

Accepted records:
[0018 Build pinned ParadeDB + AGE image](../records/0018-store-build-pinned-paradedb-age-image.md);
[0021 Canonical relational schema](../records/0021-store-create-canonical-relational-schema.md);
[0024 dbt transformation foundation](../records/0024-store-implement-dbt-transformation-foundation.md);
[0025 Projections](../records/0025-store-implement-rebuildable-search-and-graph-projections.md);
[0041 Run ledger](../records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
[0043 Progress logging](../records/0043-pipeline-add-progress-logging-and-resource-telemetry.md);
[0049 Incremental reconciliation](../records/0049-pipeline-implement-incremental-reconciliation-and-stale-pruning.md).
The [foundation checkpoint](../records/0027-store-review-foundation-and-store-boundaries.md) and
[boundary repair](../records/0028-store-refactor-foundation-store-acceptance-boundaries.md) record
the integrated review and prerelease migration consolidation.

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
make transform-parse RUN_ID=...    # parse the dbt project without materializing
make transform-compile RUN_ID=...  # compile selected models
make transform-build RUN_ID=...    # build and test an isolated derived generation
make transform-test RUN_ID=...     # run data tests without replacing the active pointer
make projections-build RUN_ID=...  # KIND=all|lexical|vector|graph; APPLY=1 activates
make projections-status RUN_ID=... # show active projection pointers
make projections-cleanup RUN_ID=... # plan retired/failed drops (APPLY=1 executes)
```

CLI equivalents: `arxiv-int store build-image`, `arxiv-int store probe-image`,
`arxiv-int store apply-schema`, and
`arxiv-int transform parse|compile|build|test --run-id RUN_ID`.
Projection commands: `arxiv-int store projections-build|status|cleanup --run-id RUN_ID`.

Default probe data lands under
`$DATA_DIR/postgres-image-probe/<run-id>/pgdata`. Probe containers and Compose database runs use
the invoking host UID/GID so that tree stays operator-owned. Compose `database` uses the local
image tag; build the image before `make services-up`.

`make db-upgrade` applies the same Alembic history to `ARXIV_INT_MIGRATION_DATABASE_URL`.
`make db-apply-schema` uses that URL when set; otherwise it starts a disposable copy of the pinned
image with PGDATA under `$DATA_DIR/migrations/<run-id>/pgdata` and writes redacted catalog evidence
beside it. Missing image or URL is `not-run`, never a pass.

## Canonical schema

`src/arxiv_int/migrations/versions/0001_initial_store.py` is the only initial revision. Head is
`0004` (`0004_source_tombstone_and_prune.py`), which revises frozen `0003`
(`0003_stage_progress.py`) and `0002` (`0002_pipeline_run_ledger.py`).
The operator authorized 0001 consolidation before any
deployed database or public release. Each revision freezes SQLAlchemy definitions and narrow
PostgreSQL-specific SQL, without importing current contracts or runtime DDL copies.
`revision_manifest.json` pins checksums; `head_state.json` tracks the contract state used by
future revision generation. After deployment, schema changes require new reviewed revisions.
Initial teardown explicitly refuses destructive 0001 downgrade. 0004 downgrade drops reconcile
tables only. 0003 downgrade drops progress snapshots only. 0002 downgrade drops ledger tables
only. Repeat-at-head preserves rows, and failed application rolls back transactionally.

No generated catalog JSON snapshots are committed. Contract metadata and the frozen initial
revision are the comparison authorities. Live inspection checks owned columns, key order and
references, unique/check constraints, defaults, declared indexes, partition/staging structure,
role attributes and forbidden table writes, function bodies, and the embedding trigger identity.
Per-run observed definitions and findings are retained under `$DATA_DIR/migrations/<run-id>/`.
These are diagnostic evidence, not schema inputs that vary the migration on another computer.

Physical HASH partitions use the logical primary key so foreign keys stay valid. Application
`bucket` is a separate SHA-256 prefix via `ctl.partition_bucket` (first seven hex digits as
`bit(28)::int` modulo 16). Large corpus, knowledge, and search tables have 16 HASH children.

Roles `arxiv_int_migrator`, `arxiv_int_pipeline`, `arxiv_int_dbt`, and `arxiv_int_reader` are
`NOLOGIN` and granted to the connecting user for `SET ROLE`. The dbt role may `USAGE`/`CREATE` in
`derived` and `SELECT` canonical tables; it cannot write canonical rows or `alembic_version`.
`derived` is created empty by Alembic; dbt materializes isolated generation tables there.
Migrations ignore dbt-owned relations.

Fact checks require a subject and predicate, object XOR literal, document plus extractor
provenance, and a closed status set. `search.embedding_profiles` plus trigger
`search.enforce_embedding_profile` reject unknown profiles, mixed dimensions/digests, and duplicate
target-plus-profile rows.

Staging tables live in `staging` as `UNLOGGED` copies. `load_canonical_batch` fills `bucket`,
runs shared contract batch quality (with explicit Polars dtypes so omitted nullable strings stay
`Utf8`), binary-COPYs, then bound `INSERT ... ON CONFLICT DO UPDATE`. Quality failures raise
`StagingRejectedError` before COPY so inherited `NOT NULL` on staging cannot mask the gate.

Live adoption relocates `public.<table>` into the owned schema when the destination is missing,
refuses partial or drifted catalogs, and stamps `0004` when the overlay includes reconcile
tables, `0003` when it includes ledger and progress tables, `0002` when it includes ledger
tables only, or `0001` for a complete 0001-era catalog without those overlays; setup then
upgrades to head.

## Relational transformations

A local dbt Core project lives under `src/arxiv_int/resources/dbt/`. Optional extra `transform` pins
`dbt-core==1.12.3` and `dbt-postgres==1.10.2`. The typed runner in
`src/arxiv_int/transformations/` copies that project under `$DATA_DIR/dbt/<run-id>/project/`,
injects generated `src/arxiv_int/resources/contracts/generated/dbt/sources.yml`, and invokes parse, compile, build, or
test. Profiles use `env_var` placeholders only. Credentials come from
`ARXIV_INT_TRANSFORM_DATABASE_URL` or, when that is unset, `ARXIV_INT_MIGRATION_DATABASE_URL`.
Build and test without a URL are `not-run` (exit 2), never a pass.

Each run materializes isolated `derived.<model>__g_<generation>` relations after
`SET ROLE arxiv_int_dbt`. An exclusive lock under `$DATA_DIR/dbt/locks/` owns one generation.
`--activate` writes `$DATA_DIR/dbt/active-generation.json` only when build or test succeeded
(`activatable`). Activation requires current matching invocation ids, successful selected models and
attached tests, and every expected generation relation to exist (including views). Missing, stale,
or failed evidence cannot activate. Reserved generation/schema variables cannot be overridden.
The active generation cannot be rebuilt: use a new run id. Parse/test checks of an active generation
retain separate evidence; refused retries preserve published manifests. Pointer replacement uses an
atomic file rename. Failed tests, concurrent locks, and invalid models leave the pointer unchanged.
Sanitized `manifest.json` / `run_results.json` drop env maps and redact URLs; `--publish` copies
them to `$RUNS_DIR/<run-id>/{manifests,quality}/`. Logs and retained target artifacts are also
sanitized; invocation failures use stable diagnostics instead of exception representations. Threads
are capped at 4. Default select is
`tag:fixture tag:quality`.

The committed DAG is synthetic: `stg_documents` (view over `source('corpus','documents')`),
`stg_source_tombstones` (view over `source('ctl_reconcile','source_tombstone')`),
`int_documents_current` (incremental delete+insert with delete reconciliation),
`int_active_documents` (excludes last-occurrence tombstone hashes), and
`documents_current` (table). Domain tasks own business models. Python-only preparation uses
`prepare_document_frame` through the existing `StageRunner` seam documented in
[Pipeline control](pipeline-control.md); dbt Python models are not used.

Live checks skip unless `ARXIV_INT_RUN_DBT=1` and the pinned image is present. Fixture runs do not
claim corpus-scale or domain quality.

## Search and graph projections

The initial revision creates `ctl.projections`, `ctl.projection_active`, `ctl.projection_evidence`, and
`ctl.projection_cleanup`. Those rows are lifecycle metadata, not canonical documents or facts. The
pipeline role may create objects in `search`; dbt still cannot write projection metadata.

dbt models under `src/arxiv_int/resources/dbt/models/projections/` use tag `projections` (outside the default
`tag:fixture tag:quality` select). They materialize isolated
`derived.<model>__g_<generation>` relations with `source`/`ref` and uniqueness/relationship tests.
Version tokens reuse the dbt generation sanitizer so input table names match.

Engine adapters then build disposable search objects from those inputs:

- ParadeDB BM25 covering index on `search.lexical_p_<version>` with a Russian stemmer on body/title
  and a keyword tokenizer on identifiers
- pgvector HNSW candidate index on `search.vector_p_<version>` when selected embeddings exist
- compact `search.graph_p_<version>_{vertices,edges}` tables plus an AGE graph `g_<version>` when
  `age_enabled` is true

Graph-disabled mode still writes the relational tables and GraphML/JSON-LD/Turtle exports under
`$DATA_DIR/projections/<run-id>/exports/`, and sampled parity uses recursive SQL. AGE `create_graph`
runs on an autocommit session because it cannot live inside the metadata transaction.

Shared quality results (`projection.row_count`, `projection.logical_id_checksum`,
`projection.sampled_parity`, `projection.engine_object`) gate activation. Typed SQLAlchemy pointer
transactions write `ctl.projection_active` only when every requested kind is publishable. Failed or
incomplete builds leave the active pointer unchanged. Rebuilds from the same canonical fixtures keep
the same logical ids (chunk, embedding, object). Cleanup plans retired or failed engine objects that
are not active. Build and cleanup share a database advisory lock across tooling roots. Rebuilding an
active version is refused before preparing its dbt inputs. Cleanup executes only planned eligible
drops for the selected kinds and rechecks active status under the same lock; it never dispatches a
build. Refused retries
preserve the active version's evidence. Optional `--publish` copies sanitized `projections.json` to
`$RUNS_DIR/<run-id>/manifests/`.

`APPLY=1` on `make projections-build` passes `--activate`. Live checks skip unless
`ARXIV_INT_RUN_PROJECTIONS=1` and the pinned image is present. Fixture evidence is not a relevance
or scale claim.

## Modules and tests

- `arxiv_int.stores.postgres_image` -- pins, build, probes, compatibility gate, CLI helpers
- `arxiv_int.stores.postgres` -- apply, inspect, adopt, staging load, HASH bucket helper
- `arxiv_int.transformations` -- rooted dbt invocation, generation lock, activation, sanitized
  artifacts, and Polars preparation
- `arxiv_int.stores.projections` -- lifecycle, dbt inputs, ParadeDB/pgvector/AGE adapters, pointer
  switch, cleanup, and secret-free artifacts
- `tests/integration/extensions/` -- pin/NOTICE/gate unit coverage; live probes when
  `ARXIV_INT_RUN_EXTENSION_PROBES=1` (pytest `heavy`, not `make ci`)
- `tests/stores/` -- store boundary unit coverage; apply/adopt `not-run` without a URL or image
- `tests/stores/projections/` -- identifier, quality, lock, and mocked lifecycle coverage
- `tests/integration/postgres/` -- declared disposable schema run when
  `ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1` (pytest `heavy`, not `make ci`)
- `tests/transformations/` -- parse/compile/lock/activation/artifact units without a live store
- `tests/integration/dbt/` -- declared disposable dbt run when `ARXIV_INT_RUN_DBT=1`
  (pytest `heavy`, not `make ci`)
- `tests/integration/projections/` -- declared disposable projection run when
  `ARXIV_INT_RUN_PROJECTIONS=1` (pytest `heavy`, not `make ci`)
- Compose profile rendering accepts the project image tag without a registry digest, matching
  other `arxiv-int/*` images

## Initialization and upgrade seam

The disposable harness waits for PostgreSQL's final initialization-complete marker and a TCP
readiness check. A temporary initialization socket or the earlier ParadeDB bootstrap marker cannot
release database consumers while the server is about to restart.

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
