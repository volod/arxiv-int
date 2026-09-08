# arxiv-int Project Specification

## Purpose

`arxiv-int` is a local-first Knowledge Discovery Platform for multi-terabyte, mostly
Russian-language document archives. Its input is one or more readable directory silos of ordinary
files that the pipeline treats as immutable; its output is evidence-backed knowledge: canonical
objects, provenance-bearing facts, and the
search, graph, and investigation views built from them. Its Python distribution and import package
are both `arxiv-int` / `arxiv_int`. The system inventories and normalizes an immutable archive,
builds reproducible lexical and selected semantic indexes, discovers topics, extracts and resolves
entities and facts, classifies source files in a UDC-derived hierarchy, projects a knowledge graph
and evidence-backed domain artifacts, and supports local search, analysis, and visualization without
requiring document or prompt egress. Required outputs include company, product, and person catalogs,
explainable anomaly findings, and an analyst report linking summaries to exact evidence. Financial,
bookkeeping, and product-description lanes support party relationships, supply chains, and
evidence-backed bills of materials. An explicit, separately authorized maintenance command can
reorganize the archive after classification -- copying the classified tree into a target directory,
or moving the silo in place -- while preserving an auditable original-to-current path map.

The target workstation typically has about 128GB of RAM and 16GB of GPU VRAM. Speed is secondary to
quality, but every expensive result must be resumable, attributable, and independently rebuildable.
The deployment boundary is one CUDA-capable host; one GPU is sufficient. Multiple local GPUs are an
optional profile, never a minimum requirement. Hardware and model defaults are planning assumptions,
not evidence that a specific model fits or meets extraction quality.

The commands and capabilities below describe the target product. The
[current implementation](../impl/current.md) currently supplies foundation and runtime primitives;
it does not yet provide the end-to-end archive-to-knowledge pipeline.

This specification is living. Product behavior, boundaries, and evaluation belong here. Remaining
implementation work belongs in `plan.md`; delivered behavior must eventually move to focused pages
under `docs/impl/current/`. The [execution architecture](architecture.md) defines stage dependencies,
module ownership, and publication boundaries for that implementation.

## Technical references

The following recorded references inform the design; inspected revisions are not current-version
guarantees or deployment acceptance. Revalidate API/version/licence assumptions and compatibility
before a pin enters the lock or deployment image. Upstream capability descriptions are not measured
project results.

