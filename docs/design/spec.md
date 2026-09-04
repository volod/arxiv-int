# arxiv-int Project Specification

## Purpose

`arxiv-int` is a local-first Knowledge Discovery Platform for multi-terabyte, mostly
Russian-language document archives. Its input is one or more read-only directory silos of ordinary
files; its output is evidence-backed knowledge: canonical objects, provenance-bearing facts, and the
search, graph, and investigation views built from them. Its Python distribution and import package
are both `arxiv-int` / `arxiv_int`. The system inventories and normalizes an immutable archive,
builds reproducible lexical and selected semantic indexes, discovers topics, extracts and resolves
entities and facts, classifies source files in a UDC-derived hierarchy, projects a knowledge graph
and evidence-backed domain artifacts, and supports local search, analysis, and visualization without
requiring document or prompt egress. An explicit, separately authorized maintenance command can
reorganize the archive after classification -- copying the classified tree into a target directory,
or moving the silo in place -- while preserving an auditable original-to-current path map.

The target workstation typically has about 128GB of RAM and 16GB of GPU VRAM. Speed is secondary to
quality, but every expensive result must be resumable, attributable, and independently rebuildable.

This specification is living. Product behavior, boundaries, and evaluation belong here. Remaining
implementation work belongs in `plan.md`; delivered behavior must eventually move to focused pages
under `docs/impl/current/`.

## Research basis and source snapshot

The design was reviewed on 2026-09-04 against the following upstream and reference repositories.
Commit pins record what was actually inspected; version pins used by the future implementation must
still be refreshed and compatibility-tested before the first lock is committed.