| Source                                                                                                        | Inspected revision                                          | Design consequence                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [ParadeDB](https://github.com/paradedb/paradedb/tree/c74bcde7bf6f6e44516d81f18350f2725d14fd5f)                | `c74bcde` (`0.25.6` workspace version)                      | ParadeDB is now a Postgres custom index for BM25, vector, hybrid, filters, aggregates, and joins, not merely an OpenSearch-like sidecar. Native vector indexing is still documented as beta. |
| [Apache AGE](https://github.com/apache/age/tree/0e30566226f017d53b7f52025803b38af3ad2b3f)                     | `0e30566`; README advertises AGE 1.8.0 and PostgreSQL 11-18 | AGE is feasible on the same PostgreSQL major, but the ParadeDB combination is not listed as an upstream-tested extension set and needs a project-owned image and compatibility gate.         |
| [pgvector](https://github.com/pgvector/pgvector/tree/e48241b4dcc045b18902914f668d03d1d399dfbe)                | `e48241b`; README install pin `0.8.6`                       | Stable exact, HNSW, IVFFlat, half-vector, binary-quantization, and iterative-scan baseline; large HNSW builds remain memory and maintenance intensive.                                       |
| [ODCS](https://github.com/bitol-io/open-data-contract-standard/tree/f5bfbb813fe2c0551e2c324913f330e7807885d8) | `f5bfbb8`; standard `3.1.0`                                 | ODCS is the human and machine-readable contract source of truth; its custom properties carry project generation hints that the standard does not define.                                     |
| [UDC Consortium](https://udcc.org/index.php/site/page?view=about_structure) and [UDC Summary](https://udcsummary.info/php/index.php?lang=en) | Web references inspected 2026-09-04                        | UDC supplies a faceted, syntactically expressive hierarchy; the project must pin an authorized vocabulary snapshot and keep local outcomes/extensions distinguishable from official notation. |

Relevant implementation constraints:

- ParadeDB documents a covering LSM-based inverted/columnar index, Russian Snowball stemming,
  Russian stopwords, Unicode and ICU tokenization, concurrent reindexing, and single-node production
  deployments in the 1-10 TB range. That scale statement is a vendor observation, not an `arxiv-int`
  acceptance result. See [architecture](https://www.paradedb.com/docs/welcome/architecture),
  [token filters](https://www.paradedb.com/docs/documentation/token-filters/stemming), and
  [limitations](https://www.paradedb.com/docs/welcome/limitations).
- ParadeDB `0.25.x` documents native SPANN-style vector search and hybrid RRF as beta. The design
  therefore retains pgvector as the stable baseline and treats native ParadeDB vector indexing as a
  benchmark candidate, not an unqualified default. See
  [vector search](https://www.paradedb.com/docs/documentation/vector/overview).
- The official ParadeDB image includes `pg_search`, pgvector, PostGIS, `pg_ivm`, and `pg_cron`, but
  its tested third-party list does not name AGE. See
  [third-party extensions](https://www.paradedb.com/docs/deploy/third-party-extensions).
- Apache AGE provides SQL/openCypher hybrid queries and AGE Viewer, but does not replace Neo4j's
  complete graph-data-science and administration ecosystem. See the
  [AGE project](https://github.com/apache/age) and
  [AGE Viewer](https://github.com/apache/age-viewer).
- ODCS `3.1.0` is the selected contract version. The open-source Data Contract CLI can lint,
  compare breaking changes,
  test Postgres, and export SQL, Avro, JSON Schema, and other formats. See
  [ODCS](https://github.com/bitol-io/open-data-contract-standard) and
  [Data Contract CLI](https://docs.datacontract.com/).
- Avro schema resolution supports aliases, defaults, and compatible type promotion, but
  compatibility policy is not automatic merely because a schema is Avro. The project must enforce
  its own reviewed version and migration policy. See the
  [Avro specification](https://avro.apache.org/docs/current/specification/).
- Docker Compose uses `.env` for interpolation, with shell values taking precedence; the resolved
  model can be inspected with `docker compose config --environment`. See
  [Docker's interpolation rules](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).
- Ollama supports a recommended systemd service, local embedding endpoint, and JSON-schema
  structured output. See [Linux service setup](https://docs.ollama.com/linux),
  [embeddings](https://docs.ollama.com/api/embed), and
  [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).
- UDC notation is hierarchical and faceted: longer simple notations express narrower concepts, and
  auxiliaries or connecting signs represent language, form, place, time, and relationships. The
  freely reusable UDC Summary contains about 2,600 classes under CC BY-SA 3.0; software use of the
  complete Master Reference File requires the applicable UDC Consortium licence. See the
  [UDC Summary](https://udcsummary.info/php/index.php?lang=en) and
  [UDC licence terms](https://udcc.org/index.php/site/page?view=licences).

## Design principles

The trust and rebuild chain is:

```text
immutable archive
  -> content-addressed inventory
  -> normalized, contract-versioned Parquet/Avro artifacts
  -> canonical objects and provenance-bearing facts
  -> rebuildable lexical, vector, topic, and graph projections
  -> evaluated search, analysis, and visualization
```

The governing principles are:

1. **Local by default.** No corpus text, extracted facts, embeddings, or prompts leave the host.
2. **One canonical database, not one irreplaceable copy.** PostgreSQL is the transactional and query
   center. The normalized lake is the recovery and bulk-analysis substrate.
3. **Contracts before stores.** ODCS contracts and canonical semantic mappings define the data;
   physical schemas, validators, and migrations are generated or checked from them.
4. **Projections are disposable.** ParadeDB indexes, pgvector indexes, and AGE vertices/edges can be
   rebuilt from normalized artifacts plus canonical PostgreSQL rows.
5. **Cheap analysis gates expensive analysis.** Inventory, hashes, lexical statistics, language, and
   lightweight NER run before embedding and LLM extraction. The full archive is not embedded by
   default.
6. **Evidence survives every transformation.** Each chunk, entity mention, fact, topic assignment,
   and answer retains document, byte/page/span, contract, code, model, prompt, and run provenance.
7. **Long runs are restartable.** Work is sharded, journaled, idempotent, and committed atomically.
8. **Adopt on measured evidence.** Search, vector, graph, model, and extraction choices are promoted
   only when representative held-out evaluations justify their cost.
9. **Source identity outlives location.** Content identity and captured evidence never depend on a
   file remaining at one path; every authorized physical move is precomputed and recorded.
10. **Usable stages prove themselves on archive data.** A stage group is not complete when only
    fixtures pass; it must publish a validated proof bundle from the operator-provided test archive.

Ontology classes, predicates, and analyst-facing graph labels follow
[Ontology design](#ontology-design).

## Scope

The first production-shaped release includes:

- recursive inventory of one or more declared source silos with stable identities, source-root
  attribution, MIME/encoding/language detection, hashes, exact deduplication, and quarantines;
- text and metadata extraction from common office, text, email, archive, image, and PDF formats,
  with OCR/layout lanes selected by policy;
- versioned, multi-label hierarchical source classification derived from UDC, including explicit
  `unclassified` and `unreadable` outcomes, plus a separately authorized archive-reorganization
  command that either copies the classified tree to a target directory or moves the silo in place,
  with a reversible path ledger;
- normalized partitioned Parquet datasets and optional Avro object containers;
- Russian-aware BM25 search, metadata filters, snippets, and hybrid retrieval;
- selective multilingual embeddings and reranking as evaluated optional branches; cited local
  question answering is an optional discovery refinement;
- topic discovery, entity mentions, entity resolution, provenance-bearing fact extraction, ontology
  assets, and graph projection;
- explicit company/legal-entity, product, and person catalogs with aliases, identifiers, roles,
  temporal relations, evidence, and unresolved identities;
- registered relationship, bill-of-materials, supply-chain, and invoice/payment investigation
  artifacts when the archive contains sufficient evidence;
- explainable anomaly findings and a portable analyst entry report with topics, catalogs,
  relationship graphs, coverage, prioritized findings, and source-level drill-down;
- PostgreSQL/ParadeDB as the canonical service; optional AGE, AGE Viewer, Grafana, and vLLM
  profiles;
- a typed Python CLI, standardized Make targets, Docker Compose, `.env.example`, progress logs, run
  manifests, and operator reports;
- content- and implementation-aware incremental updates, targeted invalidation, safe stale-artifact
  pruning, full rebuild generations, and a pre-run time/storage/free-space forecast;
- read-only proof runs over an operator-provided test archive after each usable pipeline stage group;
- deterministic unit/contract/integration tests plus representative corpus evaluations.

The initial release does not promise:

- embedding or LLM-processing every byte in a multi-terabyte archive;
- horizontal scale, high availability, or zero-downtime disaster failover on one workstation;
- automatic acceptance of LLM-generated facts or ontology axioms as truth;
- full Neo4j Graph Data Science parity, OpenSearch cluster parity, or Qdrant billion-vector parity;
- automatic destructive schema migration;
- unattended or confidence-only movement of source files;
- lossless extraction from every proprietary, corrupt, encrypted, or handwriting-heavy document;
- certification that generated bills of materials, supply chains, invoices, or payment links are
  complete accounting, engineering, or legal truth;
- remote model APIs, hosted telemetry, or cloud object storage.

## Architecture decision

### Recommendation

Use a **pinned ParadeDB Community image as the base PostgreSQL distribution**, not stock PostgreSQL
plus a separately assembled `pg_search` installation. Keep a working core image without AGE and
build an optional project-owned derivative on the same supported PostgreSQL major to add AGE.
Enable AGE and its viewer through a Compose
profile until the compatibility and graph acceptance gates pass.

The default store policy is:

- ParadeDB custom index for Russian-aware BM25, filters, snippets, facets, and lexical retrieval;
- pgvector for the stable first semantic baseline on a selected chunk tier;
- ParadeDB native vector search as an experimental candidate because upstream still calls it beta;
- relational `kg.object`, `kg.fact`, `kg.mention`, and `kg.alias` tables as the canonical graph
  data;
- Apache AGE as a rebuildable Cypher projection, never the only copy of an object or fact;
- normalized Parquet plus manifests as the bulk, portable rebuild source.

This reasonably replaces OpenSearch + Qdrant + Neo4j for the target **single-host discovery
workload**, subject to pilot gates. It reduces three database services and three synchronization
paths to one PostgreSQL service and one projection job. It does not prove equivalent scale or
feature parity.

### Option comparison

| Option                                                       | Decision              | Reason                                                                                                                                                                                       |
| ------------------------------------------------------------ | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ParadeDB image + pgvector + optional AGE                     | **Adopt as baseline** | Least service sprawl; Russian BM25 support; transactional joins between provenance, facts, and search; official image already carries pgvector; AGE can share the PostgreSQL major.          |
| Stock PostgreSQL + manually built `pg_search`, pgvector, AGE | Reject for default    | It recreates ParadeDB packaging work, increases extension/upgrade risk, and provides no product benefit. Keep only as an emergency build path.                                               |
| OpenSearch + Qdrant + Neo4j                                  | Defer as escape hatch | Strong specialized ecosystems, but multiplies storage, synchronization, operations, and schema drift. Reintroduce only the store whose acceptance gate the combined PostgreSQL design fails. |
| ParadeDB native vector only                                  | Experimental          | Attractive shared index and filtered hybrid search, but upstream marks it beta in `0.25.x`.                                                                                                  |
| pgvector over every chunk                                    | Reject                | Multi-terabyte all-corpus HNSW is inconsistent with the memory, build-time, maintenance, and storage envelope of the target host.                                                            |
| AGE as canonical fact storage                                | Reject                | AGE is useful for traversal, but canonical relational facts provide clearer constraints, provenance, bitemporality, migrations, and bulk load/rebuild semantics.                             |

### Promotion and fallback gates

- Replace pgvector with ParadeDB native vector only if held-out recall, filtered-query latency,
  index build/rebuild, update behavior, and recovery all pass.
- Add Qdrant only if neither vector option reaches the declared recall/latency/storage target on the
  representative selected-vector tier.
- Keep AGE only if extension coexistence, backup/restore, query correctness, and graph latency pass.
  Otherwise retain relational recursive SQL and export GraphML/RDF; add Neo4j only if required graph
  algorithms or visualization cannot be met.
- Add OpenSearch only if ParadeDB misses Russian relevance, index build/rebuild, stability, or
  operational recovery targets after measured tuning.

## Logical architecture

```text
Disk A: ARCHIVE_DIR (pipeline read-only) Disk B: RESULTS_DIR
          |                                      |
          v                                      v
 inventory -> extract -> normalize -> dedupe -> partitioned Parquet/Avro
                          |                       |
                          +---- run manifests ----+
                                      |
                                      v
Disk C: PGDATA_DIR         ParadeDB / PostgreSQL (tables and indexes)
                    +-------------------------------+
                    | ctl: runs, shards, contracts  |
                    | corpus: docs, spans, chunks   |
                    | kg: objects, mentions, facts  |
                    | ontology: terms, mappings     |
                    | eval: gold items and metrics  |
                    | ParadeDB lexical index        |
                    | pgvector / candidate vectors  |
                    | AGE graph projection          |
                    +-------------------------------+
                         |       |        |
                         v       v        v
                     CLI/API  Grafana  AGE Viewer
                         |
                Ollama system service
                or optional vLLM container
```

The checkout can live on any other disk and holds only code, documentation, and its own `DATA_DIR`
tooling output. No corpus runtime path is derived from the checkout unless the operator deliberately
accepts a local default for a small trial. The optional archive-reorganization target is a further
independent root, written only by that authorized command. The organizer consumes a sealed
classification export and source-location manifest through the artifact contract; the pipeline
never imports its placement executor or requests archive write access.

## Repository and package structure

Behavior that exists today is indexed by [current implementation](../impl/current.md); the target
layout the capabilities below build toward is:

```text
arxiv-int/
  AGENTS.md
  Makefile
  make/                         # grouped Make fragments with ##@ help sections
  docker/compose.yaml
  .env.example
  pyproject.toml
  uv.lock
  docker/
    postgres/Dockerfile
    postgres/initdb/
    grafana/
  src/arxiv_int/
    cli.py
    metadata.py
    resources/                  # packaged assets shipped in the wheel
      configs/                  # operator profiles and policies
      contracts/                # ODCS registry, datasets, generated schemas
      ontology/                 # Turtle and SHACL assets
      dbt/                      # dbt Core project (Python stays transformations/)
    runtime/
    interfaces/
    adapters/
    contracts/                  # catalog, lint, generate, evolution, migrations, sqlalchemy
    migrations/                 # Alembic environment and immutable Python revisions
      versions/
    data_quality/               # engine, rules, generate
    transformations/            # Typed Polars operations and dbt invocation
    readiness/
    pipeline/                   # dag, run, quality, plus control/forecast/publish/prune/reconcile
    stores/
    inference/                  # client, providers, scheduler, policy
    observability/              # logging, metrics, sinks
    extraction/
    classification/
    archive/
    retrieval/
    nlp/
    identity/
    graph/
    domain_artifacts/
    analytics/
    query/
    reporting/
    security/
    evaluation/                 # bundles, fixtures, families, proof, evaluate, scoring
    quality/
  tests/                        # mirrors src/arxiv_int subpackages
  docs/
    design/spec.md
    impl/plan.md
    impl/current/
    guide/
  scripts/shared/common.sh
```

Packaged `src/arxiv_int/resources/configs/` holds versioned operator profiles and policies;
`src/arxiv_int/resources/ontology/` holds Turtle and SHACL assets. Checkout overlays of the same
directory names win when present so tests can copy disposable trees.

Production code lives in the functional package that owns its behavior. No package is organized by
implementation history, and directories arrive with the capability that needs them rather than in
advance.

Custom Python is orchestration and domain policy, not reimplementation of Tika, Docling, OCR,
ParadeDB, pgvector, AGE, DuckDB, PyArrow, or model runtimes. Production modules remain typed and
cohesive; CLI parsing does not own pipeline behavior.

## Configuration and multi-SSD paths

Configuration precedence is:

```text
explicit CLI option > process environment > .env > documented safe default
```

`.env.example` is committed and `.env` is ignored. `make bootstrap` copies the template when `.env`
does not exist and otherwise appends declarations newly introduced by the template without changing
or duplicating existing active or commented declarations. It installs the locked environment and
then verifies package identity and runs readiness; a degraded result remains usable while a blocked
result fails the bootstrap.
Compose is always invoked with an explicit project directory and `--env-file`, so copying the
checkout to another disk does not change path resolution. `make config` renders redacted
application configuration and runs `docker compose config --environment`. No committed file carries
a machine-specific absolute path:
`.env.example` describes each root by the storage class it needs and leaves every value to the
operator's `.env`.

### Operator roots

The operator configures three roots, one per job:

| Root            | Holds                                                                              | Access             |
| --------------- | ---------------------------------------------------------------------------------- | ------------------ |
| `ARCHIVE_DIR`   | The source silos: the operator's own files, untouched                              | Pipeline read-only |
| `RESULTS_DIR`   | Everything the pipeline produces: normalized datasets, runs, logs, reports, proofs  | Read-write         |
| `PGDATA_DIR`    | The one PostgreSQL data directory: canonical tables and every lexical, vector, and graph index | Operator UID (`RUNTIME_UID`); exclusive to the database process |

Nothing else is required to start. The remaining variables are overrides with documented defaults
inside those roots, so a working configuration is three paths, a database password, and a model
profile. Every derived default is a placement decision an operator may need to change when the three
roots do not share one storage class, which is the normal case on a multi-disk workstation.

### Storage classes and device placement

Roots are not differentiated by which kind of data they hold but by who owns the bytes, how the bytes
are written, and what is lost when the device is lost. Six storage classes cover the system, and the
preflight classifies every configured path against the class its consumer requires:

| Class           | Written by            | Access pattern                          | Device and filesystem requirement                                              | Locations                                             |
| --------------- | --------------------- | --------------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------- |
| `source`        | Not by the pipeline   | Large sequential reads, one full pass per inventory | Any readable directory; host write permission and rotational storage are acceptable | `ARCHIVE_DIR` silos |
| `bulk`          | Pipeline stages       | Large sequential writes, occasional full scans | Capacity first; rotational and non-native filesystems are acceptable    | `RESULTS_DIR` and its `normalized`, `runs`, `proofs`, `exports`, `quarantine` trees |
| `database`      | PostgreSQL only       | Small random reads and writes with ordered `fsync` | PostgreSQL-supported filesystem, real per-file ownership, exclusive use; rotational disks acceptable | `PGDATA_DIR`, optional `PG_WAL_DIR`, optional tablespace roots |
| `scratch`       | Pipeline workers      | High-churn random writes, deleted after the stage | Writable storage with bounded free space; rotational disks acceptable | `TMP_DIR` |
| `model`         | Model runtimes        | Large random reads at load, then read-mostly | Sufficient capacity and access permissions; rotational disks acceptable | `MODEL_CACHE_DIR` |
| `service-state` | Local services        | Small random writes with file locking   | POSIX filesystem with real ownership; small; retain unprovisioned state in backup | `SERVICE_STATE_DIR`                       |

Rotational disks are accepted for every storage class, including database, model cache, and scratch.
Their rotational flag remains recorded as performance evidence and does not degrade readiness.
Unsupported database filesystems or missing ownership/exclusive-use semantics remain blocking;
service state without filesystem ownership remains degraded. Permission and free-space checks still
apply independently of device type.

### Why indexes, tables, and visualization artifacts do not get their own roots

Splitting storage further is only correct where the split follows an ownership boundary that already
exists:

- **Lexical, vector, and graph indexes are not separable directories.** ParadeDB `pg_search`,
  `pgvector`, and AGE are PostgreSQL extensions, so their indexes are cluster relations. The only
  supported way to move them is a tablespace, and a tablespace is part of the cluster's backup and
  recovery unit: a second root would be independently losable while still being required to recover.
  One `PGDATA_DIR` is therefore the default and the documented safe answer.
- **Tables and indexes may be split only onto a device of the same class.** `PG_WAL_DIR` and
  `PG_TABLESPACE_<NAME>_DIR` exist as optional, unset-by-default overrides for an operator with a
  second device of the `database` class. They are accepted only when the target matches the class of
  `PGDATA_DIR`, are recorded in the run manifest, and are named in the backup runbook as part of the
  same cluster. Placing a tablespace on a slower or non-native device to gain capacity is refused,
  because it trades a durable cluster for space that `RESULTS_DIR` already provides.
- **Visualization artifacts are pipeline output, not a store.** Rendered reports, HTML/SVG,
  GraphML, JSON-LD, and portable exports are written under `RESULTS_DIR` in
  `runs/<run-id>/reports/`, `runs/<run-id>/artifacts/`, and `exports/`, so generated views
  can be regenerated in one place. Review events and path ledgers have separate retention rules.
- **Mutable service state is separable, and is the one root worth adding.** Grafana's own database
  and plugins, a Prometheus TSDB, and AGE Viewer state are written by services rather than by the
  pipeline, need real file ownership and locking, and are not derived views. Unprovisioned state
  requires backup just like operator decisions under `RESULTS_DIR`. They live under
  `SERVICE_STATE_DIR`, which defaults to `${RESULTS_DIR}/services`
  and must be pointed at a `service-state`-capable path when the results root cannot express
  ownership. Dashboard and datasource definitions stay provisioned from `docker/grafana/` in the
  repository, so this root holds runtime state only.

### Variables

| Variable                                                | Purpose                                              | Storage class   | Default policy                                                 |
| ------------------------------------------------------- | ---------------------------------------------------- | --------------- | -------------------------------------------------------------- |
| `ARCHIVE_DIR`                                           | Input silos opened or mounted read-only by the pipeline | `source`    | Required for corpus stages; host write permission is acceptable |
| `RESULTS_DIR`                                           | Single pipeline output root                          | `bulk`          | Required for corpus stages; must not be inside the archive or the checkout |
| `PGDATA_DIR`                                            | PostgreSQL data and index directory; rotational disks acceptable | `database` | Required for services                                     |
| `RUNS_DIR`                                              | Run journals, logs, reports, checkpoints             | `bulk`          | `${RESULTS_DIR}/runs`                                          |
| `SERVICE_STATE_DIR`                                     | Grafana, Prometheus, and AGE Viewer runtime state    | `service-state` | `${RESULTS_DIR}/services`; must be moved when that path cannot express ownership |
| `MODEL_CACHE_DIR`                                       | Hugging Face/model cache                             | `model`         | `${RESULTS_DIR}/models`                                        |
| `TMP_DIR`                                               | Bounded extraction and sort scratch                  | `scratch`       | `${RESULTS_DIR}/tmp`                                           |
| `PG_WAL_DIR`                                            | Write-ahead log on a second `database` device        | `database`      | Unset; the WAL stays inside `PGDATA_DIR`                       |
| `PG_TABLESPACE_<NAME>_DIR`                              | Optional named tablespace on a second `database` device | `database`   | Unset; every relation stays inside `PGDATA_DIR`                |
| `DATABASE_URL`                                          | Host-side application connection                     | --              | Local-only default assembled from non-secret fields            |
| `POSTGRES_PASSWORD`                                     | Database secret                                      | --              | No committed value; readiness rejects placeholder in non-dev mode |
| `OLLAMA_BASE_URL`                                       | Host Ollama endpoint                                 | --              | `http://127.0.0.1:11434` for host CLI                          |
| `INFERENCE_BACKEND`                                     | `ollama` or `vllm`                                   | --              | `ollama`                                                       |
| `EMBEDDING_MODEL`, `GENERATION_MODEL`, `RERANK_MODEL`   | Model identities for the selected backend             | --              | Generation defaults to `qwen3.8:27b` on Ollama, or `VLLM_MODEL` on vLLM; other roles require explicit selection |
| `GENERATION_MODEL_REVISION`                             | Immutable Hugging Face generation-model revision    | --              | Revision paired with `GENERATION_MODEL`                        |
| `VLLM_MODEL`, `VLLM_MODEL_REVISION`                     | Alternate vLLM service model and revision            | --              | Pinned Qwen3.8 27B FP8 repository and revision; independent of the Ollama model tag |
| `VLLM_TENSOR_PARALLEL_SIZE`, `VLLM_CPU_OFFLOAD_GB`     | vLLM multi-GPU and host-RAM allocation               | --              | Evaluated CUDA-host profile                                    |
| `VLLM_GPU_MEMORY_UTILIZATION`, `VLLM_MAX_MODEL_LEN`     | vLLM memory and context bounds                       | --              | Evaluated CUDA-host profile                                    |
| `DATA_DIR`                                              | Repository-local root for developer tooling only     | --              | `.data`, resolved from the project root                        |
| `LOG_LEVEL`, `LOG_FORMAT`, `PROGRESS_INTERVAL_SEC`      | Operator feedback                                    | --              | `INFO`, console plus JSONL, 30 seconds                         |
| `PIPELINE_WORKERS`, `BATCH_SIZE`, `GPU_MAX_CONCURRENCY` | Resource bounds                                      | --              | Auto-detected conservative values; GPU concurrency `1`         |

Path preflight must resolve symlinks, prove source and destinations are distinct, verify each
archive is a readable directory, verify outputs are writable, record filesystem type, device
identifier, and rotational flag, classify each path against its required storage class, estimate
free space, and
refuse dangerous roots such as `/`. Docker receives absolute bind-mount sources, even when `.env`
contains paths relative to the project root. The recorded filesystem type, device id, rotational
flag, and storage class of every root enter the run manifest, so a slow or unsafe placement is
visible in the evidence rather than inferred later from timings.

### Source silos

The archive input is a declared set of one or more source roots that the pipeline opens without
modification. Host filesystem write permission is allowed and is not a readiness failure.
`ARCHIVE_DIR` is the one-silo case and carries the `default` id;
`ARCHIVE_SILO_<ID>_DIR` declares each additional or
alternative root, with underscores normalized to hyphens in the stable lowercase id. The silo id is
part of source identity: every inventory row, document, path
event, quarantine record, classification row, and move-ledger entry stores its silo id together with
the root-relative path, so two silos may hold the same relative path without colliding and any
derived fact can name the silo it came from. Content identity remains the content hash, so the same
bytes found in two silos are one document with two source locations rather than two documents.
Silos may sit on different filesystems, and each is separately declared readable, forecast, and
counted; the archive-reorganization command operates on exactly one silo per plan.

### The results root

`RESULTS_DIR` is the single output root, so an operator can point one path at a spare disk, inspect
everything the system produced in one tree, and archive that tree without touching the
source silos or the database. Deletion must preserve the decision and recovery records below.
Its layout is fixed and documented:

```text
$RESULTS_DIR/
  normalized/   contract-versioned Parquet and Avro datasets: inventory, documents, spans, chunks,
                classifications, nlp, mentions, facts, linkage, embeddings, topics, catalogs,
                domain-artifacts, anomalies
  quarantine/   inputs that could not be processed, by reason
  runs/         one directory per run: journal, logs, manifests, telemetry, evaluation, reports
  decisions/    backed-up review, identity, policy, and path-ledger exports; never disposable
  proofs/       provided-archive proof bundles, by capability and proof id
  exports/      operator-requested portable outputs, including rendered graphs and reports
  services/     local service runtime state, unless SERVICE_STATE_DIR points elsewhere
  models/       model cache, unless MODEL_CACHE_DIR points elsewhere
  tmp/          bounded scratch, unless TMP_DIR points elsewhere
```

Derived datasets and rendered views are rebuildable from retained source snapshots, contracts,
code, pinned tools/models, and decision overlays. Byte-identical model regeneration is not assumed.
Operator reviews, identity overrides, accepted policies, run evidence, and archive path ledgers
cannot be recreated from source bytes. They require independent backup and are never disposable
just because they live under `RESULTS_DIR`. No generated view is the only copy of a source file.
The three subtrees with their own
variables allow independent capacity and access placement: scratch and model cache can use either
rotational or solid-state storage, while service state needs real ownership. Separate disks are
optional; suitable derived paths under the results root are accepted.

`PGDATA_DIR` is separate because PostgreSQL owns that directory exclusively and its failure and
backup semantics differ from a lake of files. Keeping indexes inside `PGDATA_DIR` rather than in a
fourth root is deliberate: ParadeDB, pgvector, and AGE are all PostgreSQL extensions, so their
storage is part of the database.

`DATA_DIR` is not part of this model. It is the repository's own convention for developer tooling --
linter, type-checker, and test caches, and local records produced by repository tasks -- and it
defaults to `.data` inside the checkout. Corpus-scale output never goes there, and preflight refuses
a `RESULTS_DIR` or `PGDATA_DIR` that resolves inside the checkout unless the operator states that
intent for a small local trial.

Proof tasks retain source manifests and hashes in repository documentation. No source-derived
example is committed; see
[published proof and evaluation data](#published-proof-and-evaluation-data).
A bounded disposable copy under the configured data root may be used for addition,
modification, and removal drills.

`ARCHIVE_DIR` remains read-only for analysis. The archive-reorganization command is the sole
exception, and only in its `move` mode: it takes an explicit silo root, runs outside the read-only
service mounts, defaults to dry-run, and requires `--apply` plus the accepted classification and plan
ids before requesting write access. Its `copy` mode needs no write access to the archive at all -- it
reads the silo read-only and writes into an explicit target root that must not overlap the archive,
the results root, or the database directory.

### Development workstation configuration

A development workstation configures the same variables as an operator installation; there is no
second path model and no development-only default that a production run would not also use. What
differs is placement, because a development machine usually has one fast disk holding the archive and
one large slow disk for output:

- point `ARCHIVE_DIR` at the authorized representative slice during development, or at the real
  archive silo for a production-like run, so ordinary pipeline, forecast, and proof commands read
  one source without modifying it; there is no second proof-only source root;
- point `RESULTS_DIR` at the bulk output disk and let `RUNS_DIR`, `exports/`, and `proofs/` derive
  from it, so every pipeline result lands in one inspectable tree;
- choose `PGDATA_DIR`, `TMP_DIR`, and `MODEL_CACHE_DIR` for sufficient capacity; rotational disks
  are acceptable. PostgreSQL still requires its supported filesystem and ownership semantics, and
  `SERVICE_STATE_DIR` needs filesystem ownership;
- keep `DATA_DIR` at its `.data` default inside the checkout; it is developer tooling state, never a
  corpus or results location.

The preflight reports each of these placements with its measured device and filesystem, so the
difference between a deliberate trial on a slow disk and an accidental one is visible before a long
run starts.

## Docker and local-service topology

Compose profiles allow bounded service selections:

| Profile         | Services                                      | Notes                                                                                   |
| --------------- | --------------------------------------------- | --------------------------------------------------------------------------------------- |
| `core`          | project-derived ParadeDB/PostgreSQL           | Pinned image, healthcheck, persistent bind mount, localhost port only                   |
| `graph`         | core image with AGE enabled, AGE Viewer       | Same PostgreSQL service; AGE projection remains disposable                              |
| `ui`            | Grafana and provisioned PostgreSQL datasource | Dashboards, pipeline progress, topic/entity/fact tables, node graph panels              |
| `observability` | Prometheus and its PostgreSQL exporter        | No corpus content in labels or metrics                                                  |
| `vllm`          | pinned `vllm/vllm-openai` image               | Optional all-device NVIDIA runtime; model cache bind mount; sequential with other GPU-heavy stages |
| `cadvisor`      | cAdvisor                                      | Privileged host-container metrics remain an explicit opt-in                             |

The operator alias `pipeline` expands to `core ui observability`. It is the default selection for
readiness and service commands. Inference uses the host Ollama service by default when it is running.
vLLM is an alternate only when the operator explicitly includes the `vllm` profile and selects the
`vllm` inference backend. `graph`, `vllm`, and the privileged `cadvisor` profile are not part of
`pipeline`.

Ollama generation defaults to `qwen3.8:27b`. An explicit `GENERATION_MODEL` overrides the selected
backend's default. The alternate vLLM service uses its own Hugging Face model and revision defaults;
an Ollama tag must not enter its Compose command. Selecting vLLM makes its defaults the active
generation model, with explicit generation overrides also applied to that service. Readiness checks
the selected backend's model availability; an absent model is degraded with the next operator action.
Choosing a default does not pull a model or assert evaluated model quality.

Ollama is deliberately not in Compose. It is installed and managed as the host system service. A
Linux container reaches it through a documented host-gateway alias only when a containerized worker
needs inference. The host CLI uses loopback directly. The default does not expose Ollama or
PostgreSQL beyond localhost.

Every service mount follows the storage classes above. Artifact-writing services run as the
operator's `RUNTIME_UID`:`RUNTIME_GID` so bind-mounted directories stay host-writable by the same
account that runs `make services-up`. The database service bind-mounts `PGDATA_DIR`
read-write and nothing else; when `PG_WAL_DIR` or a named tablespace root is configured, each is a
separate bind mount that the service refuses to start without. Grafana, Prometheus, and AGE Viewer
bind-mount only their own subdirectory of `SERVICE_STATE_DIR` read-write, with dashboard, datasource,
and scrape definitions provisioned read-only from `docker/`. Services that read pipeline output mount
`RESULTS_DIR` read-only; the vLLM profile mounts `MODEL_CACHE_DIR` and also runs as that operator
UID; the archive silos are mounted read-only or not at all. Compose receives absolute host paths
resolved by the same preflight the CLI uses, and a container whose mount fails its storage-class
check does not start.

The vLLM service exposes all NVIDIA devices on the CUDA host. Its evaluated model profile pins both
the model identity and repository revision, declares tensor parallelism, and bounds GPU utilization,
CPU offload, and context length. Containers without CUDA-capable work do not request GPU devices.

The Postgres derivative image must:

- pin the ParadeDB image digest and PostgreSQL major;
- compile or install a pinned AGE release for exactly that major;
- create extensions in deterministic order (`vector`, `pg_search`, then `age`);
- set required preload libraries without overwriting one another;
- run a build-time and runtime extension smoke suite;
- preserve all applicable AGPL-3.0, Apache-2.0, PostgreSQL, and dependency notices;
- document that ParadeDB Community lacks the enterprise HA/read-replica guarantees.

## Contract-first data governance

### Source of truth

ODCS `3.1.0` YAML under `src/arxiv_int/resources/contracts/` is the authoritative description of datasets, fields,
relationships, quality expectations, ownership, versions, and physical bindings. Avro is a generated
serialization schema and compatibility aid, not a competing source of truth.

The registry binds:

- a stable dataset/contract id and semantic version;
- ODCS source path;
- canonical entity or event role;
- generated artifact paths and fingerprints;
- PostgreSQL schema/table and partition policy;
- Parquet/Arrow and Avro names;
- search fields, tokenizers, filters, and vector dimensions;
- graph label/edge projection hints;
- migration/evolution baseline.

Project-specific generation hints live under namespaced `customProperties`, for example
`x-arxiv-int`, so contracts remain valid ODCS. A canonical model and controlled vocabulary define
`document`, `span`, `chunk`, `object`, `mention`, `alias`, `fact`, `topic`, `ontology_term`,
`extraction`, `source_occurrence`, `transaction`, `catalog_entry`, `anomaly_finding`, and
`evaluation_item` semantics. Source-specific mappings translate physical fields to
these concepts without changing pipeline code.

### Generation

Use Data Contract CLI for ODCS linting, Avro/JSON Schema export, changelogs, and breaking checks.
Generate SQLAlchemy Core `MetaData` from the existing typed ODCS registry for PostgreSQL tables,
types, keys, relationships, named constraints, and schema-qualified physical bindings. Reuse this
metadata for Alembic comparison and SQLAlchemy dialect compilation of review DDL; generic SQL
export is no longer a separate authoritative PostgreSQL model. Do not reverse-parse exported SQL
into the contract model or maintain handwritten ORM classes beside it. Keep project adapters
focused on mappings and engine features that generic tooling cannot express:

- PostgreSQL partition, constraint, index, and extension DDL;
- ParadeDB index/tokenizer definitions;
- pgvector dimensions and index candidates;
- AGE label/edge projection SQL;
- Arrow/Parquet descriptors with field metadata;
- Pydantic models or JSON Schema for structured LLM outputs;
- canonical semantic fingerprint and provenance fields.

Generated outputs are deterministic and committed when needed for review. `make contracts-check`
regenerates under `$DATA_DIR/contracts-check/<run-id>/` and fails on drift. The same normalized
contract fields generate Pandera schemas and dbt source/column/test YAML. Descriptions, units,
decimal precision/scale, time zones, nullability, keys, relationship targets, and rule identities
must survive generation; unsupported semantics are explicit failures, not silently dropped hints.
Handwritten domain transformations and semantic predicates reference contracts and rule ids.

[SQLAlchemy Core metadata](https://docs.sqlalchemy.org/en/20/core/metadata.html) supplies Python
schema objects without requiring an ORM. This is the selected schema representation.

### Evolution and migrations

Before the first database deployment or public release, the operator-authorized baseline is one
initial Alembic revision. Later deployed/released revisions are immutable and additive. Catalog
observations are run evidence under DATA_DIR; live checks derive expected definitions from
contracts and the authored migration, without a parallel committed catalog snapshot.

Compatibility classes follow a documented policy:

- identical physical schema or documentation-only change: patch or no version change;
- optional additive field or additive enum/semantic use: at least a minor version bump;
- removed/renamed field without alias, type narrowing, requiredness change, identity change,
  vector-dimension change, binding retarget, or semantic contraction: major version bump;
- search tokenizer/index schema change: migration plus measured reindex, even when row schema is
  compatible;
- graph projection change: projection version bump and rebuild; canonical facts remain unchanged.

Each reviewed version has a committed baseline containing physical fields, semantic metadata,
generator version, parsing fingerprint, and migration history. Avro reader/writer compatibility is
tested in both required directions. Alembic owns the revision graph, applied version state, and
upgrade/downgrade execution. Use immutable Python revisions under
`src/arxiv_int/migrations/versions/` with typed SQLAlchemy/Alembic operations and pinned contract
fingerprints. Historical revisions carry frozen definitions; they never import today's contracts
to decide what an old upgrade creates. Generated DDL never auto-migrates a store. Offline review
SQL from `arxiv-int db upgrade --sql` lands under `$DATA_DIR/migrations/<run-id>/` and is not
committed.

Autogeneration compares contract-derived metadata to an explicitly selected disposable database
and produces candidate Python operations for review. Restrict comparison to owned canonical
schemas/tables, retaining prior owned identities to detect removals. Exclude dbt relations,
extension internals, and other applications. Names, revision parents, checksums, one expected head,
types, defaults, precision, nullability, keys, checks, indexes, and partitions need explicit gates.
Renames, semantic changes, extension operations, and data backfills need reviewed handling;
autogeneration cannot infer their intent. Alembic documents these
[autogeneration limits](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).

Separate generate/check/status from apply. A missing runner or unavailable required live database
is `not-run`/failure, never a successful migration check. Verify empty-to-head and
previous-release-to-head upgrades against the pinned PostgreSQL image and compare live catalog
definitions, not SQL substrings. Reapplying head is a no-op; supported downgrades preserve their
declared data guarantees, while irreversible revisions refuse with a recovery path. Destructive or
table-rewriting changes still require the explicit approved plan, backup, free-space check, and
rollback/rebuild path. A comment marker alone does not supply that evidence. Large data backfills
are resumable transformation jobs with a separate activation step, not long schema transactions.

Only verified equivalent databases may be stamped at a baseline revision. Unknown, partial, or
drifted databases refuse adoption with a diagnostic and repair plan; do not blindly stamp, replay
CREATE statements over existing data, or rewrite applied history.

### Data transformations and quality

Operators need named, reviewable operations, reproducible lineage, and a clear reason when data
cannot be published. Use the following tools behind the existing stage interfaces; keep one
local pipeline scheduler and one canonical PostgreSQL service.

| Concern | Selected tool and ownership | Boundary |
| --- | --- | --- |
| Canonical schema and transactional access | SQLAlchemy Core + Alembic; psycopg for binary COPY | Python schema operations, bound queries/upserts, and migrations; no business transformation SQL strings in Python or shell |
| Relational transformations | Python dbt Core 1.x + `dbt-postgres` | Versioned SQL models and YAML descriptions/tests under `src/arxiv_int/resources/dbt/`; canonical inputs are dbt sources |
| Local tabular transformations | Polars expressions; PyArrow batches/Parquet IO | Typed functions in `src/arxiv_int/transformations/`; bounded partitions and measured memory; retain DuckDB where an existing library such as Splink needs it |
| Dataset quality | Pandera with its Polars backend + dbt data tests | Contract-derived batch validation and whole-relation checks; reuse existing domain/SHACL validators for semantic rules |

dbt organizes SQL into models with dependency references and tests; it does not eliminate SQL.
For this PostgreSQL design, Python processing runs in local Polars stages, without assuming dbt
Python-model support from the adapter. Select a compatible pinned Python dbt Core 1.x release and
PostgreSQL adapter; upstream `main` now documents a Rust 2.0 beta. See
[dbt Core](https://github.com/dbt-labs/dbt-core),
[PostgreSQL setup](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup), and
[Python model platform constraints](https://docs.getdbt.com/docs/build/python-models).

dbt owns derived staging/intermediate/mart relations in a dedicated `derived` schema. Alembic owns
canonical relations and the schema/role boundary, and never migrates dbt model tables. dbt reads
canonical sources and writes only derived relations. Ingestion, leases, reviews, COPY, and canonical
upserts remain typed Python/SQLAlchemy operations. BM25/vector index DDL and AGE/Cypher use narrow,
reviewed engine adapters where Python operations cannot express them. Keep unavoidable dialect SQL
in named versioned assets with bound values and safely composed identifiers; do not add a general
SQL templating framework or move transactional control into dbt hooks.

Models declare grain, stable keys, column descriptions, units, source/ref dependencies, inclusion
policy, and incremental/deletion semantics. Generated contract YAML owns shared field definitions;
model-specific descriptions/formulas and tests remain reviewed source assets. Build into an isolated
generation, run tests, then let the pipeline activate it atomically. dbt's model DAG is invoked by
the stage runner; it does not replace run/shard leases. Prevent concurrent writes to the same target.
Active derived generations and engine versions are immutable: rebuild under a new run id.
Activation requires current invocation evidence for selected relations and their required tests;
missing or stale evidence fails closed. Cleanup only drops eligible inactive projections, and
rechecks eligibility under the same database lock as publication.
Input removals, late corrections, review/identity changes, and formula changes must invalidate or
rebuild affected outputs. A blind append-only incremental model cannot satisfy reconciliation.

Use Pandera plus dbt tests as the default equivalent to Great Expectations for this local workflow.
This choice avoids a second suite/checkpoint configuration lifecycle; it is an architectural choice,
not a measured package-size claim. GX remains a future option only for an unmet validation need.
See [GX Core workflows](https://docs.greatexpectations.io/docs/core/introduction/),
[Pandera Polars validation](https://pandera.readthedocs.io/en/stable/polars.html), and
[dbt data tests](https://docs.getdbt.com/docs/build/data-tests).

Generate structural checks from ODCS: strict types, nullability, accepted values, keys, and declared
relationships. Keep monetary arithmetic decimal and units/currencies explicit. Run data checks on
bounded materialized batches: Pandera LazyFrame schema-only validation is insufficient. Cross-batch
uniqueness and relationships require whole-snapshot checks using dbt or bounded disk-backed
aggregation; batch-local passes cannot prove them. Polars streaming can fall back to memory for
some operations, so inspect execution plans and test memory bounds; see
[Polars streaming](https://docs.pola.rs/user-guide/concepts/streaming/).

Quality results carry rule id/version, contract/model/input fingerprints, scope, checked/failed
counts, severity, and bounded redacted failure references. Distinguish pass, fail, warning,
not-applicable, and not-run; define empty-data and minimum-sample outcomes. Missing required checks
and schema/evidence failures block activation. Quarantine row-level failures with evidence and
explicit coverage when policy permits; never silently coerce, discard, or publish invalid rows.
Data quality is separate from held-out extraction/retrieval/model-quality evaluation.

Keep tooling optional: migration dependencies in `store` (shared metadata dependency in
`contracts`), Polars in `lake`, and dedicated `transform`/`data-quality` feature groups for dbt and
Pandera. Each implementing task updates feature metadata, Python 3.12 compatibility, exact
output-sensitive pins, `uv.lock`, licences, and Make setup together. No network installs occur in
pipeline workers. `.env` credentials use the shared resolver and stay out of generated profiles,
logs, and manifests. Tool targets/logs/caches live under `$DATA_DIR/<method>/<run-id>/`; sanitized
dbt manifest/run-results and quality evidence needed for replay are retained in
`$RUNS_DIR/<run-id>/{manifests,quality}/` through the normal artifact publisher.

Acceptance requires deterministic contract generation, migration graph/drift regressions, declared
live upgrade/adoption tests, dbt parse/compile/build/test on synthetic PostgreSQL fixtures, and
Pandera positive/negative fixtures. Compare clean builds to repeated/incremental builds after
updates/deletions, enforce read/write ownership, verify failure prevents activation, and retain
redacted lineage. Missing tools/databases or unsupported contract semantics are valid negative
outcomes but keep the corresponding required implementation gate open. Fixture success does not
prove archive-scale memory, extraction accuracy, or production migration safety.

## Data model and stores

### Normalized data lake

`$RESULTS_DIR/normalized/` is organized by contract id/version and stable partitions, never by an
ephemeral checkout path:

```text
$RESULTS_DIR/
  normalized/
    inventory/contract_version=.../scan_id=.../*.parquet
    documents/contract_version=.../bucket=ab/*.parquet
    spans/contract_version=.../bucket=ab/*.parquet
    chunks/chunker_id=.../bucket=ab/*.parquet
    classifications/scheme_id=.../bucket=ab/*.parquet
    mentions/extractor_id=.../bucket=ab/*.parquet
    facts/extractor_id=.../bucket=ab/*.parquet
    embeddings/profile_id=.../bucket=ab/*.parquet
    domain-artifacts/type=.../artifact_id=.../
  quarantine/reason=.../
  runs/<run-id>/
```

Parquet is the default bulk format because it supports column pruning, partitioning, and DuckDB or
PyArrow out-of-core processing. Avro object container files are emitted where writer/reader schema
resolution or row transport is useful. Extracted large text can be stored as compressed Parquet
large strings or content-addressed compressed blobs referenced from rows; the pilot decides which
layout provides acceptable scan and repair behavior.

Dataset manifests bind every partition to an output generation. Incremental updates may reuse
unchanged content-addressed partitions, while replacements and from-scratch rebuilds are written to
generation-specific staging/published paths and activated only after validation. A path shown above
is therefore a logical dataset layout, not permission to overwrite a currently active partition.

### PostgreSQL schemas

| Schema     | Ownership and contents                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------------------- |
| `ctl`      | Contracts, migrations, runs, forecasts, shards, leases, checkpoints, errors, artifact lineage/registry |
| `corpus`   | Documents, editions, path events, spans, chunks, language, quality, duplicate and classification data   |
| `search`   | Search projection rows, embedding profiles, selected embeddings, topic assignments                      |
| `kg`       | Canonical objects, aliases, mentions, facts, qualifiers, review state, source evidence                  |
| `ontology` | Terms, classes, predicates, mappings, axioms, ontology versions                                         |
| `eval`     | Frozen gold items, query sets, labels, run metrics, paired comparisons                                  |
| `derived`  | Rebuildable dbt staging/intermediate/mart relations; never canonical rows                              |

Large tables are declaratively partitioned by a stable hash bucket and, where useful, corpus or
contract version. Partitions must be large enough to avoid catalog explosion. Text and vector
columns are kept out of narrow control tables. Bulk loads use binary `COPY` into staging/partitions,
validate contract-derived quality, counts and checksums, then attach or merge transactionally.

### Source and evidence identity

Distinguish a physical source occurrence `(silo_id, relative_path, scan_id)` from a content-hash
identity and an extracted document rendition `(content_hash, extractor_profile)`. Duplicate files
share analysis but retain every source occurrence. A ZIP/email attachment is a virtual member with
a container-content id and nested member path; it is never an independently movable source file.
Evidence anchors support page/character spans, table row/column and bounding boxes, spreadsheet
sheet/cell ranges, and container/member paths, with original-to-normalized coordinate mappings.

A complete scan records its source-set boundary and completion state. Permission failures,
unmounted silos, interrupted walks, or files changing while read are explicit unknown/unstable
outcomes, not removals. Only a complete comparable scan may tombstone a missing occurrence; ambiguous
renames remain linked add/remove occurrences until verified, without losing shared content evidence.

### Canonical object and fact model

An object has a stable internal id, type, preferred label, normalized attributes, lifecycle/review
state, resolution cluster, first/last evidence, and provenance. Aliases and mentions remain separate
so a merge can be reversed. Required types distinguish a legal entity/organization, natural person,
product/model, product revision, physical equipment instance, material, account, document, and
transaction/event. Supplier, buyer, manufacturer, employee, representative, and signatory are roles
in time-bounded relations, not mutually exclusive entity types. A brand is not automatically a legal
entity, a model is not a serial-numbered asset, and a shared name/address is not identity proof.
Identifiers retain scheme, jurisdiction/issuer where known, raw value, normalized value, and evidence.
Unknown legal form or jurisdiction stays unknown; the pipeline performs no external registry lookup.

Every mention receives an unresolved object anchor before fact extraction. Resolution proposes a
versioned mapping of those anchors to clusters; facts keep their original anchors and the applicable
identity snapshot. Merge/split decisions therefore rebuild affected views without rewriting evidence
or rerunning unrelated extraction. Temporal roles and explicit cross-document identifiers are used
for party linkage; same-name people and incompatible registration/part identifiers stay separable.

A fact is an assertion, not an unquestioned truth. It contains:

- subject object id;
- predicate id;
- object object id or one typed literal value;
- qualifiers and units;
- valid-time interval when the source asserts one;
- transaction/extraction time;
- source document, page/byte/character span, and chunk;
- extractor/model/prompt/schema/code versions;
- confidence and calibration profile;
- status: `proposed`, `accepted`, `rejected`, `superseded`, or `conflicted`;
- contradiction/duplicate group and reviewer provenance.

Database constraints enforce the object-versus-literal shape. No LLM response enters `accepted`
state merely because it parsed. Company, product, and person catalogs and equipment/supplier lists
are queries over typed objects
and accepted or explicitly included proposed facts, with citations and confidence visible. Derived
calculations retain the input fact ids, formula/rule version, and operands; their evidence is a
derivation chain, not a fabricated source sentence.

### Geotemporal assertions

Location and time qualify source assertions and evidenced roles; they are not identity proof.
Reuse `Location`, fact qualifiers, source anchors and domain contracts. Keep geographic coordinates
separate from page bounding boxes and spreadsheet coordinates. Preserve the asserted address/place,
coordinate reference system, axis order, units, precision and uncertainty when supplied. Validate
coordinate ranges for the declared system; missing CRS, ambiguous place names or absent coordinates
remain unknown. Do not infer a person's residence from a company address or geocode through an
external service. Bounded place/time filters and SQL/graph parity are in scope; a GIS platform,
map service, routing engine and new spatial database extension are not required.

Keep source-valid time distinct from extraction/transaction time and document publication time.
Retain source timezone, granularity, open bounds and uncertainty; normalize known instants to UTC
without inventing a timezone or a precise instant for a date/year-only assertion. Declare interval
endpoint conventions in the contract. Inverted intervals fail validation; missing/ambiguous time
remains explicit. Role, location and product-revision/effectivity joins use compatible asserted
intervals. As-of queries identify both the valid-time scope and the recorded identity/ontology
snapshot; a later correction must not silently rewrite an earlier result.

Evaluate open/closed bounds, timezone-equivalent instants, partial dates, unknown CRS, reversed axes,
invalid coordinates, shared addresses with distinct entities, role/location changes, contradictory
sources and revision/effectivity boundaries. SQL, graph and report filters must agree on the same
pinned interpretation. These requirements belong to ontology/identity contracts, fact validation
and domain views; they do not add a separate capability.

### Ontology design

Pinned Turtle/SHACL assets under `src/arxiv_int/resources/ontology/` are the formal vocabulary. AGE, catalogs, and reports
project that vocabulary; they do not invent parallel class systems. Ontology evolution stays
additive under the existing contract/ontology evolution policy: a new meaning is a new term or
shape, and rewriting an active IRI in place is breaking.

Model the vocabulary with four design rules:

1. **Domain-driven design.** Classes and predicates are semantically meaningful investigation
   concepts (legal entity, natural person, product, equipment, `part-of`, `pays`, evidenced roles).
   Helper and non-semantic objects stay hidden: lease rows, run ids, Parquet partitions, JSON
   bindings, SHACL blank nodes, AGE projection bookkeeping, and `ctl.*` control records are not
   ontology classes and must not appear as catalog entities or analyst graph labels. Supplier,
   buyer, manufacturer, employee, representative, and signatory remain roles in time-bounded
   relations, not competing entity types.
2. **Don't repeat yourself, using the rule of three.** Reuse an existing term for the same
   relation. Do not mint a parallel predicate or class for one already mapped to
   `fact.predicateId`. Add a new term when the same semantic distinction is independently
   evidenced three times, or when this specification already requires the type. Do not collapse
   distinct domain concepts (person versus organization, model versus serialized equipment) to
   share storage.
3. **Open for extension, closed for modification.** Extend with additive classes, predicates, and
   SHACL shapes. Existing IRIs keep their meaning so current facts, mappings, and consumers keep
   working. Required investigation types may be added; changing domain, range, or disjointness of
   an active term follows breaking-evolution review, not an in-place edit.
4. **Producer extends, consumer super (covariance and contravariance).** Query, catalog, and graph
   export producers may yield a requested class or a subclass: a query for organization may include
   more specific legal-entity types. Assertion consumers (stores, SHACL, application validators)
   accept the declared domain/range; a more general consumer may handle a more specific produced
   instance. Extractors must not write a type into a slot whose domain/range is disjoint from it.
   A valid negative is refusing the assertion or leaving it `proposed`/`conflicted` with the
   violating types recorded.

Evaluation: fixture graphs and generated bindings contain only published domain classes on
analyst-facing labels; helper types are absent from catalogs. Duplicate equivalent predicates
without a mapping fail ontology-check. In-place meaning changes of an active IRI fail evolution
policy. Domain/range fixtures prove subclass production and superclass consumption, and prove
disjoint-type writes are rejected. Human ontology review may keep a draft term unpublished.

Dynamic ontology means explicit versioned evolution, not automatic acceptance of generated axioms.
The `ontology` stage seals an immutable snapshot of published terms, mappings, shapes and policy
fingerprints for each run. Candidate terms/aliases/shapes remain a separate draft review artifact;
unknown terms remain unmapped/proposed. Only the existing human ontology-policy gate can accept new
semantics. Reuse published terms, retain stable IRIs, and record deprecation/replacement mappings;
no run edits the vocabulary it already pinned. A changed term/shape invalidates the affected
validation, graph, catalog and report lineage; old snapshots and review decisions remain replayable.

Evaluate additive extension with unchanged old results, rejected in-place meaning changes,
draft-versus-published visibility, removed/disjoint types, subclass-compatible consumers and stale
snapshot refusal. Domain boundaries stay explicit: party/account/transaction, model/revision/physical
instance, and component/assembly relations reuse the canonical meanings. Shared names, proximity,
co-occurrence, similar amounts and overlapping dates cannot manufacture a merge, `part-of`, supply,
or settlement assertion. Bounded domain fixtures prove both valid relations and those non-implications.

### Search and vector projections

The ParadeDB covering index includes only columns required for retrieval, filtering, snippets,
facets, and top-k. Russian text uses Unicode or ICU tokenization plus lowercase, Russian stemming,
and Russian stopwords as an evaluated baseline. A second exact/literal field supports identifiers,
part numbers, and model names. Tokenizer changes imply reindexing.

Embeddings are tiered:

1. Tier 0: no embedding; every searchable chunk has BM25.
2. Tier 1: representative samples, high-value document classes, unique chunks, and topic centroids.
3. Tier 2: chunks selected by query logs, uncertainty, entity/fact density, or evaluation misses.
4. Tier 3: an explicit operator-requested corpus slice.

Every embedding records model revision, pooling, normalization, dimensions, chunker, input hash, and
inference backend. Changing any identity creates a new profile; vectors from incompatible profiles
are never mixed.

### AGE graph projection

AGE vertices and edges carry canonical ids and compact display/query properties. Full evidence and
large text stay in relational tables. Projection state records canonical fact version, graph schema
version, and last committed id. Rebuilding creates a versioned graph, validates counts and sampled
paths, then switches the active graph pointer. Recursive SQL remains the correctness reference for
bounded traversals.

Ontology assets are also exported in open RDF formats such as Turtle, with SHACL shapes for
validation. AGE is a property-graph query projection; it is not the formal ontology serialization.
Analyst-facing vertex/edge labels follow [Ontology design](#ontology-design).

## Pipeline

Every stage can run independently after its declared dependencies or through the end-to-end
orchestrator.

| Stage          | Main work                                                                   | Primary output                |
| -------------- | --------------------------------------------------------------------------- | ----------------------------- |
| `preflight`    | Paths, devices, space, tools, services, contracts, model endpoints          | Readiness report              |
| `inventory`    | Walk declared silos, stat, MIME, encoding, hashes, archive-member policy    | Inventory Parquet             |
| `extract`      | Tika baseline; Docling/OCR/layout fallback; source coordinates              | Extracted documents/spans     |
| `normalize`    | UTF-8, Unicode normalization, boilerplate policy, language, metadata        | Canonical document records    |
| `dedupe`       | Exact, normalized, lexical/MinHash, edition groups; no destructive deletion | Duplicate overlays            |
| `chunk`        | Structure/table/sentence-aware chunks with overlap and source spans         | Chunk Parquet                 |
| `classify`     | UDC-derived multi-label assignment, primary class, exceptional outcomes    | File-classification map       |
| `load-lexical` | PostgreSQL bulk load and ParadeDB index build/refresh                       | Lexical search projection     |
| `nlp`          | Russian morphology, NER, terminology, mention candidates                    | Mentions and term statistics  |
| `embed`        | Selective embeddings and optional reranker candidates                       | Versioned embedding artifacts |
| `load-vector`  | pgvector baseline and experimental ParadeDB vector projection               | Semantic search projection    |
| `topics`       | Sample/incremental clustering, labels, drift and hierarchy                  | Topics and assignments        |
| `entities`     | Blocking, probabilistic linkage, aliases, reversible clusters               | Canonical objects             |
| `facts`        | Rule/model/LLM structured extraction, validation, conflicts                 | Proposed facts with evidence  |
| `ontology`     | Load and validate pinned vocabulary, mappings, and SHACL assets | Versioned ontology configuration |
| `validate-facts` | Type, evidence, temporal, unit, conflict and review-policy validation | Validated fact views and findings |
| `graph`        | Build and validate AGE projection                                           | Active versioned graph        |
| `domain-artifacts` | Relationship, BOM, supply-chain, and invoice/payment projections        | Registered investigation artifacts |
| `catalogs`     | Company, product, and person lists with identity/role/evidence coverage | Versioned catalog tables |
| `anomalies`    | Explainable data, transaction, graph, and product consistency signals | Finding tables and subgraphs |
| `evaluate`     | Retrieval, extraction, linkage, graph, cost, and resource metrics           | Immutable evaluation bundle   |
| `report`       | Coverage, failures, topics, objects, facts, registered domain artifacts     | HTML/JSON/Parquet reports     |

The end-to-end command runs the dependency closure, not a hardcoded shell chain. Table order is an
orientation; the [stage dependency contract](architecture.md#stage-dependency-contract) is the DAG.
Classification, lexical indexing, and topics branch from corpus artifacts; entity anchors and
ontology schemas precede fact extraction. Domain artifacts and anomaly calculations depend on
canonical facts and identity snapshots, not on AGE availability.

### End-to-end run and output contract

After `make setup` succeeds, `make pipeline` runs end-to-end from the resolved `.env` settings.
Its direct CLI equivalent is `arxiv-int pipeline run`, with no required path or profile arguments.
`PIPELINE_PROFILE` defaults to `investigation`; explicit CLI/Make or process-environment overrides
retain the normal precedence. It takes a directory tree of files; compressed containers are
members of that tree, not a required input packaging format. The resolved archive roots, source
selection, model/policy pins, enabled families, and resource bounds are frozen before work. A bounded
`--profile lexical` run is an explicit partial product path, never labelled a complete investigation.
The profile files live under `configs/pipeline/` and share one registered stage implementation.

The investigation profile accounts for every physical input, normalizes supported content, builds
lexical search, classifies files, derives topics/mentions/facts/identities, produces all required
catalog and domain-family entries, evaluates coverage, calculates anomalies, and publishes one
knowledge-base generation. CPU rules and unresolved/proposed states allow useful output while a
local model is unavailable; requested model work that cannot run is reported as partial or blocked.
Vector search, generative answers, AGE, viewers, and archive placement are not prerequisites.

Each completed generation publishes `$RUNS_DIR/<run-id>/knowledge-base.json` containing source and
contract fingerprints, active canonical/projection snapshots, every output's schema/path/checksum,
coverage denominators, limitations, policy states, and a report entry path. Required outputs are:

| Output | Analyst purpose |
| --- | --- |
| Inventory and document index | Account for each file, extraction status, content overview, and source location |
| Topic and classification maps | Browse contents by discovered subjects and a versioned filing hierarchy |
| Company, product, person catalogs | Inspect distinct identities, aliases, identifiers, roles, unresolved links, and citations |
| Facts and relationship graph exports | Follow typed, directed, time-qualified claims to documents/cells/pages |
| BOM, supply-chain, invoice/payment families | Inspect supported domain views, arithmetic, uncertainty, and evidence gaps |
| Anomaly finding register | Triage explainable candidates and their comparison baselines |
| `reports/index.html` plus report JSON | Start with coverage, important supported findings, and bounded drill-down links |

A run records `succeeded`, `partial`, `failed`, `blocked`, or `interrupted`, separately from artifact
states `produced`, `partial`, `empty`, `failed`, and `not-selected`. Empty is valid only when the
eligible inputs were processed and no qualifying evidence exists. An unsupported/failed requested
lane cannot masquerade as empty. No anomaly finding does not certify the archive as anomaly-free.
Optional not-selected branches state why and identify the working baseline; they need not run a
benchmark just to remain disabled. Promotion claims still require comparative evaluation.

Pipeline exit codes are `0` for a validated complete requested profile (including valid empty
families), `2` for partial results, `1` for failure, `3` for precondition/resource refusal, and `130`
for interrupted work. A partial run writes a diagnostic entry report but cannot silently replace the
last complete knowledge-base pointer. Evidence validation runs without gold labels; quality claims
require the separate reviewed final evaluation. Completion requires an actual single-command
archive-to-report run, source-link verification, and a no-change cache-hit rerun, not only a union
of independently produced stage proofs.

## Hierarchical archive classification and optional reorganization

Operators need a navigable subject view of source silos without losing ambiguous material or the
path from a derived claim back to its original file. The `classify` stage assigns every inventoried
physical file a versioned result from a hierarchy derived from Universal Decimal Classification
(UDC). It is multi-label because UDC can express several subjects and facets, while one declared
primary simple class and its ancestors determine a possible physical filing path. Compound UDC
expressions, auxiliary facets, alternate candidates, captions, scores, evidence, classifier
identity, vocabulary version, and review state remain in the mapping artifact rather than being
encoded completely into directory names.

The vocabulary source is explicit and checksummed. The CC BY-SA UDC Summary is the distributable
baseline; an operator may configure a licensed MRF or authorized service snapshot for deeper
coverage. Locally required subdivisions use a separate project namespace and parent link and never
masquerade as official UDC codes. Two project outcomes are mandatory and are not UDC notations:

- `unclassified`: usable content exists, but no supported class clears the acceptance threshold or
  the material is random/non-substantive;
- `unreadable`: no usable content could be obtained because the input is inaccessible, encrypted,
  corrupt, unsupported, or an unknown/binary format for which extraction failed.

Every file-classification row contains the stable inventory id, content/document id when readable,
silo id and original root-relative path, primary and alternate class ids, ancestor chain, confidence
and calibration profile, decisive source spans or failure reason,
extraction/classifier/configuration fingerprints, and run id.
Low-confidence cases remain `unclassified`; unreadability is determined from recorded inventory and
extraction outcomes, not guessed from filename extensions. A valid negative result is a complete
mapping with a high exceptional-outcome rate and a recommendation to improve extraction or labels;
the pipeline must not force ordinary UDC assignments to improve coverage.

### Separate archive organization utility

`archive-organization` owns physical placement; `archive-classification` owns only the classification
map. The organizer must work from a sealed classification export and source manifest without model
inference, reclassification, or live search/graph services. It writes a portable path-event ledger;
`archive locate` and subsequent pipeline updates can import that ledger idempotently. Ordinary
pipeline proofs and full-corpus authorization never depend on applying a placement.

`arxiv-int archive reorganize` is a separate maintenance command, not an ordinary pipeline stage.
It consumes one accepted, complete classification artifact and produces a deterministic plan for
exactly one declared silo. Dry-run is the default; `--apply --plan PLAN_ID` requires explicit
operator authorization and revalidation of every source path, available content hash, destination,
free-space/device condition, and classification fingerprint. Entries lacking the permissions or
strong hash needed for a safe placement remain explicitly blocked. The normal pipeline and all
containers continue to mount the archive read-only.

The plan declares one of two placement modes, and the mode is part of the authorized decision:

| Mode                            | Effect                                                                              | Cost and risk                                                                            |
| ------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `copy` to `--target DIR`        | Builds the classified tree in a separate target root and leaves the silo untouched  | Needs free space for the selected subset; the source archive is never modified, so the target can be deleted and rebuilt at any time |
| `move` in place                 | Renames files inside the silo root into their class directories                     | Reclaims no extra space but rewrites the operator's own tree, so it requires a writable archive and a verified backup |

`copy` is the default and the recommended first organization: it turns an accepted classification
into a browsable subject tree without ever putting the original files at risk, and it may target a
different device. The target may be on the same or a different filesystem. Copies have independent contents;
hardlinks are excluded because later target edits would also alter the source. `move` exists for
operators who want the archive itself reorganized and accept
that cost; it stays same-filesystem and atomic, and it is refused without a verified backup. Both
modes read the same classification mapping, write the same ledger, and support the same resume,
verification, and lookup behavior.

Physical directories follow the primary class's ancestor path. Each segment combines a reversible
safe class token with a short meaningful ASCII slug, is capped at a configured byte length, and is
checked together with the full destination against filesystem component and path limits. Dedicated
ASCII directories such as `_unclassified` and `_unreadable` hold exceptional outcomes that can be
safely placed. Complex facets and secondary classes stay in metadata. Filenames are preserved where
safe, with deterministic content/occurrence suffixes for duplicate
basenames and normalized-name collisions; the exact policy enters the reviewed plan. Directory
slugs never derive from unvalidated model text. A plan excludes concurrent pipeline scans and other
placement writers for its silo; apply rechecks filesystem identity and source hashes at each action.
The command never overwrites a
destination, never follows a link outside the selected root, never relocates virtual members
independently of their container, and refuses stale, colliding, overlong, or incompletely accounted
plans. A `move` plan additionally refuses cross-device entries; a `copy` plan accepts either device
placement and refuses a target that overlaps the silo, results, or database root.

Before the first placement, the command seals an append-only ledger containing inventory and
document/content ids, silo id, mode, original and proposed destination relative paths, action order,
available hashes, classification and plan ids, placed/blocked status, and rollback information. It
journals each atomic rename or verified copy and can resume or reverse only operations proven by that
ledger. A copied file is verified against its recorded hash before the entry is marked complete, and
reversing a `copy` plan removes only target files the ledger proves this plan created and whose
current hash still matches. Changed or newly occupied paths require conflict resolution; rollback
never deletes later user edits. Durability requires flushing the journal and directory metadata
around each operation; atomic per-file renames do not make the entire multi-file move atomic. Original
provenance is never rewritten to contain only the new path, and in `copy` mode the original location
remains the source of record while the target path is recorded as an additional location. The
`arxiv-int archive locate DOCUMENT_ID` command is a shared read-only source resolver available
with the pipeline before the placement utility. It resolves the initial, run-time, and current known
locations through path events, so later knowledge artifacts continue to find their sources.

Evaluation uses a frozen, stratified file set with expert primary/alternate labels and expected
unclassified/unreadable outcomes. It reports exact and ancestor-aware precision/recall, hierarchical
distance, calibration/selective coverage, exceptional-outcome confusion, reproducibility, and cost.
Placement fixtures prove byte-identical contents in both modes, one-to-one path accounting,
collision refusal, interruption/resume, rollback, and source lookup. No real archive placement is
accepted without review of the mapping, thresholds, directory vocabulary, dry-run diff, target space,
and, for `move`, backup/recovery readiness.

## Russian-language and document analysis

The pipeline must handle UTF-8, Windows-1251, KOI8-R, mixed encodings, OCR noise, Cyrillic/Latin
homoglyphs, e/yo variants, abbreviations, inflection, transliterated names, and mixed
Russian/Ukrainian/
English technical text without silently rewriting source evidence.

Recommended lanes:

- extraction: Apache Tika for breadth; Docling for layout/tables; OCRmyPDF/Tesseract or a separately
  evaluated local OCR model for scanned PDFs;
- language and morphology: fastText/CLD-style language identification plus Natasha/Slovnet, Stanza,
  or spaCy-compatible Russian models; pymorphy-based normalization where licensed and empirically
  useful;
- open NER: Natasha/Slovnet baseline; multilingual GLiNER or an evaluated alternative for custom
  types such as equipment, model, supplier, material, organization, location, standard, and date;
- retrieval: ParadeDB Unicode/ICU tokenizer, Russian stemmer and stopwords, identifier literal
  field, abbreviation/alias dictionary, typo and keyboard-layout query probes;
- embeddings: compare BGE-M3, multilingual E5, and other locally runnable candidates on actual
  Russian queries; do not select from English leaderboard scores alone;
- topics: CPU-first TF-IDF/NMF or MiniBatchKMeans baseline over sampled/centroided data, then a
  BERTopic-style embedding/HDBSCAN lane only for bounded subsets;
- facts: deterministic patterns and dictionaries first, local LLM structured output second, and
  human review for high-impact types or ontology changes.

Both original and normalized text offsets are retained or mapped. Search and reports show original
source snippets, not morphology-normalized reconstructions.

## Local inference

One provider-neutral client supports Ollama and vLLM through local HTTP APIs.

Ollama is the default because it is easiest to install as a system service, supports embeddings and
JSON-schema output, and can unload/keep alive models. The project provides `make ollama-check`,
`make models-list`, and `make models-pull` wrappers but does not install or mutate the system
service without an explicit operator action.

vLLM is an optional Compose profile for higher-throughput supported models. Its image, model
revision, CUDA compatibility, maximum model length, quantization, and GPU memory utilization are
pinned in an evaluated profile. Before promotion, prove model loading and representative maximum
context/batch work on one CUDA device, including weights, runtime overhead, KV cache, activations,
and simultaneous CPU/database memory. A parameter-count or quantization estimate alone is not a
fit test. A smaller/quantized profile or CPU/offload lane may be selected with recorded quality/cost;
no implicit second GPU, remote endpoint, or model download is allowed. GPU-heavy embedding,
reranking, extraction, and generation stages
run sequentially by default on 16 GB VRAM. The scheduler checks free VRAM, unloads an Ollama model
when policy permits, and records load time, throughput, peak VRAM, failures, and fallback use.

LLM outputs use generated JSON Schema/Pydantic validation, temperature near zero where supported,
bounded repair, explicit refusal/malformed statuses, and source-evidence requirements. Prompt text,
model id/digest, sampling settings, and output schema version are part of provenance.

## CLI and Make interface

### Retryable setup and default pipeline command

The normal operator workflow from a checkout uses one setup target, with edits/retries as needed,
followed by one pipeline command:

```text
make setup
# Edit .env when requested, then rerun make setup until the selected infrastructure is ready.
make pipeline
```

The operator edits `.env`; `.venv` is the generated Python environment and is managed by setup.
Git/Make/Bash, uv, Python 3.12+, Docker/Compose and the selected host inference/GPU prerequisites
must be installed with the host's normal tools. Setup diagnoses missing tools, permissions, mounts,
drivers and host services with exact next actions; it does not install privileged OS packages,
change Docker groups, manage systemd, or rewrite host storage configuration.

`make setup` creates `.env` from the template when absent and preserves all existing values and
commented declarations on later attempts. It reports missing/invalid operator roots and secrets
before product-root writes, downloads or service startup. Setup does not launch an editor. No
activated virtual environment, manual exports, direct uv invocation or command chain is required.
Every invocation rereads the
file through the existing resolver; explicit environment overrides remain visible as override
sources and retain precedence, with secret values masked.

After configuration is valid, the setup coordinator performs these ordered phases through shared
atomic command handlers: check host prerequisites; sync one locked union of selected feature
dependencies into `.venv`; verify package identity; prepare validated paths; obtain required pinned
images and configured model assets; start selected services; wait within bounded deadlines;
check/apply eligible reviewed Alembic revisions; validate contract/tool/model/service readiness.
A stopped host Ollama
service requires an operator action; a selected vLLM container is managed through Compose. Model
acquisition uses the configured backend's storage and never silently chooses another model.
Downloads are setup operations; `SETUP_DOWNLOADS=0` requires locally cached assets and refuses
missing ones. Default `SETUP_DOWNLOADS=1` permits configured package/image/model acquisition during
setup. Pipeline workers never install dependencies, pull models, or start infrastructure.

Each phase remains independently callable through Make/CLI. The coordinator supplies resolved
configuration and attempt context to the same typed handlers used by those commands; it does not
copy shell recipes, SQL or model/service operations. The ordered command chain and the availability
of each command belong in the linked [operator workflow](../guide/operator-workflow.md).
The setup owner provides the missing configuration, environment, image/model acquisition, bounded
wait and schema-binding commands around existing dotenv, feature, Compose, store and inference
adapters. Package/contract/ontology checks use their existing handlers with the prepared dependency
union; nested commands must not remove selected extras or repeat online dependency sync in offline
mode. Bootstrap remains a contributor workflow, not a pre-start readiness barrier for setup.

Schema preparation explicitly binds to the selected service's database and credentials from the
shared runtime configuration, verifies target identity, and uses the existing store apply/inspect
and Alembic policy. Pass credentials privately through the adapter; never print a URL or interpolate
passwords into shell commands. A conflicting explicit migration target is refused with a redacted
next action. The store smoke command's disposable-database fallback is disabled in setup. An empty
database can receive the reviewed initial revisions. A nonempty unversioned, unknown or drifted
catalog requires a separate reviewed repair/adoption action; setup never auto-adopts it, invents a
revision, or substitutes scratch-database success for service health.

Setup and pipeline use one declarative profile requirement source: required/optional stage features,
services, model identities, contract revisions and availability. The setup coordinator consumes
those declarations without importing heavy workers or implementing a second stage DAG. Providers
join the shared feature/service policy as their capabilities ship. Missing mandatory providers or
reserved, unimplemented stages must be named as unavailable; successful installation alone cannot
be labelled ready to run the pipeline. Infrastructure health and pipeline implementation availability
are separate report fields.

`PIPELINE_PROFILE=investigation` selects the default run. `SERVICE_PROFILES=pipeline` retains the
existing core/UI/observability alias as the service default; required services for the selected run
and inference backend are added by the shared selector, including vLLM when selected. Explicit
optional graph/vector branches remain opt-ins. Make and CLI must not pass hardcoded default
arguments that shadow `.env`. These variables and `SETUP_DOWNLOADS` enter `.env.example` and the
shared typed configuration schema in the owning implementation tasks.

Retries reconcile actual state using lock/config/profile/image/model/revision fingerprints. Reuse
verified installed packages and cached assets, preserve operator data and healthy services, retry
only missing/failed work, and recheck readiness even when all previous phases passed. A failure
stops dependent phases and reports phase, status, next action and the same `make setup` retry command.
Bound waits/download operations, support cancellation, and serialize concurrent setup against the
same environment/service/database targets. Never reset data, rotate secrets, blindly stamp a
database, or replay a successful migration to repair readiness. Destructive or rewriting migrations
retain their separate approval/recovery gate; eligible additive migrations use the existing Alembic
policy. Before safe product roots exist, diagnostics stay on the console; after validation, retain
the redacted setup report at `$RESULTS_DIR/reports/setup.json` alongside readiness. Tool logs belong
under `$DATA_DIR/setup/<attempt-id>/`. Ready returns success; blocked/degraded/interrupted outcomes
remain explicit, and an unimplemented required check cannot count as ready.

`make pipeline` loads `.env` itself, invokes the installed CLI, and runs preflight plus a fresh,
fingerprinted resource forecast before expensive work. It then executes the selected dependency
closure through validation, evaluation and report publication. A separate forecast, stage loop,
manual validation or `report build` is optional diagnosis, not part of the normal run procedure.
Existing resource limits, source scope and human authorization requirements still apply. Missing
setup or required implementations refuses execution with an actionable result; partial work never
claims success. The command reports the run id, final logical status, knowledge-base manifest and
report entry paths, plus exact status/resume commands after interruption. CLI exit codes follow the
run contract; Make returns nonzero on failure and displays the logical result without claiming to
preserve every distinct CLI exit code. Repeated unchanged runs reuse validated artifacts.

The aggregate pipeline command composes the same run-create, preflight, forecast, registered stage
and run-finalize handlers exposed by the atomic interfaces. Creation assigns a unique run id and
freezes the resolved profile/configuration; each subsequent atomic command uses that run id and
validates its recorded inputs. Retain only secret-free configuration evidence and fingerprints;
resolve credentials privately at execution. A changed configuration requires a new run or explicit invalidation,
not silent cross-command drift. Finalization verifies required quality/artifact states and commits
the coherent generation pointer; building a report alone cannot activate a generation. Standalone
processing stages still enforce preflight, forecast freshness, dependencies and leases. The explicit
chain and aggregate run must produce equivalent logical artifacts, lineage, quality outcomes and
completion states, allowing different run ids/timestamps. Both stop on failure and retain resumable evidence.

Evaluation covers no `.env`/no `.venv`, edit-and-retry without shell exports, precedence, dependency
sync failure, cached/offline runs, missing host services, slow startup, model failure, schema drift,
concurrency and cancellation. Fixture tests compare Make and CLI defaults, aggregate/atomic phase
traces, and run-generation results; they prove unsafe or incomplete setup cannot launch workers and
that schema readiness checks the intended service. A declared disposable host smoke verifies setup,
followed by the existing mixed-fixture and authorized archive proofs using bare `make pipeline`.
Until those owners pass, README labels these targets planned and links the available manual path.

### Command reference

The installed command is `arxiv-int`. Representative commands are:

```text
arxiv-int readiness
arxiv-int setup
arxiv-int features [--stage STAGE]
arxiv-int config show --redact
arxiv-int contracts lint|generate|diff|check|test
arxiv-int db revision|check|status|upgrade|downgrade
arxiv-int transform parse|build|test --run-id RUN_ID
arxiv-int data-quality check DATASET --run-id RUN_ID
arxiv-int services status
arxiv-int pipeline forecast --archive-dir PATH [--from STAGE] [--to STAGE]
arxiv-int pipeline forecast --run-id RUN_ID
arxiv-int pipeline run [--archive-dir PATH] [--results-dir PATH] [--profile investigation|lexical]
                       [--from STAGE] [--to STAGE]
arxiv-int pipeline update --archive-dir PATH [--from STAGE] [--to STAGE]
arxiv-int pipeline rebuild --archive-dir PATH [--from STAGE] [--to STAGE]
arxiv-int pipeline invalidate STAGE [--document-id ID]
arxiv-int stage STAGE --archive-dir PATH --results-dir PATH [stage options]
arxiv-int stage STAGE --run-id RUN_ID [stage options]
arxiv-int run create
arxiv-int run finalize RUN_ID
arxiv-int artifacts prune --stale [--apply --plan PLAN_ID]
arxiv-int archive reorganize --classification PATH --silo ID --mode copy --target PATH
arxiv-int archive reorganize --classification PATH --silo ID --mode move
arxiv-int archive reorganize --apply --plan PATH
arxiv-int archive reorganize --resume PLAN_ID
arxiv-int archive reorganize --rollback PLAN_ID
arxiv-int archive locate DOCUMENT_ID
arxiv-int inspect DATASET|RUN|latest [--limit N]
arxiv-int run status RUN_ID
arxiv-int run resume RUN_ID
arxiv-int run artifacts RUN_ID
arxiv-int search lexical|semantic|hybrid QUERY
arxiv-int graph rebuild|check|query
arxiv-int catalog company|product|person [--run RUN_ID]
arxiv-int anomalies list|show [--run RUN_ID]
arxiv-int report build RUN_ID
```

Standard Make targets are thin, documented wrappers:

```text
make help                  make setup                 make pipeline
make setup-config          make setup-env             make setup-wait
make services-pull         make models-pull           make setup-schema
make bootstrap             make package-check
make readiness             make config                make contracts
make contracts-gen         make contracts-evolution  make services-up
make db-check              make db-status            make db-revision MESSAGE=...
make db-upgrade REVISION=...                          make db-downgrade REVISION=...
make transform-build RUN_ID=...                      make data-quality DATASET=... RUN_ID=...
make services-down         make services-reset       make services-status
make logs
make run-create            make forecast RUN_ID=...   make run-finalize RUN_ID=...
make inspect RUN_ID=...    make archive-locate DOCUMENT_ID=...    make update
make proof CAPABILITY=...  make stage STAGE=...       make resume RUN_ID=...
make search QUERY=...      make graph-up              make ui-up
make eval                  make test                  make integration-test
make ci                    make backup                make restore-check
```

The default workflow needs no path flags or exported shell variables. Explicit path overrides work
in both forms:

```bash
make pipeline ARCHIVE_DIR=/mnt/archive RESULTS_DIR=/mnt/results

arxiv-int pipeline run \
  --archive-dir /mnt/archive \
  --results-dir /mnt/results
```

Command-line values override `.env`; resolved non-secret values and path device ids are written into
the run manifest. Make never embeds machine-specific absolute paths.

These are target commands; available commands are listed in current-state documentation.

Every stage becomes available through the standard `arxiv-int stage STAGE` and
`make stage STAGE=...` interfaces in the same task that implements it. The implementation task runs
that command against a bounded authorized archive when available and inspects its normal artifacts;
there are no development-only path aliases, stage wrappers, or output trees. The complete
`make pipeline` command uses the same registered stage implementations and artifacts.

Deterministic CI remains fixture-based and never reads the configured archive. A real-data run is an
implementation feedback signal, not acceptance evidence: it does not replace the capability's
evaluation or proof bundle, and no corpus content or machine-specific path enters Git.
Missing private access or reviewed labels keeps the proof/human task open, rather than blocking deterministic
implementation and fixture checks. A fixture pass never claims real-corpus acceptance.

## Resumability, idempotency, and provenance

A run id identifies an immutable requested configuration and one output generation. Each stage is
divided into stable shards derived from content hashes or partition buckets. `ctl.run`,
`ctl.stage_run`, `ctl.shard_run`, and the artifact lineage graph record states such as `pending`,
`running`, `succeeded`, `failed`, `quarantined`, `superseded`, `stale`, and `pruned`.

A shard identity includes:

- ordered input artifact hashes and upstream manifest ids;
- contract, schema, stage-owned code, dependency, tool, model, prompt, and configuration
  fingerprints;
- stage name/version and deterministic parameters;
- output manifest and row/file checksums.

Before scheduling work, the planner resolves every requested output to its complete transitive input
fingerprint. A successful shard from any compatible run is a cache hit only when that fingerprint
matches, it is not stale or pruned, and its manifest, files, row counts, and checksums still validate.
Cache hits are recorded without loading the heavy model or executing the stage. Concurrent requests
for one reuse key share a lease rather than duplicating work. Failed or expired leases are resumable.
Outputs are written to temporary sibling paths, validated, then atomically renamed; database loads
use staging tables and transactions.
Retries are bounded and classify permanent versus transient failures. `--force` creates a new
attempt but does not overwrite accepted evidence.

`pipeline update` inventories the current archive against the last selected source manifest and
creates an explicit delta of added, content-changed, path-only-renamed, and removed files. New or
changed content invalidates only its owning shards and their downstream lineage closure. A path-only
rename updates path events without repeating content analysis. A complete scan can tombstone
removed source occurrences; unavailable/partial scans cannot.
Content is inactive only after its last active occurrence is removed;
active normalized datasets, indexes, entity/fact evidence sets, graphs, and reports retract rows or
edges reachable only from removed/superseded inputs, while immutable audit and review events remain.
Shared content and facts supported by other active evidence are retained.

Implementation, dependency, contract, model, prompt, or configuration changes invalidate the
smallest stage-owned fingerprint boundary and all downstream artifacts that consumed it. Unrelated
repository or documentation changes do not invalidate results. `pipeline invalidate` prints the
affected shards, descendants, bytes, and recomputation estimate before recording a logical stale
transition. The next update builds replacements and switches active generation pointers only after
validation.

Physical removal is separate from logical invalidation. `artifacts prune --stale` defaults to a
dry-run plan and may delete only superseded derived files and database partitions that have no active,
pinned, review, rollback, or backup reference. `--apply --plan PLAN_ID` records a prune event and
retains compact manifests, lineage, checksums, and tombstones. It never deletes source archive files,
move ledgers, current outputs, or the sole recovery copy.

`pipeline rebuild` creates a fresh generation without cache reuse for the selected dependency
closure. It never clears the current generation first; the rebuilt generation becomes active only
after contract, count, checksum, and query validation, after which the prior generation is eligible
for the same explicit prune policy. This supplies a true from-scratch path without sacrificing
rollback evidence.

Pipeline stages never modify the archive. The separately authorized archive-reorganization command
is the only exception and records every rename in the sealed move ledger before execution. Duplicate
resolution, suppression, entity merges, and fact review remain overlays with audit trails and
rollback.

## Logging, progress, and observability

Every long-running command emits:

- one human-readable console stream with UTC timestamp, run/stage/shard, counts, throughput, ETA,
  elapsed time, and current resource summary;
- one structured JSONL log under `RUNS_DIR/<run-id>/logs/`;
- periodic progress rows in PostgreSQL, enabling `arxiv-int run status` and dashboards;
- a final stage manifest with input/output counts, bytes, durations, warning/error taxonomy, model
  telemetry, and next action.

Concurrent worker logs pass through one queue to avoid interleaving. Document text, prompts,
credentials, and full paths are excluded from normal logs; a redacted document id is enough.
Progress updates are time- and count-throttled. Heartbeats distinguish a slow shard from a dead
worker. Signals request a checkpoint and clean stop before forced termination.

Optional Grafana dashboards cover stage throughput, backlog, failure classes, CPU/RAM/disk/GPU,
Postgres/WAL/index size, topic drift, entity/fact review queues, and retrieval quality. Metrics
labels have bounded cardinality.

## Performance and scalability assumptions

The design targets one workstation and several terabytes of source files, not several terabytes of
clean searchable text by assumption. A pilot must measure extraction yield, normalized-to-raw ratio,
unique chunk count, average token length, index amplification, and vector-selection rate before a
full run.

Operational rules:

- stream file discovery and hashing; never hold the inventory or document set in RAM;
- use partitioned Parquet, DuckDB/PyArrow scans, bounded queues, and backpressure;
- hash once where possible and cache extraction by content hash, not path;
- bulk-load with `COPY`, delay expensive indexes until representative bulk load, and build by
  partition or staged table;
- keep large transactions bounded and monitor WAL, checkpoints, autovacuum, temp, and free space;
- account for ParadeDB's covering-index duplication when selecting indexed columns;
- run exact/normalized dedupe before chunking and near-dedupe before embedding;
- embed selected tiers only and use `halfvec`, IVFFlat, binary quantization, or native vector only
  after measured recall/cost comparisons;
- use one GPU-heavy process at a time on 16 GB VRAM; CPU workers remain memory-bounded;
- keep at least one unindexed rebuild copy of normalized artifacts on an independent path or backup.

### Pre-run forecast and resource refusal

`arxiv-int pipeline forecast` is a read-only prerequisite for a new or materially changed run. It
combines the current inventory/delta, cache-hit plan, format mix, configured stages and profiles,
sample measurements, and comparable prior run telemetry. It prints and writes JSON containing, per
stage and target filesystem:

- input files/bytes and added, changed, renamed, removed, cached, and recomputed shard counts;
- expected output bytes as a range for normalized data, database heap, indexes, vectors, graph,
  registered artifacts, logs, and backups;
- peak temporary, WAL, staging, rebuild, and rollback space for the selected pipeline, without
  double-counting paths on the same filesystem device;
- expected wall-clock time as a range, critical path, CPU/GPU/RAM assumptions, and heavy model loads;
- currently accessible free bytes, configured reserve, required headroom, confidence, and the sample
  or prior-run evidence behind every coefficient;
- a per-stage decision of `ready`, `degraded`, `blocked`, or `unknown` with corrective actions.

No fixed multiplier is universally safe. With no comparable evidence, the forecast uses conservative
declared bounds and marks confidence low; it never invents a precise duration. The initial planning
envelope is **2.5-4.0 times the normalized indexed subset in addition to the raw archive**, and a
full run is refused until a pilot replaces that envelope with measured amplification and a safety
margin. Concurrent index rebuild may temporarily require a second full index.

The command resolves device ids and checks read/write accessibility plus actual free space for
`RESULTS_DIR`, `PGDATA_DIR`, `RUNS_DIR`, `TMP_DIR`, `SERVICE_STATE_DIR`, model cache, backup, any
configured WAL or tablespace root, and any selected export path. The separate organizer forecasts
its own copy target and
move backup; pipeline forecasts do not depend on a placement plan. Roots that share one device are
budgeted once and reported together, and the storage class
measured for each root is carried into the forecast, so a `database` or `scratch` root on a
rotational device widens the time range and lowers confidence instead of being estimated as if it
were fast. It exits non-zero before work when a requested stage's
upper-bound peak plus safety reserve does not fit. The orchestrator requires a current forecast
fingerprint and rechecks free space immediately before every large materialization, bulk load, index
build, embedding batch, graph build, render, backup, and rebuild switch. Falling below the hard
reserve checkpoints cleanly and blocks the next allocation rather than waiting for an out-of-space
failure. An `unknown` estimate for a large stage
requires a bounded pilot or an explicitly smaller scope, not a silent override.

The first scale gate uses at least a representative 0.1-1% or 50-200 GB slice, whichever captures
the file-format and language distribution. A second gate uses a larger partition before full-corpus
authorization.

## Analysis, graph, and visualization behavior

Topic discovery produces stable topic ids, centroids/terms, representative evidence, parent-child
links, assignment confidence, and drift across corpus partitions or time. Labels are proposed by
deterministic terms first and optionally refined by a local LLM; the proposal remains attributable.

Entity resolution is probabilistic and reversible. Blocking uses normalized identifiers, names,
locations, model numbers, and co-occurrence; reviewer labels select operating thresholds on a
precision/recall curve. A merge proposal never rewrites source mentions.

Fact extraction combines patterns, tables, NER relations, and local structured LLM extraction.
Validation checks types, units, ontology domain/range, functional relations, temporal coherence,
duplicate claims, contradictions, and evidence spans. Catalogs explicitly include `company`,
`product`, and `person` outputs; equipment and supplier lists
are filtered views. Every entry carries canonical and unresolved ids, preferred/alternate names,
source-asserted identifiers, document counts, first/last evidence, roles, relation counts, confidence,
review state, identity snapshot, and source citations. A document overview index adds available
title/date/format, representative extractive snippets,
content/section/table pointers, topics and linked entities, with an extraction-quality indicator.
Missing titles or summaries stay explicit rather than being invented. Catalogs expose filters by
topic, file class, role, time, silo, and evidence quality. Empty and unresolved categories remain
visible. Their counts
reconcile to canonical snapshots and change correctly after a merge, split, or source removal.

`reports/index.html` is the default analyst entry point: archive coverage and unreadable formats,
major topics/content summaries, the three catalogs, domain graphs, prioritized anomalies, conflicting
claims, and unanswered questions. Rank findings with a declared policy over severity, evidence
quality, recency, and analyst-selected scope; an LLM cannot invent importance or supporting claims.
Each summary links to a bounded detail view, fact/derivation, and original document/cell/page through
source lookup. Filters and graph depth/time/result caps are visible, and truncation is explicit.
Portable HTML and JSON work without Grafana or AGE Viewer; source opening uses an explicit local
command or service, not browser access to arbitrary filesystem paths. A deterministic templated
report is required; generative summaries and cited question answering are optional and must abstain
when evidence is insufficient. No global performance/quality claim is inferred from missing gold.

Visualization uses:

- AGE Viewer for exploratory Cypher subgraphs when the graph profile is active;
- Grafana with PostgreSQL queries for progress, counts, topic/entity/fact dashboards, and bounded
  node-edge panels;
- generated HTML reports and open exports (CSV/Parquet, GraphML, JSON-LD, RDF/Turtle) for portable
  inspection;
- optional local notebooks against DuckDB/Parquet for research, never as the operational pipeline.

All graph/UI queries have result, depth, time, and text-size limits.

## Domain investigation artifacts

Generic objects and facts are not sufficient for an operator investigating technical design and
commercial records. When supported evidence exists, the pipeline produces the following named,
versioned artifact families from canonical objects and facts:

- `relationship-map`: typed relationships among designs, products, documents, revisions, natural persons,
  legal entities/organizations, equipment, materials, accounts, contracts, and events;
- `bill-of-materials`: assembly/component/material hierarchies with part numbers, quantities,
  units, alternatives, revision/effectivity, and unresolved references;
- `supply-chain`: supplier, manufacturer, customer, location, order, shipment, invoice, and payment
  relationships, including direction, time, and status where the source states them;
- `invoice-payment`: invoice lines and totals, currencies, due dates, payment events, allocations,
  and evidence-backed matched, partial, duplicate, disputed, or unmatched states.

### Financial, bookkeeping, and party relationship semantics

The financial lane reads invoices/credit notes, bank/payment records, bookkeeping journal or ledger
exports, orders, contracts, and supporting receipts when present. It preserves document type, issuer,
source-asserted identifiers, line numbers, posting/document/due/payment dates, currency, exact decimal
amounts, debit/credit side, tax and discount fields, and corrections/reversals. Spreadsheet formulas
and cached values are identified; the extractor does not execute workbook macros or active content.

Represent legal entities and natural persons separately and link them through evidenced roles such
as signatory-for, representative-of, employee-of, payer, payee, account-holder, supplier, buyer, and
manufacturer. Ownership/control is included only when explicitly asserted by cited evidence, with
its effective time and review policy. Co-occurrence, similar names, a shared contact/address, an
account reference, or a payment is a candidate association, not proof of ownership or identity.

Transactions/events preserve all participants and roles before projecting binary graph edges.
Matching invoices to payments supports many-to-many allocations, partial payments, credit notes,
reversals, overpayments, duplicate candidates, and unmatched records. Journal balances are checked
within the source's declared accounting scope, never across unlike currencies or incomplete exports.
Allocation totals cannot silently exceed the applicable amount; tolerances, rounding, and currency
conversion policies are explicit. No bank event is inferred solely from an invoice marked paid.
These are source-record analytics, not jurisdiction-specific legal/accounting determinations.

### Product, BOM, and supply-chain semantics

Product descriptions and technical tables supply product/model/revision identifiers, assemblies,
components, materials, manufacturer claims, quantities, units, and specifications. A mentions/uses
relation alone cannot become a component requirement. Every BOM states whether it is explicitly
listed or derived, its root product/revision, source scope, effectivity, exclusions, and completeness
limits. Unknown quantities stay null; listed alternatives never add together as mandatory parts.
Multi-level rollups require compatible units and explicit conversion factors, preserve quantity per
parent and cumulative derivation, detect cycles, and keep conflicting revisions separate. A valid
output may be a partial BOM or no BOM for a marketing-only product description.

Supply-chain views separate quoted, ordered, invoiced, shipped, received, and paid stages. A catalog
supplier claim does not prove an actual shipment. Paths retain product/revision, party role,
transaction, time, source coverage, and confidence. Basic analytics include evidenced supplier
concentration and single-observed-source dependencies with denominators and coverage warnings;
absence of another observed supplier does not prove that none exists in the world.

### Publication and evaluation

Each family has a contracted tabular/JSON representation and a bounded graphical representation.
Bills of materials render assembly trees or part-of subgraphs; supply-chain and invoice/payment
artifacts render directed networks or flows; the general relationship artifact renders a filtered
evidence graph. Portable outputs include Parquet/JSON plus GraphML and self-contained HTML or SVG.
The renderer selection follows the dependency policy and must not pull a GPU/ML or large browser/UI
stack into the core installation merely to draw bounded graphs.

These artifacts are derived investigation views, not new truth stores. Every node, edge, table row,
amount, quantity, and reconciliation state resolves to canonical fact ids and exact source evidence,
and displays confidence, review state, inclusion policy, and conflicts. Arithmetic checks preserve
source currency and units; conversions require an explicit rate and source. A referenced component
does not become a `part-of` fact, an invoice does not prove delivery, and an invoice/payment amount
or date resemblance does not prove settlement. The system does not infer missing ownership,
liability, sanctions status, engineering completeness, or accounting correctness.

Every run that reaches the `domain-artifacts` stage writes an artifact registry in `ctl.artifact` and
`$RUNS_DIR/<run-id>/artifacts/registry.{json,parquet}`. A registry row contains artifact id and type,
schema/version, generator/configuration/policy fingerprints, input fact and identity snapshots,
review-state inclusion rules, URI or relative path, media type, byte/count/checksum summaries,
evidence-coverage statistics, creation status, and failure reason. Allowed creation statuses include
`produced`, `partial`, `empty`, and `failed`; `empty` is the valid negative result when the run found
no qualifying evidence. Registry publication is atomic, and a failed artifact never appears as a
successful run result.

Evaluation uses reviewed design, assembly, procurement, invoice, and payment fixtures. It measures
typed relation and edge precision/recall, BOM parent/child and quantity/unit accuracy, invoice total
arithmetic, payment-allocation accuracy, unresolved/conflict coverage, graph-to-table parity,
evidence-link validity, deterministic rendering, and registry completeness. Acceptance is per
artifact family; a weak family remains `partial` or disabled without blocking useful families.
Human approval defines high-impact inclusion states and confirms that labels such as `paid`,
`supplier`, and `part-of` match the archive's domain meaning.

## Anomaly detection and triage

Analysts need a reproducible entry point into unusual records and relationships rather than only
counts or an unfiltered graph. The `anomaly-analysis` capability consumes selected canonical,
domain-artifact, topic, and inventory snapshots and emits explainable findings; it never edits
source data, merges identities, accepts facts, or labels a person/company as fraudulent.

The required baseline uses deterministic constraints and bounded descriptive statistics:

- data/evidence: extraction gaps, duplicate candidates, identifier conflicts, contradictory facts,
  missing anchors, and classification/topic coverage shifts;
- financial: source-total inconsistencies, duplicate invoice/payment candidates, unmatched or
  overallocated records, and unusual amounts within comparable currency/role/time cohorts;
- relations/supply chain: unusual new counterparties, concentration, repeated/cyclic transaction
  paths, and single-observed-source dependencies in a declared time/product scope;
- product/BOM: cycles, missing component references, nonpositive or conflicting quantities, unit
  incompatibilities, and revision/effectivity conflicts.

A finding stores its detector/version, input generation, subject/fact ids, source/derivation links,
rule and observed value, expected constraint or comparison cohort, units/currency, time window,
minimum sample size, score, severity, confidence, rank rationale, and coverage limits. Scores are
signals, not probabilities of wrongdoing. Missing data, small cohorts, or incompatible quantities
produce `insufficient-evidence`, not an outlier claim. Findings have stable identities, grouped
related evidence, and reversible review states `new`, `in-review`, `dismissed`, or `explained`.
Reviewer reasons do not remove source facts; reruns and new data preserve review history while
invalidating stale calculations. Review state does not train a model without a declared evaluation.

Publish contracted JSON/Parquet findings plus bounded tables, histograms/time comparisons, and
highlighted subgraphs linked from the entry report. Rank and filters expose detector, severity,
confidence, topic, entity type, period, source quality, and review state. Every configured detector
reports evaluated/skipped/insufficient counts and denominators, including when there are zero flags.

Evaluation freezes positive and negative fixtures, cohort definitions, thresholds, time splits, and
a review budget before scoring. Measure per-detector precision/recall on labelled cases,
precision at the review budget, false-positive burden, source-link validity, temporal leakage,
determinism, grouping, and bounded resource use. Held-out archive review may conclude that a detector
is unhelpful: retain constraints only, mark a statistical detector `not-selected`, or report no
supported findings. ML detectors are outside the required baseline and need their own measured
proposal; no requirement to generate a nonempty anomaly list is allowed.

## Implementation boundaries

Project modules own orchestration, contracts, policy, metrics, and backend-neutral interfaces.
Maintained engines such as Tika, Docling, OCRmyPDF/Tesseract, PyArrow, Polars, DuckDB,
Data Contract CLI, SQLAlchemy Core, Alembic, dbt Core, Pandera, ParadeDB, pgvector, AGE,
rdflib/pySHACL, Splink, Ollama, and vLLM are integrated through narrow adapters rather than
reimplemented. Optional stacks remain in the feature group that activates
them, and runtime artifacts never depend on a sibling source checkout.

### Development integrity and review checkpoints

Tasks must remain reviewable across model budgets. `project-foundation` owns the development
workflow; each capability owns its repairs and checkpoints. [AGENTS.md](../../AGENTS.md) gives the
task cycle and conditional guidance; agents need not preload the entire documentation tree.

Permanent records under `docs/impl/records/` retain full accepted task text, amendments, decisions,
acceptance evidence and routed audit notes. Current pages describe available behavior and link
records; the plan holds only unresolved work. Summaries and Git history cannot replace task scope.

Task-local review is mandatory. Finite foundation/store, corpus/control, knowledge/identity,
investigation/report, production/recovery, semantic and archive-organization checkpoints declare
inputs, invariants, evidence and downstream gates. No refactor needed is a valid result. Blockers
require separate repairs before consumers proceed; each concern has one owner. New rounds use new
ids. Fixture reviews cannot waive real-data, CUDA or human gates; unavailable private labels cannot
block independent fixture implementation.

Checkpoint placement follows dependency risk, not just the end of a large capability group. Add
bounded reviews after inference/evaluation foundations, pipeline publication orchestration,
control integration before the first corpus producers, retrieval/classification integration,
domain-artifact/anomaly integration, and recovery preparation
before scale pilots. Each names the exact producer records, cross-module invariants and first gated
consumers. Producers accepted after a checkpoint closes are reviewed by a later round before their
own first consumer starts; the closed round cannot stand in for them. The knowledge/identity
checkpoint additionally covers dynamic ontology snapshots,
geotemporal assertions and domain distinctions. Wire required consumer dependencies explicitly;
a `Review checkpoint` label alone does not block execution. Reviews neither reopen accepted
0029-0033 nor replace their evidence; they verify integration with the later producers.

Agent tasks that produce human-review artifacts name a `Human review handoff`: the human task id,
packet path, required decisions and blocked downstream work. Human prerequisites use explicit task
ids, including other human decisions. Producers prepare candidates and evidence without depending
on approval of the very packet they must create. At completion the agent reports whether each
packet is ready, what is missing, how to inspect it, the decision needed and the next blocked task.
It stops dependent work until the human decision is recorded; independent fixture work may continue.
Approval binds exact artifact/code/model/ontology/policy fingerprints and scope. Changed evidence
requires renewed review; a model verdict or successful checkpoint cannot approve on the human's
behalf. The [handoff workflow](../guide/planning-workflow.md#human-review-handoffs) defines the message.

Implementation tasks add tests for integrity, correctness, and business logic: the happy path, the
main corner cases, and a regression for each defect found. That set is sufficient while interfaces
are still changing. Do not add tests that only freeze current implementation, configuration
snapshots, or historical policy. The suite stays a specification of required behavior, not an
inventory of incidental coverage. A numeric line or branch coverage percentage is not an
acceptance signal and must not fail `make ci` or `make quality`. Coverage reports remain
diagnostic. Milestone checkpoints add targeted tests for important cases once that stage's
interfaces have stabilized. Concluding that existing tests already cover those cases is valid.
Restoring a numeric coverage floor is out of scope.

Refactoring preserves public behavior except specified defect fixes. Reuse typed seams and shared
root, service, credential, contract and artifact policy; avoid frameworks or line-count-only splits.

Evaluation requires manual gate-to-evidence review of the recorded evidence itself. Automated
fixtures detect lost multiline fields, dangling open/archived dependencies, cycles, missing accepted
task snapshots, orphan notes and unresolved checkpoint blockers; they judge resolvable structure,
not whether the evidence behind a gate is sufficient. This workflow does not select models or
claim that a model choice proves implementation quality.

## Evaluation and acceptance

### Evaluation datasets

Before store or model promotion, freeze a representative corpus manifest and reviewable gold sets:

- file-format/extraction set with expected text, tables, page/offset anchors, and failures;
- hierarchical file labels with primary/alternate paths and expected `unclassified`/`unreadable`
  outcomes;
- Russian lexical query set including inflection, identifiers, abbreviations, OCR noise, e/yo
  variants,
  keyboard-layout mistakes, and mixed-language queries;
- semantic and multi-hop query set with exact source spans;
- entity pairs/clusters with match/non-match labels;
- entity and relation/fact extraction set by high-value type;
- ontology constraint and contradiction cases;
- graph path/query answers checked against relational SQL;
- company/product/person catalog cases, including same-name nonmatches, roles, merge/split and
  removal effects, plus equipment and supplier report cases with evidence and coverage review;
- anomaly positives, hard negatives, insufficient cohorts, time leakage, review budgets, and
  source/derivation links;
- design relationship, BOM, supply-chain, invoice, and payment cases with reviewed edges,
  quantities, units, totals, allocations, conflicts, and valid empty results.

Gold creation and threshold setting use separate tuning and final partitions. LLM-drafted items do
not become scoring truth without review. During development the operator points `ARCHIVE_DIR` at one
authorized representative slice and uses the ordinary pipeline or stage commands. Machine-specific
paths, source text and gold sets stay out of the repository; they are published and reviewed under
the configured roots, per
[published proof and evaluation data](#published-proof-and-evaluation-data).

### Published proof and evaluation data

No archive, corpus, gold set, proof bundle, or other archive-derived artifact is committed to this
repository or prepared for a commit. There is no sanctioned export path that turns source-derived
content into repository files, obfuscated or otherwise. Such data lives only under the
operator-configured roots: `ARCHIVE_DIR` and any `ARCHIVE_SILO_<ID>_DIR` for read-only sources, and
`RESULTS_DIR`, `RUNS_DIR` and `PGDATA_DIR` for produced artifacts.

The operator publishes an archive and its result artifacts separately from this repository and, when
sharing them, points the corresponding variables at the published location. The repository never
carries a copy, a sample, an excerpt, or a location of specific data. Producing and publishing a
dataset for analysis is the operator's separate activity, not a project deliverable.

A reviewer checks an implementation in place. With those roots configured, the ordinary read-only
commands report whether the expected artifacts exist, whether their checksums, contracts and
validator results hold, and how they trace back to source occurrences, without copying anything into
a repository. Presence and integrity of database-backed results are checked the same way against the
configured store. A proof bundle records its own fingerprint so a reviewer can confirm the bundle
they hold is the one a record names.

The repository holds code, contracts, ontology assets, configuration, documentation, and fixtures
authored for tests. A committed fixture must be synthetic: written to exercise a rule, never derived
from, sampled from, or reconstructed from archive content. Synthetic fixtures still satisfy the
ordinary secret and path rules.

Design documents, plan tasks and records name roots, contracts, stages and fingerprints. They do not
name specific archives, corpora, collections, entities, or datasets, and they do not embed source
text. Current-state pages and records may cite proof ids, fingerprints, counts, validation summaries
and verdicts; machine-specific paths, source content and real identities stay out of Git.

### Provided-archive proof runs

Configured archive silos (`ARCHIVE_DIR` and optional `ARCHIVE_SILO_<ID>_DIR`) are the file-silo
source for integration proof. There is no second proof-only source root. After the required
implementation tasks for each artifact-producing capability group, a final `RUN NEEDED` task
executes every then-usable stage in that group against those silos using the ordinary pipeline or
stage commands. A later behavior change that alters a stage or its inputs must regenerate the
impacted proof before that change is complete; an older bundle remains historical evidence but is
marked stale by fingerprint.

| Capability group | Proof scope |
| --- | --- |
| `corpus-foundation` | `inventory`, `extract`, `normalize`, `dedupe`, and `chunk` artifacts |
| `pipeline-control` | forecast, cache hit, resume, delta update, invalidation, rebuild, and prune planning |
| `archive-classification` | complete classification mapping, hierarchy, exceptions, and source lookup |
| `lexical-retrieval` | lexical load, index manifest, queries, filters, and source citations |
| `semantic-retrieval` | selected embeddings/vector load and paired verdict, when the branch is usable |
| `russian-nlp` | language, morphology, terminology, and mention artifacts |
| `knowledge-extraction` | proposed facts, `validate-facts`, conflicts, and evidence links |
| `identity-ontology-graph` | clusters, ontology validation, graph/fallback exports, and parity checks |
| `domain-investigation-artifacts` | relationship, BOM, supply-chain, invoice/payment, and registry outputs |
| `anomaly-analysis` | detector coverage, findings, baselines, review replay, and bounded graphs |
| `discovery-visualization` | topics, three catalogs, search/report scenarios, exports, and configured local views |
| `evaluation-evidence` | `evaluate`, `report`, and an end-to-end proof index over all prior bundles |

Each task first runs the forecast and refuses a blocked scope. It records a proof bundle under
`$RESULTS_DIR/proofs/<capability-id>/<proof-id>/` containing the redacted command/configuration,
source-manifest hash, code/contract/dependency/model fingerprints, forecast, stage and shard ledger,
artifact registry with checksums, validator results, errors/quarantines, resource/timing metrics, and
an overall verdict. The proof reruns the unchanged scope and demonstrates that heavy stages are cache
hits. Incremental-control proof uses a bounded disposable copy or overlay under the data root to test
add/change/rename/remove cases and never mutates the configured archive silos.

A required usable stage passes only with validated artifacts or a contract-defined valid empty
result. Failure, missing evidence, or resource refusal keeps its proof task open. An optional branch
may record `not-selected` with an explicit selection reason and working fallback; comparative
promotion or rejection claims additionally require a measured verdict. Repository
current-state documentation records proof ids, fingerprints, artifact paths, validation summaries,
and results. It commits no source-derived content and never copies machine-specific archive paths
into Git; a reviewer reads the bundle itself under the configured roots.

### Required acceptance gates

| Area              | Gate                                                                                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Fresh setup       | From a copied repo, `make setup` creates or extends `.env`, reports required edits, and retries safely to verified service/schema/model readiness. Bare `make pipeline` then produces the required manifest/report using `.env`; the documented atomic chain is equivalent. Missing implementations remain explicit. `make ci` passes without paths tied to the original disk. |
| Operator entrypoints | `make setup`, edit `.env`, and retry reaches verified readiness without losing completed work; bare `make pipeline` performs forecast through validated report publication with no manual stage commands. |
| Contracts         | ODCS lint, generation drift, Avro round-trip/compatibility, evolution policy, migration status, and live Postgres schema tests pass.                                                             |
| Migrations        | Contract-derived SQLAlchemy metadata, reviewed Alembic Python history, empty/prior-release upgrades, verified legacy adoption and live catalog parity pass; unavailable live checks remain not-run. |
| Transformations   | Described dbt models and typed Polars operations retain source/rule lineage; clean/incremental/deletion parity, role isolation and failed-build activation refusal pass. |
| Data quality      | Pandera batch checks and whole-snapshot dbt/disk-backed checks cover contract rules; missing/failed required checks block publication with bounded redacted evidence. |
| Idempotency       | Re-running an unchanged successful shard writes no duplicate canonical rows or artifacts and reports a cache hit; interrupted stages resume from completed shards.                               |
| Incremental state | Added/changed/renamed/removed sources and stage-owned implementation changes invalidate only their lineage closure; active views retract stale outputs and retain audit evidence.                 |
| Forecast          | Time/size ranges cite evidence, all target devices and peak scratch/rebuild needs are counted, and insufficient free space blocks before heavy allocation.                                        |
| Published proof data | Proof, gold and dataset artifacts stay under the configured roots; no archive-derived file is committed or staged for commit; a reviewer validates presence, checksums and contracts in place. |
| Ontology/geotemporal integrity | Pinned ontology evolution, source-valid versus recorded time, place/CRS uncertainty, revision/effectivity and domain non-implication fixtures pass across validators, SQL, graph and reports. |
| Proof bundles     | Every usable artifact-producing stage group has a current provided-archive proof whose outputs, checksums, validators, cache-hit rerun, and fingerprint are complete.                              |
| Provenance        | Every sampled search result, mention, fact, topic assignment, graph edge, and report row resolves to source evidence and a complete transformation fingerprint.                                  |
| Extraction        | Per-format text/table/anchor coverage and quarantine reasons meet thresholds declared before the full run.                                                                                       |
| Classification    | Hierarchical accuracy, calibration, exceptional outcomes, reproducibility, and path-ledger safety gates pass; uncertain files are not forced into ordinary classes.                              |
| Lexical retrieval | Russian BM25 recall@k, MRR, evidence intactness, p95 latency, and index amplification pass on the final query set.                                                                               |
| Vector/hybrid     | Candidate must beat or complement lexical retrieval with a paired confidence interval and remain within build, storage, latency, and VRAM/RAM budgets; otherwise lexical-only is a valid result. |
| Entity resolution | Precision at the proposed auto-merge threshold meets the predeclared high-precision target; uncertain pairs remain unmerged.                                                                     |
| Facts             | Per-type precision/recall and citation-span validity meet declared thresholds; invalid structured output and ontology violations are accounted for.                                              |
| Graph             | Counts reconcile with relational projection inputs; sampled SQL/Cypher paths agree; rebuild and backup/restore tests pass.                                                                       |
| Catalogs and entry report | Company, product, and person outputs reconcile to identity snapshots; report drill-down reaches facts and source anchors without optional services. |
| Anomalies | Predeclared per-detector accuracy/review-budget and coverage gates pass; insufficient evidence and no useful statistical detector are valid outcomes. |
| End-to-end | One investigation command on one CUDA host publishes the required generation and entry report; no-op rerun reuses heavy work and source bytes remain unchanged. |
| Domain artifacts  | BOM, relationship, supply-chain, and invoice/payment tables and graphs agree with reviewed facts, evidence links, arithmetic, and registry status.                                                |
| Scale             | Two staged pilots complete within measured disk/RAM/VRAM envelopes with no unbounded queue, transaction, temp, or WAL growth.                                                                    |
| Privacy           | Network-denied integration run succeeds after required images/models are present; logs and reports contain no secrets or unintended corpus content.                                              |

Each comparison ends in `adopt`, `retain baseline`, or `inconclusive`; a negative result is valid
and must not be hidden by choosing a convenient threshold.

## Operations, backup, and security

Every service bind-mounts the archive read-only, and every ordinary pipeline stage opens it only for
reading. The host directory itself may remain writable. Only the explicit host-side
archive-reorganization command may modify it, only in `move` mode, and only with an
accepted dry-run plan, a sealed ledger, and a recoverable backup or equivalent snapshot; its `copy`
mode writes solely into the declared target root. Service ports bind to loopback.
Database roles separate migration, pipeline writes, read-only UI, and backup. Secrets live in `.env`
or operator-provided secret files, never generated artifacts or logs. Containers run non-root where
upstream images permit, have bounded resources, and receive only required mounts.

Backups include:

- ODCS contracts, migrations, configuration template, and code in version control;
- normalized manifests and portable datasets through filesystem snapshots or another disk;
- classification snapshots and archive move ledgers needed to locate or reverse moved sources;
- review/identity decisions, anomaly dispositions, inclusion policies, and non-reproducible run
  evidence, exported with canonical snapshot ids and backed up independently of derived views;
- PostgreSQL logical/physical backup appropriate to the pinned extension versions, covering
  `PGDATA_DIR` together with any configured `PG_WAL_DIR` and named tablespace roots as one unit,
  because a cluster is not recoverable from a subset of them;
- `SERVICE_STATE_DIR` only where a service holds state the repository does not provision;
- extension/image/model digests and a restore runbook;
- restore verification that rebuilds or validates ParadeDB and AGE projections.

Because Community ParadeDB does not promise enterprise HA/read-replica support, local recovery is
based on tested backup plus projection rebuild, not an assumed replica.

## Delivery strategy

Registry order is implementation priority, not a requirement to finish every proof in one group
before starting another. Follow explicit task dependencies across groups. Build control interfaces
with fixture stages first, then register corpus stages; seal base ontology and domain contracts
before extracting facts. Identity anchors precede facts; graph projection follows validated facts.
Research and human acceptance never substitute for deterministic implementation checks.

| Milestone | Required usable result | Exit signal |
| --- | --- | --- |
| Foundation | Portable runtime, contracts, canonical store, inference seam, evaluation fixtures, stage control | Fresh-copy and fixture-only DAG/contract/store smoke |
| Searchable archive | Inventory through chunks, lexical search, complete classification, resume and forecast | Bounded directory-to-search run and corpus/control/classification proofs |
| Investigation baseline | Mentions, identity anchors, facts, topics, three catalogs, domain views, anomaly constraints, portable report | One `investigation` command publishes every required family or justified empty/partial state |
| Production acceptance | Held-out quality, single-CUDA capacity, update/recovery, and two staged pilots | End-to-end proof, restore/failure evidence, and explicit full-corpus authorization |
| Optional branches | Selected vectors, generative answers, AGE/viewers, or archive placement | Branch-specific evidence or explicit non-selection; core pipeline remains usable |

The runtime dependency graph and the first complete vertical slice are specified in the
[execution architecture](architecture.md). Semantic comparisons and archive placement do not delay
that slice. Archive organization is a separate product utility delivered against classification
artifacts and accepted independently; using it is never required to finish a pipeline run.

## Capability Registry

Every capability appears once. Status is `planned` until current-state documentation and acceptance
evidence exist. Registry order is the implementation line used by `plan.md`.

| #   | Capability                | Status  | How it is evaluated                                                                          | Implementation                                               |
| --- | ------------------------- | ------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 1 | `project-foundation` | shipped | Fresh copy, rename, locked bootstrap, CLI identity, docs integrity, and CI pass | [Project foundation](../impl/current/project-foundation.md) |
| 2 | `portable-runtime` | shipped | Existing path/profile gates plus fresh setup, edit/retry, cached assets, failure propagation and shared requirement resolution pass | [Portable runtime](../impl/current/portable-runtime.md) |
| 3 | `contract-governance` | shipped | ODCS generation/evolution, Alembic revision checks, shared dataset-quality checks and ontology gates pass; live schema upgrade/adoption is recorded under canonical-store | [Contracts](../impl/current/contracts.md) |
| 4 | `canonical-store` | shipped | Disposable extension compatibility, initial schema/adoption, dbt validation/publication and projection rebuild/cleanup pass the foundation checkpoint; operator recovery remains a separate capability | [Canonical store](../impl/current/canonical-store.md); [Checkpoint](../impl/records/0027-store-review-foundation-and-store-boundaries.md) |
| 5 | `local-inference` | shipped | Ollama/vLLM conformance, structured outputs, model-fit, host-wide GPU lease, and local-only endpoint gates pass | [Local inference](../impl/current/local-inference.md) |
| 6 | `evaluation-foundation` | shipped | Frozen synthetic fixtures, replayable metrics, split guards, paired verdicts, and immutable locally published bundles/proofs pass the inference/evaluation checkpoint | [Evaluation foundation](../impl/current/evaluation-foundation.md); [Checkpoint](../impl/records/0038-eval-found-review-inference-and-evaluation-boundaries.md) |
| 7 | `pipeline-control` | planned | Fixture-first DAG, output manifest, resume, generation activation, delta, forecast, and progress gates pass | [Open work](../impl/plan.md#pipeline-control----pipeline-control) |
| 8 | `corpus-foundation` | planned | Representative inventory, extraction, normalization, dedupe, and chunk gold sets pass | [Open work](../impl/plan.md#corpus-foundation----corpus-foundation) |
| 9 | `lexical-retrieval` | planned | Held-out Russian relevance, latency, index size, and rebuild gates pass | [Open work](../impl/plan.md#lexical-retrieval----lexical-retrieval) |
| 10 | `archive-classification` | planned | Hierarchical gold labels, calibrated exceptions, complete source accounting, and reproducibility pass | [Open work](../impl/plan.md#archive-classification----archive-classification) |
| 11 | `russian-nlp` | planned | Language, morphology, terminology, and NER metrics pass per type | [Open work](../impl/plan.md#russian-nlp----russian-nlp) |
| 12 | `identity-ontology-graph` | planned | Linkage, pinned ontology evolution, domain terms and typing, geotemporal uncertainty/as-of semantics, SQL/Cypher parity, rebuild, and bounded traversal gates pass | [Open work](../impl/plan.md#identity-ontology-and-graph----identity-ontology-graph) |
| 13 | `knowledge-extraction` | planned | Structured extraction, evidence, fact quality, and contradiction gates pass | [Open work](../impl/plan.md#knowledge-extraction----knowledge-extraction) |
| 14 | `domain-investigation-artifacts` | planned | Reviewed BOM, relationship, supply-chain, invoice/payment, render, and registry gates pass | [Open work](../impl/plan.md#domain-investigation-artifacts----domain-investigation-artifacts) |
| 15 | `anomaly-analysis` | planned | Per-detector fixtures, cohort/time guards, review-budget precision, provenance, and bounded triage views pass | [Open work](../impl/plan.md#anomaly-analysis----anomaly-analysis) |
| 16 | `discovery-visualization` | planned | Topic stability, three catalog parity, and analyst report/search/graph/anomaly drill-down scenarios pass | [Open work](../impl/plan.md#discovery-and-visualization----discovery-visualization) |
| 17 | `evaluation-evidence` | planned | Artifact-lineage checks and representative scale pilots produce readable, capacity-aware verdicts | [Evaluation](../impl/current/evaluation.md); [Open work](../impl/plan.md#evaluation-and-evidence----evaluation-evidence) |
| 18 | `operational-recovery` | planned | Security checks, backup/restore drill, disk exhaustion, interruption, and runbook tests pass | [Open work](../impl/plan.md#operational-recovery----operational-recovery) |
| 19 | `semantic-retrieval` | planned | Selected-tier vector and hybrid candidates receive paired adopt/retain verdicts | [Open work](../impl/plan.md#semantic-retrieval----semantic-retrieval) |
| 20 | `archive-organization` | planned | Artifact-only dry-run, independent copies, move backup, path accounting, resume, rollback, and lookup pass | [Open work](../impl/plan.md#separate-archive-organization----archive-organization) |

## Success criteria

The project succeeds when an operator can copy the repository to any suitable disk, bootstrap and
point `.env` at separate archive, results, and PostgreSQL disks, start
the selected local services, and run one stage or the complete pipeline with continuous progress and
safe resume. The default investigation command publishes an evidence-linked entry report, topics,
company/product/person catalogs, facts, graphs, and explainable anomaly findings that are useful
on a representative Russian corpus, carry source evidence, and can be rebuilt from open,
versioned contracts and normalized artifacts. Every source has a classified or explicit exceptional
outcome, optional physical moves remain traceable to the initial path, and every available BOM,
supply-chain, relationship, and invoice/payment view is registered with evidence and review state.
Unchanged inputs reuse validated heavy results, archive and implementation deltas update only their
lineage closure, stale derived data can be safely pruned or fully rebuilt, and forecasts refuse work
that cannot fit available storage. Every usable stage group has a current proof bundle from the
provided archive and the full investigation profile is proven by one executable run. Independent
copy/in-place organization consumes classification exports without joining the pipeline DAG.
The PostgreSQL architecture remains in place only while measured quality,
scale, and recovery evidence supports it.