| Source                                                                                                        | Inspected revision                                          | Design consequence                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [ParadeDB](https://github.com/paradedb/paradedb/tree/c74bcde7bf6f6e44516d81f18350f2725d14fd5f)                | `c74bcde` (`0.25.6` workspace version)                      | ParadeDB is now a Postgres custom index for BM25, vector, hybrid, filters, aggregates, and joins, not merely an OpenSearch-like sidecar. Native vector indexing is still documented as beta. |
| [fl-op contracts](https://github.com/volod/fl-op/tree/1f452ecaeded92c6bbbd4a86de9ded1ea7444e60/contracts)     | `1f452ec`                                                   | Reuse the ODCS registry, canonical-model, generator, fingerprint, reviewed baseline, and semantic-evolution patterns.                                                                        |
| [selfsuvis](https://github.com/volod/selfsuvis/tree/bd0f4447bf20a72e9421c93f208ce1f52f1c622b)                 | `bd0f444`                                                   | Reuse layered environment/path resolution, preflight checks, serialized concurrent logging, per-step timings, GPU-aware model scheduling, and partial-result preservation.                   |
| [loc-lm-bench](https://github.com/volod/loc-lm-bench/tree/23519f7f0255c8b5ccfe4d2a4c9a5e4adf24e1a3)           | `23519f7`                                                   | Reuse the evidence discipline for ingestion, corpus hygiene, probabilistic linkage, retrieval comparison, local model serving, answer evaluation, and provenance.                            |
| [agent-py](https://github.com/volod/agent-py/tree/d7c3467b6f6b3816c2c1aad34eb3871f5da8ef22)                   | `d7c3467`                                                   | Use the repository template, Python 3.12+, `uv`, Make entrypoints, typed `src` layout, CI gates, capability registry, and forward-only planning lifecycle.                                   |
| [Apache AGE](https://github.com/apache/age/tree/0e30566226f017d53b7f52025803b38af3ad2b3f)                     | `0e30566`; README advertises AGE 1.8.0 and PostgreSQL 11-18 | AGE is feasible on the same PostgreSQL major, but the ParadeDB combination is not listed as an upstream-tested extension set and needs a project-owned image and compatibility gate.         |
| [pgvector](https://github.com/pgvector/pgvector/tree/e48241b4dcc045b18902914f668d03d1d399dfbe)                | `e48241b`; README install pin `0.8.6`                       | Stable exact, HNSW, IVFFlat, half-vector, binary-quantization, and iterative-scan baseline; large HNSW builds remain memory and maintenance intensive.                                       |
| [ODCS](https://github.com/bitol-io/open-data-contract-standard/tree/f5bfbb813fe2c0551e2c324913f330e7807885d8) | `f5bfbb8`; standard `3.1.0`                                 | ODCS is the human and machine-readable contract source of truth; its custom properties carry project generation hints that the standard does not define.                                     |
| [UDC Consortium](https://udcc.org/index.php/site/page?view=about_structure) and [UDC overview](https://en.wikipedia.org/wiki/Universal_Decimal_Classification) | Web references inspected 2026-09-04                        | UDC supplies a faceted, syntactically expressive hierarchy; the project must pin an authorized vocabulary snapshot and keep local outcomes/extensions distinguishable from official notation. |

Additional current upstream facts used by the decision:

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
- ODCS `3.1.0` is current and the open-source Data Contract CLI can lint, compare breaking changes,
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
  [UDC Summary](https://udcc.org/udcsummary/php/index.php?lang=en&tag=--) and
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
- selective multilingual embeddings, reranking, and local RAG;
- topic discovery, entity mentions, entity resolution, provenance-bearing fact extraction, ontology
  assets, and graph projection;
- registered relationship, bill-of-materials, supply-chain, and invoice/payment investigation
  artifacts when the archive contains sufficient evidence;
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
plus a separately assembled `pg_search` installation. Build a small project-owned derivative image
on one supported PostgreSQL major to add Apache AGE. Enable AGE and its viewer through a Compose
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
SSD A: ARCHIVE_DIR (read-only)         SSD B: RESULTS_DIR
          |                                      |
          v                                      v
 inventory -> extract -> normalize -> dedupe -> partitioned Parquet/Avro
                          |                       |
                          +---- run manifests ----+
                                      |
                                      v
SSD C: PGDATA_DIR          ParadeDB / PostgreSQL (tables and indexes)
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
independent root, written only by that authorized command.

## Repository and package structure

The repository foundation was adapted from the pinned `agent-py` source above. Behavior that exists
today is indexed by [current implementation](../impl/current.md); the target layout the capabilities
below build toward is:

```text
arxiv-int/
  AGENTS.md
  Makefile
  compose.yaml
  .env.example
  pyproject.toml
  uv.lock
  contracts/
    registry.yaml
    canonical/
    datasets/
    mappings/
    evolution/
    generated/
  db/
    migrations/
    schema.sql
  docker/
    postgres/Dockerfile
    postgres/initdb/
    grafana/
  configs/
    capacity/ classification/ evaluation/ models/ nlp/ policy/ proofs/ retrieval/ topics/
  ontology/
  src/arxiv_int/
    cli.py
    config.py
    paths.py
    interfaces/
    adapters/
    vendor/
    contracts/
    doctor/
    pipeline/
    stores/
    inference/
    observability/
    extraction/
    classification/
    archive/
    retrieval/
    nlp/
    identity/
    graph/
    domain_artifacts/
    query/
    reporting/
    security/
    evaluation/
    quality/
  tests/
  docs/
    design/spec.md
    impl/plan.md
    impl/current/
    guide/
  scripts/shared/common.sh
```

`configs/` holds versioned operator profiles and policies; `ontology/` holds Turtle and SHACL assets;
`src/arxiv_int/vendor/` holds attributed small extractions from other repositories under the reuse
decision rule below. Every directory arrives with the capability that needs it, not in advance.

Custom Python is orchestration and domain policy, not reimplementation of Tika, Docling, OCR,
ParadeDB, pgvector, AGE, DuckDB, PyArrow, or model runtimes. Production modules remain typed and
cohesive; CLI parsing does not own pipeline behavior.

## Configuration and multi-SSD paths

Configuration precedence is:

```text
explicit CLI option > process environment > .env > documented safe default
```

`.env.example` is committed and `.env` is ignored. Compose is always invoked with an explicit
project directory and `--env-file`, so copying the checkout to another disk does not change path
resolution. `make config` renders redacted application configuration and runs
`docker compose config --environment`. No committed file carries a machine-specific absolute path:
`.env.example` describes each root by the storage class it needs and leaves every value to the
operator's `.env`.

### Operator roots

The operator configures three roots, one per job:

| Root            | Holds                                                                              | Access             |
| --------------- | ---------------------------------------------------------------------------------- | ------------------ |
| `ARCHIVE_DIR`   | The source silos: the operator's own files, untouched                              | Read-only          |
| `RESULTS_DIR`   | Everything the pipeline produces: normalized datasets, runs, logs, reports, proofs  | Read-write         |
| `PGDATA_DIR`    | The one PostgreSQL data directory: canonical tables and every lexical, vector, and graph index | Postgres-owned |

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
| `source`        | Nobody; read-only     | Large sequential reads, one full pass per inventory | Any readable mount; rotational is acceptable                          | `ARCHIVE_DIR` silos, `PROOF_ARCHIVE_DIR`              |
| `bulk`          | Pipeline stages       | Large sequential writes, occasional full scans | Capacity first; rotational and non-native filesystems are acceptable    | `RESULTS_DIR` and its `normalized`, `runs`, `proofs`, `exports`, `quarantine` trees |
| `database`      | PostgreSQL only       | Small random reads and writes with ordered `fsync` | A filesystem PostgreSQL supports, real per-file ownership, exclusive use, SSD/NVMe strongly preferred | `PGDATA_DIR`, optional `PG_WAL_DIR`, optional tablespace roots |
| `scratch`       | Pipeline workers      | High-churn random writes, deleted after the stage | Fast local SSD/NVMe, bounded free space, no durability requirement     | `TMP_DIR`                                             |
| `model`         | Model runtimes        | Large random reads at load, then read-mostly | SSD/NVMe preferred; rotational multiplies model load latency               | `MODEL_CACHE_DIR`                                     |
| `service-state` | Local services        | Small random writes with file locking   | POSIX filesystem with real ownership; small; disposable but not rebuildable from the archive | `SERVICE_STATE_DIR`                       |

A class mismatch is a configuration finding, not a silent slowdown. `database` on a rotational device
or on a filesystem PostgreSQL does not support, `scratch` or `model` on a rotational device, and
`service-state` on a filesystem that cannot express ownership are each reported by name with the
variable to change. Only a `database` root that cannot take real ownership or exclusive use is a
refusal; the rest are warnings the operator may accept for a trial.

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
  `runs/<run-id>/reports/`, `runs/<run-id>/artifacts/`, and `exports/`, so the whole output tree
  stays deletable and rebuildable in one place.
- **Mutable service state is separable, and is the one root worth adding.** Grafana's own database
  and plugins, a Prometheus TSDB, and AGE Viewer state are written by services rather than by the
  pipeline, need real file ownership and locking, and are not rebuildable from the archive the way
  `RESULTS_DIR` is. They live under `SERVICE_STATE_DIR`, which defaults to `${RESULTS_DIR}/services`
  and must be pointed at a `service-state`-capable path when the results root cannot express
  ownership. Dashboard and datasource definitions stay provisioned from `docker/grafana/` in the
  repository, so this root holds runtime state only.

### Variables

| Variable                                                | Purpose                                              | Storage class   | Default policy                                                 |
| ------------------------------------------------------- | ---------------------------------------------------- | --------------- | -------------------------------------------------------------- |
| `ARCHIVE_DIR`                                           | Declared immutable input silos; bind-mounted read-only | `source`      | Required for corpus stages; one path, or several named roots |
| `RESULTS_DIR`                                           | Single pipeline output root                          | `bulk`          | Required for corpus stages; must not be inside the archive or the checkout |
| `PGDATA_DIR`                                            | PostgreSQL data and index directory on fast local SSD/NVMe | `database` | Required for services                                     |
| `PROOF_ARCHIVE_DIR`                                     | Operator-provided read-only archive silo for proof runs | `source`     | Required only by provided-archive proof tasks                |
| `DEV_ARCHIVE_DIR`                                       | Read-only archive used by the development loop       | `source`        | `${PROOF_ARCHIVE_DIR}`; never read by `make ci`                |
| `DEV_RESULTS_DIR`                                       | Output root for bounded development-loop runs        | `bulk`          | `${RESULTS_DIR}/dev`; keeps development slices out of published generations |
| `RUNS_DIR`                                              | Run journals, logs, reports, checkpoints             | `bulk`          | `${RESULTS_DIR}/runs`                                          |
| `SERVICE_STATE_DIR`                                     | Grafana, Prometheus, and AGE Viewer runtime state    | `service-state` | `${RESULTS_DIR}/services`; must be moved when that path cannot express ownership |
| `MODEL_CACHE_DIR`                                       | Hugging Face/model cache                             | `model`         | `${RESULTS_DIR}/models`                                        |
| `TMP_DIR`                                               | Bounded extraction and sort scratch                  | `scratch`       | `${RESULTS_DIR}/tmp`                                           |
| `PG_WAL_DIR`                                            | Write-ahead log on a second `database` device        | `database`      | Unset; the WAL stays inside `PGDATA_DIR`                       |
| `PG_TABLESPACE_<NAME>_DIR`                              | Optional named tablespace on a second `database` device | `database`   | Unset; every relation stays inside `PGDATA_DIR`                |
| `DATABASE_URL`                                          | Host-side application connection                     | --              | Local-only default assembled from non-secret fields            |
| `POSTGRES_PASSWORD`                                     | Database secret                                      | --              | No committed value; doctor rejects placeholder in non-dev mode |
| `OLLAMA_BASE_URL`                                       | Host Ollama endpoint                                 | --              | `http://127.0.0.1:11434` for host CLI                          |
| `INFERENCE_BACKEND`                                     | `ollama` or `vllm`                                   | --              | `ollama`                                                       |
| `EMBEDDING_MODEL`, `GENERATION_MODEL`, `RERANK_MODEL`   | Model identities                                     | --              | Pinned by an evaluated profile, not silently floated           |
| `DATA_DIR`                                              | Repository-local root for developer tooling only     | --              | `.data`, resolved from the project root                        |
| `LOG_LEVEL`, `LOG_FORMAT`, `PROGRESS_INTERVAL_SEC`      | Operator feedback                                    | --              | `INFO`, console plus JSONL, 30 seconds                         |
| `PIPELINE_WORKERS`, `BATCH_SIZE`, `GPU_MAX_CONCURRENCY` | Resource bounds                                      | --              | Auto-detected conservative values; GPU concurrency `1`         |

Path preflight must resolve symlinks, prove source and destinations are distinct, verify the archive
mount is readable, verify outputs are writable, record filesystem type, device identifier, and
rotational flag, classify each path against its required storage class, estimate free space, and
refuse dangerous roots such as `/`. Docker receives absolute bind-mount sources, even when `.env`
contains paths relative to the project root. The recorded filesystem type, device id, rotational
flag, and storage class of every root enter the run manifest, so a slow or unsafe placement is
visible in the evidence rather than inferred later from timings.

### Source silos

The archive input is a declared set of one or more read-only source roots. Each root has a stable,
operator-declared silo id and an absolute path; a single configured path is the one-silo case and
carries a default id. The silo id is part of source identity: every inventory row, document, path
event, quarantine record, classification row, and move-ledger entry stores its silo id together with
the root-relative path, so two silos may hold the same relative path without colliding and any
derived fact can name the silo it came from. Content identity remains the content hash, so the same
bytes found in two silos are one document with two source locations rather than two documents.
Silos may sit on different filesystems, and each is separately declared readable, forecast, and
counted; the archive-reorganization command operates on exactly one silo per plan.

### The results root

`RESULTS_DIR` is the single output root, so an operator can point one path at a spare disk, inspect
everything the system produced in one tree, and delete or archive that tree without touching the
source silos or the database. Its layout is fixed and documented:

```text
$RESULTS_DIR/
  normalized/   contract-versioned Parquet and Avro datasets: inventory, documents, spans, chunks,
                classifications, nlp, mentions, facts, linkage, embeddings, topics, domain-artifacts
  quarantine/   inputs that could not be processed, by reason
  runs/         one directory per run: journal, logs, manifests, telemetry, evaluation, reports
  proofs/       provided-archive proof bundles, by capability and proof id
  exports/      operator-requested portable outputs, including rendered graphs and reports
  dev/          bounded development-loop output, unless DEV_RESULTS_DIR points elsewhere
  services/     local service runtime state, unless SERVICE_STATE_DIR points elsewhere
  models/       model cache, unless MODEL_CACHE_DIR points elsewhere
  tmp/          bounded scratch, unless TMP_DIR points elsewhere
```

Everything under `RESULTS_DIR` is rebuildable from the archive plus contracts and code, given enough
time; nothing under it is the only copy of an operator's file. The four subtrees with their own
variables are the ones whose storage class differs from `bulk`: scratch and model cache want a fast
device, service state wants real ownership, and development output wants separation from published
generations. Pointing them elsewhere is the expected configuration on a workstation whose results
disk is large and slow.

`PGDATA_DIR` is separate because PostgreSQL owns that directory exclusively and its failure and
backup semantics differ from a lake of files. Keeping indexes inside `PGDATA_DIR` rather than in a
fourth root is deliberate: ParadeDB, pgvector, and AGE are all PostgreSQL extensions, so their
storage is part of the database.

`DATA_DIR` is not part of this model. It is the repository's own convention for developer tooling --
linter, type-checker, and test caches, and local records produced by repository tasks -- and it
defaults to `.data` inside the checkout. Corpus-scale output never goes there, and preflight refuses
a `RESULTS_DIR` or `PGDATA_DIR` that resolves inside the checkout unless the operator states that
intent for a small local trial.

`PROOF_ARCHIVE_DIR` is never committed as a machine-specific value and may not overlap generated
proof data. Proof tasks retain source manifests and hashes, not corpus contents, in repository
documentation. A bounded disposable copy under the configured data root may be used for addition,
modification, and removal drills; the provided archive itself remains read-only.

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

- point `ARCHIVE_DIR` and `PROOF_ARCHIVE_DIR` at the real archive silo and leave `DEV_ARCHIVE_DIR` to
  its default, so the development loop, forecasts, and proof runs read one declared read-only source;
- point `RESULTS_DIR` at the bulk output disk and let `RUNS_DIR`, `exports/`, `proofs/`, and
  `DEV_RESULTS_DIR` derive from it, so every run result of either kind lands in one deletable tree;
- point `PGDATA_DIR`, `TMP_DIR`, and `MODEL_CACHE_DIR` at the fast disk when the results disk is
  rotational or not a PostgreSQL-supported filesystem, and point `SERVICE_STATE_DIR` there too when
  the results disk cannot express file ownership;
- keep `DATA_DIR` at its `.data` default inside the checkout; it is developer tooling state, never a
  corpus or results location.

The preflight reports each of these placements with its measured device and filesystem, so the
difference between a deliberate trial on a slow disk and an accidental one is visible before a long
run starts.

## Docker and local-service topology

Compose profiles keep optional services out of the default footprint:

| Profile         | Services                                      | Notes                                                                                   |
| --------------- | --------------------------------------------- | --------------------------------------------------------------------------------------- |
| `core`          | project-derived ParadeDB/PostgreSQL           | Pinned image, healthcheck, persistent bind mount, localhost port only                   |
| `graph`         | core image with AGE enabled, AGE Viewer       | Same PostgreSQL service; AGE projection remains disposable                              |
| `ui`            | Grafana and provisioned PostgreSQL datasource | Dashboards, pipeline progress, topic/entity/fact tables, node graph panels              |
| `observability` | Prometheus exporter and optional cAdvisor     | No corpus content in labels or metrics                                                  |
| `vllm`          | pinned `vllm/vllm-openai` image               | Optional NVIDIA runtime; model cache bind mount; sequential with other GPU-heavy stages |

Ollama is deliberately not in Compose. It is installed and managed as the host system service. A
Linux container reaches it through a documented host-gateway alias only when a containerized worker
needs inference. The host CLI uses loopback directly. The default does not expose Ollama or
PostgreSQL beyond localhost.

Every service mount follows the storage classes above. The database service bind-mounts `PGDATA_DIR`
read-write and nothing else; when `PG_WAL_DIR` or a named tablespace root is configured, each is a
separate bind mount that the service refuses to start without. Grafana, Prometheus, and AGE Viewer
bind-mount only their own subdirectory of `SERVICE_STATE_DIR` read-write, with dashboard, datasource,
and scrape definitions provisioned read-only from `docker/`. Services that read pipeline output mount
`RESULTS_DIR` read-only; the vLLM profile mounts `MODEL_CACHE_DIR`; the archive silos are mounted
read-only or not at all. Compose receives absolute host paths resolved by the same preflight the CLI
uses, and a container whose mount fails its storage-class check does not start.

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

ODCS `3.1.0` YAML under `contracts/` is the authoritative description of datasets, fields,
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
`extraction`, and `evaluation_item` semantics. Source-specific mappings translate physical fields to
these concepts without changing pipeline code.

### Generation

Prefer Data Contract CLI for ODCS linting, generic SQL/Avro/JSON Schema export, changelogs, breaking
checks, and live Postgres tests. Adapt the small MIT-licensed `fl-op` generator/evolution seams only
for gaps that generic tooling cannot express:

- PostgreSQL partition, constraint, index, and extension DDL;
- ParadeDB index/tokenizer definitions;
- pgvector dimensions and index candidates;
- AGE label/edge projection SQL;
- Arrow/Parquet descriptors with field metadata;
- Pydantic models or JSON Schema for structured LLM outputs;
- canonical semantic fingerprint and provenance fields.

Generated outputs are deterministic and committed when needed for review. `make contracts-check`
regenerates into a temporary directory and fails on drift.

### Evolution and migrations

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
tested in both required directions. A migration tool such as dbmate owns ordered SQL migrations and
`schema.sql`; generated baseline DDL does not auto-migrate an existing database. Destructive or
table-rewriting migrations require an explicit human-approved plan, backup, free-space check, and
rollback/rebuild path.

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

| Schema     | Canonical contents                                                                                      |
| ---------- | ------------------------------------------------------------------------------------------------------- |
| `ctl`      | Contracts, migrations, runs, forecasts, shards, leases, checkpoints, errors, artifact lineage/registry |
| `corpus`   | Documents, editions, path events, spans, chunks, language, quality, duplicate and classification data   |
| `search`   | Search projection rows, embedding profiles, selected embeddings, topic assignments                      |
| `kg`       | Canonical objects, aliases, mentions, facts, qualifiers, review state, source evidence                  |
| `ontology` | Terms, classes, predicates, mappings, axioms, ontology versions                                         |
| `eval`     | Frozen gold items, query sets, labels, run metrics, paired comparisons                                  |

Large tables are declaratively partitioned by a stable hash bucket and, where useful, corpus or
contract version. Partitions must be large enough to avoid catalog explosion. Text and vector
columns are kept out of narrow control tables. Bulk loads use binary `COPY` into staging/partitions,
validate counts and checksums, then attach or merge transactionally.

### Canonical object and fact model

An object has a stable internal id, type, preferred label, normalized attributes, lifecycle/review
state, resolution cluster, first/last evidence, and provenance. Aliases and mentions remain separate
so a merge can be reversed.

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
state merely because it parsed. Equipment and supplier lists are queries over typed objects and
accepted or explicitly included proposed facts, with citations and confidence visible.

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
| `ontology`     | Vocabulary, class/predicate mappings, SHACL/OWL-compatible checks           | Versioned ontology assets     |
| `graph`        | Build and validate AGE projection                                           | Active versioned graph        |
| `domain-artifacts` | Relationship, BOM, supply-chain, and invoice/payment projections        | Registered investigation artifacts |
| `evaluate`     | Retrieval, extraction, linkage, graph, cost, and resource metrics           | Immutable evaluation bundle   |
| `report`       | Coverage, failures, topics, objects, facts, registered domain artifacts     | HTML/JSON/Parquet reports     |

The end-to-end command runs the dependency closure, not a hardcoded shell chain.

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
different device. When the target is on the same filesystem, an opt-in hardlink placement gives the
same tree without duplicating bytes, which is safe only because both paths then reference the same
immutable content. `move` exists for operators who want the archive itself reorganized and accept
that cost; it stays same-filesystem and atomic, and it is refused without a verified backup. Both
modes read the same classification mapping, write the same ledger, and support the same resume,
verification, and lookup behavior.

Physical directories follow the primary class's ancestor path. Each segment combines a reversible
safe class token with a short meaningful ASCII slug, is capped at a configured byte length, and is
checked together with the full destination against filesystem component and path limits. Dedicated
ASCII directories such as `_unclassified` and `_unreadable` hold exceptional outcomes that can be
safely placed. Complex facets and secondary classes stay in metadata. The command never overwrites a
destination, never follows a link outside the selected root, never relocates virtual members
independently of their container, and refuses stale, colliding, overlong, or incompletely accounted
plans. A `move` plan additionally refuses cross-device entries; a `copy` plan expects a different
device and refuses a target that overlaps the silo, the results root, or the database directory.

Before the first placement, the command seals an append-only ledger containing inventory and
document/content ids, silo id, mode, original and proposed destination relative paths, action order,
available hashes, classification and plan ids, placed/blocked status, and rollback information. It
journals each atomic rename or verified copy and can resume or reverse only operations proven by that
ledger. A copied file is verified against its recorded hash before the entry is marked complete, and
reversing a `copy` plan removes only target files the ledger proves this plan created. Original
provenance is never rewritten to contain only the new path, and in `copy` mode the original location
remains the source of record while the target path is recorded as an additional location. The
`arxiv-int archive locate DOCUMENT_ID` command resolves the initial, run-time, and current known
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
pinned in an evaluated profile. GPU-heavy embedding, reranking, extraction, and generation stages
run sequentially by default on 16 GB VRAM. The scheduler checks free VRAM, unloads an Ollama model
when policy permits, and records load time, throughput, peak VRAM, failures, and fallback use.

LLM outputs use generated JSON Schema/Pydantic validation, temperature near zero where supported,
bounded repair, explicit refusal/malformed statuses, and source-evidence requirements. Prompt text,
model id/digest, sampling settings, and output schema version are part of provenance.

## CLI and Make interface

The installed command is `arxiv-int`. Representative commands are:

```text
arxiv-int doctor
arxiv-int config show --redact
arxiv-int contracts lint|generate|diff|check|test
arxiv-int services status
arxiv-int pipeline forecast --archive-dir PATH [--from STAGE] [--to STAGE]
arxiv-int pipeline run --archive-dir PATH --results-dir PATH [--from STAGE] [--to STAGE]
arxiv-int pipeline update --archive-dir PATH [--from STAGE] [--to STAGE]
arxiv-int pipeline rebuild --archive-dir PATH [--from STAGE] [--to STAGE]
arxiv-int pipeline invalidate STAGE [--document-id ID]
arxiv-int stage STAGE --archive-dir PATH --results-dir PATH [stage options]
arxiv-int artifacts prune --stale [--apply --plan PLAN_ID]
arxiv-int archive reorganize --classification ID [--apply --plan PLAN_ID]
arxiv-int archive locate DOCUMENT_ID
arxiv-int inspect DATASET|RUN|latest [--limit N]
arxiv-int run status RUN_ID
arxiv-int run resume RUN_ID
arxiv-int run artifacts RUN_ID
arxiv-int search lexical|semantic|hybrid QUERY
arxiv-int graph rebuild|check|query
arxiv-int report build RUN_ID
```

Standard Make targets are thin, documented wrappers:

```text
make help                  make bootstrap             make doctor
make config                make contracts             make contracts-gen
make contracts-evolution  make services-up           make services-down
make services-status      make logs                   make forecast
make dev-link              make dev-stage STAGE=...    make dev-check
make pipeline              make update                 make proof CAPABILITY=...
make stage STAGE=...       make resume RUN_ID=...     make search QUERY=...
make graph-up              make ui-up                  make eval
make test                  make integration-test      make ci
make backup                make restore-check
```

The primary path contract works in both forms:

```bash
make pipeline ARCHIVE_DIR=/mnt/archive RESULTS_DIR=/mnt/results

arxiv-int pipeline run \
  --archive-dir /mnt/archive \
  --results-dir /mnt/results
```

Command-line values override `.env`; resolved non-secret values and path device ids are written into
the run manifest. Make never embeds machine-specific absolute paths.

## Development loop

A pipeline stage is built against fixtures but proven against files. The formats, encodings,
truncations, and failures that decide whether a stage is correct live in the operator's own archive,
so the moment a stage becomes runnable it must be runnable against real data and its output must be
readable without knowing a run id. This is a build-time convenience, not an acceptance path.

Three aliases are created from configuration and refreshed by `make dev-link`. They live under the
repository's `DATA_DIR`, which is already ignored by Git, so a stable name is available on every
machine while the machine-specific path stays in `.env`:

| Alias                     | Points at                                     | Answers                                    |
| ------------------------- | --------------------------------------------- | ------------------------------------------ |
| `$DATA_DIR/dev/archive`   | `DEV_ARCHIVE_DIR`, read-only                  | where is the real archive on this machine  |
| `$DATA_DIR/dev/results`   | `DEV_RESULTS_DIR`                             | where did the output go                    |
| `$DATA_DIR/dev/latest`    | the most recent run directory under `RUNS_DIR` | what did the step I just ran produce       |

`DEV_ARCHIVE_DIR` defaults to `PROOF_ARCHIVE_DIR`, so one configured read-only archive serves both the
development loop and proof runs while remaining separately overridable. `DEV_RESULTS_DIR` defaults to
`${RESULTS_DIR}/dev`, so bounded development slices stay on the operator's configured output disk and
out of the published generations under `$RESULTS_DIR/normalized/`, and deleting the development tree
never touches a proof bundle or an accepted generation. Every published dataset under
`$RESULTS_DIR/normalized/` additionally exposes a `current` pointer to its active generation, so a
reader never has to know the newest generation id. A broken or missing alias reports the variable to
set rather than falling back to a guessed path.

`make dev-stage STAGE=...` runs one stage against the development archive over a bounded slice, so the
loop costs seconds to minutes rather than a full pass, and then prints the artifact summary:
row and byte counts, contract conformance, partitions written, sampled rows with their source anchors,
quarantine reasons, and the failure taxonomy. `arxiv-int inspect` prints the same summary for any
dataset, run, or the `latest` alias without recomputing anything, and `make dev-check` runs the
opt-in real-archive lane for every stage that already exists.

The real-archive lane is deliberately outside the deterministic gate. `make ci` never reads the
archive, never depends on a configured `DEV_ARCHIVE_DIR`, and stays reproducible on a machine that has
no corpus; when no development archive is configured, the lane skips with an actionable message and
reports that as its result. Development-loop output is local evidence only: it is not a proof bundle,
it does not satisfy a provided-archive proof task, no stage is complete because its development run
looked reasonable, and no corpus content, sample row, or machine-specific path from this loop enters
Git. The loop never writes to the development archive.

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
rename updates path events without repeating content analysis. Removed content creates tombstones;
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
- peak temporary, WAL, staging, rebuild, rollback, and archive-reorganization target space, without
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
configured WAL or tablespace root, any configured export path, and any archive-reorganization copy
target. Roots that share one device are budgeted once and reported together, and the storage class
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
duplicate claims, contradictions, and evidence spans. Lists of equipment and suppliers include the
query definition, coverage, review state, and source citations.

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

- `relationship-map`: typed relationships among designs, documents, revisions, people,
  organizations, equipment, materials, contracts, and events;
- `bill-of-materials`: assembly/component/material hierarchies with part numbers, quantities,
  units, alternatives, revision/effectivity, and unresolved references;
- `supply-chain`: supplier, manufacturer, customer, location, order, shipment, invoice, and payment
  relationships, including direction, time, and status where the source states them;
- `invoice-payment`: invoice lines and totals, currencies, due dates, payment events, allocations,
  and evidence-backed matched, partial, duplicate, disputed, or unmatched states.

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

## Reuse map

| Source         | Reuse                                                                                                                                                                                                                             | Do not carry forward                                                                                               |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `agent-py`     | Template structure, project rename, Python/uv/Make gates, typed CLI seam, doc-link and spec-plan integrity, AGENTS policy                                                                                                         | Starter identity and example-only behavior                                                                         |
| `fl-op`        | ODCS registry, canonical model, namespaced generation hints, deterministic multi-format generators, fingerprints, semantic mapping, reviewed evolution baselines, compatibility tests                                             | Fleet domain, optimization solver, ES generator as an active target                                                |
| `selfsuvis`    | Layered env/path helper, cross-filesystem cache handling, preflight/resource checks, queued logging, step timing, partial results, GPU/model lifecycle patterns                                                                   | Video/IoT pipeline, Qdrant production dependency, monolithic 35-step orchestration                                 |
| `loc-lm-bench` | Citation-preserving ingestion where applicable, conflict/dedup audit, Splink linkage seam, retrieval metrics and paired verdicts, local backend abstraction, model fit/VRAM telemetry, ontology/fact gates, immutable run bundles | Ukrainian-only defaults, robotics lanes, FAISS as production store, the full benchmark CLI inside the core package |
| Upstream OSS   | Tika, Docling, OCRmyPDF/Tesseract, PyArrow, DuckDB, Data Contract CLI, ParadeDB, pgvector, AGE, rdflib/pySHACL, Ollama/vLLM                                                                                                       | Thin local rewrites of their core engines                                                                          |

### Reuse decision rule

Reuse from `volod/*` and other repositories is smallest-footprint-first, not dependency-first. A new
distribution dependency is a permanent installation, resolution, and upgrade cost, so it must be
earned by the size of the reused surface rather than assumed. The reused seam is measured first, then
one of two forms is chosen:

| Reused surface                                                                                                                                          | Form                                                                                                                                                     |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Small and self-contained: at most about 400 source lines across a few cohesive modules, adding no transitive package, and not expected to track upstream | **Vendor it.** Copy the extraction into `src/arxiv_int/vendor/<source>/`, adapt it to project typing and style, and record source repository, revision, licence, and local changes in `THIRD_PARTY.md`. |
| Large, or dependent on the upstream's own packages, or valuable mainly because it keeps receiving upstream fixes                                         | **Depend on it.** Prefer a released package pinned by version; a commit-pinned VCS revision is acceptable while a release is being established.          |

A vendored extraction is a fork by intent: it carries the upstream licence and revision, is covered
by project tests, and is refreshed only by a deliberate re-extraction. It is never a silent divergence
and never an unattributed copy. Copying an entire application, vendoring an engine that upstream
maintains as a product (Tika, ParadeDB, Splink, rdflib and similar), or maintaining a parallel
implementation of behavior the project already owns is not reuse in either form.

When the dependency form is chosen, upstream repositories must expose cohesive importable modules and
optional dependency groups so `arxiv-int` installs only the reused seam, and portable locks must not
rely on sibling checkout paths. Before adding a dependency, record its licence, maintainer/revision,
reused API, transitive packages, wheel/download and installed sizes, native-build requirements, and
the pipeline extras that activate it. PyTorch, CUDA toolchains, model runtimes, graph/UI stacks, and
similarly heavy packages never enter the core dependency closure unless the core actually executes
them. A heavy upstream package must first split or expose a lightweight subpackage/extra; otherwise
the integration is resolved by vendoring the small seam or by deferral.

Deciding, measuring, and testing this belongs to the implementing agent: it inventories the seam,
measures size and transitive cost, and proves the choice with lock, import-isolation, clean-install,
size, licence, and behavioral-equivalence tests. Only a change to a repository the project does not
own requires human authorization. In that case the agent produces the change request as a reviewable
artifact for the owning repository -- the module boundary, the interface contract, the packaging
change, and the tests it needs -- and continues here with the vendored or deferred form until that
request is authorized and released. Waiting on an external repository never blocks this project's
critical path. A valid negative result is to defer reuse and keep an existing local seam.

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
- equipment and supplier report cases with evidence and completeness review;
- design relationship, BOM, supply-chain, invoice, and payment cases with reviewed edges,
  quantities, units, totals, allocations, conflicts, and valid empty results.

Gold creation and threshold setting use separate tuning and final partitions. LLM-drafted items do
not become scoring truth without review.

### Provided-archive proof runs

`PROOF_ARCHIVE_DIR` is the operator-provided file-silo archive used for integration proof. After the
required implementation tasks for each artifact-producing capability group, a final `RUN NEEDED`
task executes every then-usable stage in that group against this archive. A later behavior change
that alters a stage or its inputs must regenerate the impacted proof before that change is complete;
an older bundle remains historical evidence but is marked stale by fingerprint.

| Capability group | Proof scope |
| --- | --- |
| `corpus-foundation` | `inventory`, `extract`, `normalize`, `dedupe`, and `chunk` artifacts |
| `pipeline-control` | forecast, cache hit, resume, delta update, invalidation, rebuild, and prune planning |
| `archive-classification` | classification mapping and archive-reorganization dry-run/lookup |
| `lexical-retrieval` | lexical load, index manifest, queries, filters, and source citations |
| `semantic-retrieval` | selected embeddings/vector load and paired verdict, when the branch is usable |
| `russian-nlp` | language, morphology, terminology, and mention artifacts |
| `knowledge-extraction` | proposed facts, validation, conflicts, and evidence links |
| `identity-ontology-graph` | clusters, ontology validation, graph/fallback exports, and parity checks |
| `domain-investigation-artifacts` | relationship, BOM, supply-chain, invoice/payment, and registry outputs |
| `discovery-visualization` | topics, search/report scenarios, exports, and configured local views |
| `evaluation-evidence` | `evaluate`, `report`, and an end-to-end proof index over all prior bundles |

Each task first runs the forecast and refuses a blocked scope. It records a proof bundle under
`$RUNS_DIR/proofs/<capability-id>/<proof-id>/` containing the redacted command/configuration,
source-manifest hash, code/contract/dependency/model fingerprints, forecast, stage and shard ledger,
artifact registry with checksums, validator results, errors/quarantines, resource/timing metrics, and
an overall verdict. The proof reruns the unchanged scope and demonstrates that heavy stages are cache
hits. Incremental-control proof uses a bounded disposable copy or overlay under the data root to test
add/change/rename/remove cases and never mutates `PROOF_ARCHIVE_DIR`.

A required usable stage passes only with validated artifacts or a contract-defined valid empty
result. Failure, missing evidence, or resource refusal keeps its proof task open. An optional branch
may record `not-selected` only with its measured negative verdict and working fallback. Repository
current-state documentation records proof ids, fingerprints, artifact paths, validation summaries,
and results, but never copies private source content or machine-specific archive paths into Git.

### Required acceptance gates

| Area              | Gate                                                                                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Fresh setup       | From a copied repo and edited `.env`, `make bootstrap`, `make doctor`, `make services-up`, a smoke pipeline, and `make ci` succeed without paths tied to the original disk.                      |
| Contracts         | ODCS lint, generation drift, Avro round-trip/compatibility, evolution policy, migration status, and live Postgres schema tests pass.                                                             |
| Idempotency       | Re-running an unchanged successful shard writes no duplicate canonical rows or artifacts and reports a cache hit; interrupted stages resume from completed shards.                               |
| Incremental state | Added/changed/renamed/removed sources and stage-owned implementation changes invalidate only their lineage closure; active views retract stale outputs and retain audit evidence.                 |
| Forecast          | Time/size ranges cite evidence, all target devices and peak scratch/rebuild needs are counted, and insufficient free space blocks before heavy allocation.                                        |
| Proof bundles     | Every usable artifact-producing stage group has a current provided-archive proof whose outputs, checksums, validators, cache-hit rerun, and fingerprint are complete.                              |
| Provenance        | Every sampled search result, mention, fact, topic assignment, graph edge, and report row resolves to source evidence and a complete transformation fingerprint.                                  |
| Extraction        | Per-format text/table/anchor coverage and quarantine reasons meet thresholds declared before the full run.                                                                                       |
| Classification    | Hierarchical accuracy, calibration, exceptional outcomes, reproducibility, and path-ledger safety gates pass; uncertain files are not forced into ordinary classes.                              |
| Lexical retrieval | Russian BM25 recall@k, MRR, evidence intactness, p95 latency, and index amplification pass on the final query set.                                                                               |
| Vector/hybrid     | Candidate must beat or complement lexical retrieval with a paired confidence interval and remain within build, storage, latency, and VRAM/RAM budgets; otherwise lexical-only is a valid result. |
| Entity resolution | Precision at the proposed auto-merge threshold meets the predeclared high-precision target; uncertain pairs remain unmerged.                                                                     |
| Facts             | Per-type precision/recall and citation-span validity meet declared thresholds; invalid structured output and ontology violations are accounted for.                                              |
| Graph             | Counts reconcile with relational projection inputs; sampled SQL/Cypher paths agree; rebuild and backup/restore tests pass.                                                                       |
| Domain artifacts  | BOM, relationship, supply-chain, and invoice/payment tables and graphs agree with reviewed facts, evidence links, arithmetic, and registry status.                                                |
| Scale             | Two staged pilots complete within measured disk/RAM/VRAM envelopes with no unbounded queue, transaction, temp, or WAL growth.                                                                    |
| Privacy           | Network-denied integration run succeeds after required images/models are present; logs and reports contain no secrets or unintended corpus content.                                              |

Each comparison ends in `adopt`, `retain baseline`, or `inconclusive`; a negative result is valid
and must not be hidden by choosing a convenient threshold.

## Operations, backup, and security

The archive mount is read-only for every service and pipeline stage. Only the explicit host-side
archive-reorganization command may request write access, only in `move` mode, and only with an
accepted dry-run plan, a sealed ledger, and a recoverable backup or equivalent snapshot; its `copy`
mode writes solely into the declared target root. Service ports bind to loopback.
Database roles separate migration, pipeline writes, read-only UI, and backup. Secrets live in `.env`
or operator-provided secret files, never generated artifacts or logs. Containers run non-root where
upstream images permit, have bounded resources, and receive only required mounts.

Backups include:

- ODCS contracts, migrations, configuration template, and code in version control;
- normalized manifests and portable datasets through filesystem snapshots or another disk;
- classification snapshots and archive move ledgers needed to locate or reverse moved sources;
- PostgreSQL logical/physical backup appropriate to the pinned extension versions, covering
  `PGDATA_DIR` together with any configured `PG_WAL_DIR` and named tablespace roots as one unit,
  because a cluster is not recoverable from a subset of them;
- `SERVICE_STATE_DIR` only where a service holds state the repository does not provision;
- extension/image/model digests and a restore runbook;
- restore verification that rebuilds or validates ParadeDB and AGE projections.

Because Community ParadeDB does not promise enterprise HA/read-replica support, local recovery is
based on tested backup plus projection rebuild, not an assumed replica.

## Delivery strategy

| Phase                       | Outcome                                                          | Capability span                                          | Exit signal                                                     |
| --------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------- |
| 0 - Foundation              | Personalized repo, portable paths, development loop, contracts, one database image | `project-foundation` through `canonical-store` | Fresh-copy service and contract smoke passes            |
| 1 - Local evidence seams    | Local inference adapters and replayable evaluation fixtures      | `local-inference`, `evaluation-foundation`               | Provider and metric conformance tests pass                      |
| 2 - Corpus substrate        | Rebuildable lake, restartable stages, classification and path map | `corpus-foundation` through `archive-classification`     | Corpus/control/classification proof bundles pass                 |
| 3 - Retrieval and NLP       | Russian lexical baseline, selected vectors, mentions             | `lexical-retrieval` through `russian-nlp`                | Retrieval and NLP proof bundles pass or retain a valid fallback |
| 4 - Knowledge and discovery | Facts, identity, domain artifacts, graph, topics, reports, UI    | `knowledge-extraction` through `discovery-visualization` | Knowledge through discovery proof bundles pass                  |
| 5 - Evidence and operations | Comparative scale evidence and recovery                          | `evaluation-evidence`, `operational-recovery`            | End-to-end proof, staged pilot, and restore drill support a verdict |

The critical path is:

```text
project foundation
  -> portable runtime
  -> development loop
  -> contract governance
  -> canonical store
  -> local inference and evaluation foundation
  -> corpus foundation
  -> pipeline control
  -> archive classification
  -> lexical retrieval
  -> Russian NLP
  -> knowledge extraction
  -> identity/ontology/graph
  -> domain investigation artifacts
  -> discovery and visualization
  -> evaluation and operational recovery
```

Semantic retrieval, vLLM, and physical archive reorganization are evaluated or authorized branches.
They must not block a useful lexical, CPU-first system when their valid result is `retain baseline`
or `do not move`.

## Capability Registry

Every capability appears once. Status is `planned` until current-state documentation and acceptance
evidence exist. Registry order is the implementation line used by `plan.md`.

| #   | Capability                | Status  | How it is evaluated                                                                          | Implementation                                               |
| --- | ------------------------- | ------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 1   | `project-foundation`      | planned | Fresh copy, rename, locked bootstrap, CLI identity, docs integrity, and CI pass              | `plan.md#project-foundation----project-foundation`           |
| 2   | `portable-runtime`        | planned | Multi-SSD path and Compose profile smoke tests pass from two checkout locations              | `plan.md#portable-runtime----portable-runtime`               |
| 3   | `development-loop`        | planned | Stable aliases resolve from two checkouts and an opt-in real-archive stage lane runs outside the deterministic gate | `plan.md#development-loop----development-loop`               |
| 4   | `contract-governance`     | planned | ODCS lint/generation/evolution/Avro/migration/live-store gates pass                          | `plan.md#contract-governance----contract-governance`         |
| 5   | `canonical-store`         | planned | ParadeDB/pgvector/AGE compatibility, schema, backup, restore, and projection checks pass     | `plan.md#canonical-store----canonical-store`                 |
| 6   | `local-inference`         | planned | Ollama/vLLM conformance, structured outputs, model-fit, and local-only endpoint gates pass   | `plan.md#local-inference----local-inference`                 |
| 7   | `evaluation-foundation`   | planned | Frozen fixtures, replayable metrics, split guards, and paired verdict utilities pass         | `plan.md#evaluation-foundation----evaluation-foundation`     |
| 8   | `corpus-foundation`       | planned | Representative inventory, extraction, normalization, dedupe, and chunk gold sets pass        | `plan.md#corpus-foundation----corpus-foundation`             |
| 9   | `pipeline-control`        | planned | Sharded stage, resume, retry, invalidation, idempotency, and progress tests pass             | `plan.md#pipeline-control----pipeline-control`               |
| 10  | `archive-classification`  | planned | Hierarchical gold labels, calibrated exceptions, path safety, resume, rollback, and lookup pass | `plan.md#archive-classification----archive-classification`   |
| 11  | `lexical-retrieval`       | planned | Held-out Russian relevance, latency, index size, and rebuild gates pass                      | `plan.md#lexical-retrieval----lexical-retrieval`             |
| 12  | `semantic-retrieval`      | planned | Selected-tier vector and hybrid candidates receive paired adopt/retain verdicts              | `plan.md#semantic-retrieval----semantic-retrieval`           |
| 13  | `russian-nlp`             | planned | Language, morphology, terminology, and NER metrics pass per type                             | `plan.md#russian-nlp----russian-nlp`                         |
| 14  | `knowledge-extraction`    | planned | Structured extraction, evidence, fact quality, and contradiction gates pass                  | `plan.md#knowledge-extraction----knowledge-extraction`       |
| 15  | `identity-ontology-graph` | planned | Linkage, ontology, SQL/Cypher parity, rebuild, and bounded traversal gates pass              | `plan.md#identity-ontology-graph----identity-ontology-graph` |
| 16  | `domain-investigation-artifacts` | planned | Reviewed BOM, relationship, supply-chain, invoice/payment, render, and registry gates pass | `plan.md#domain-investigation-artifacts----domain-investigation-artifacts` |
| 17  | `discovery-visualization` | planned | Topic stability plus operator completion of search, graph, equipment, and supplier scenarios | `plan.md#discovery-visualization----discovery-visualization` |
| 18  | `evaluation-evidence`     | planned | Provenance audit and representative scale pilots produce readable, capacity-aware verdicts   | `plan.md#evaluation-evidence----evaluation-evidence`         |
| 19  | `operational-recovery`    | planned | Security checks, backup/restore drill, disk exhaustion, interruption, and runbook tests pass | `plan.md#operational-recovery----operational-recovery`       |

## Success criteria

The project succeeds when an operator can copy the repository to any suitable disk, copy
`.env.example` to `.env`, point it at separate archive, results, and PostgreSQL disks, start
the selected local services, and run one stage or the complete pipeline with continuous progress and
safe resume. Search, topics, objects, facts, ontologies, graphs, and equipment/supplier reports are
useful on a representative Russian corpus, carry source evidence, and can be rebuilt from open,
versioned contracts and normalized artifacts. Every source has a classified or explicit exceptional
outcome, optional physical moves remain traceable to the initial path, and every available BOM,
supply-chain, relationship, and invoice/payment view is registered with evidence and review state.
Unchanged inputs reuse validated heavy results, archive and implementation deltas update only their
lineage closure, stale derived data can be safely pruned or fully rebuilt, and forecasts refuse work
that cannot fit available storage. Every usable stage group has a current proof bundle from the
provided archive. The simpler PostgreSQL architecture remains in place only while measured quality,
scale, and recovery evidence supports it.
