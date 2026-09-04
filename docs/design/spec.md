# arxiv-int Project Specification

## Purpose

`arxiv-int` is a local-first Knowledge Discovery Platform for multi-terabyte, mostly
Russian-language document archives. Its Python distribution and import package are both `arxiv-int`
/ `arxiv_int`. The system inventories and normalizes an immutable archive, builds reproducible
lexical and selected semantic indexes, discovers topics, extracts and resolves entities and facts,
projects a knowledge graph, and supports local search, analysis, and visualization without requiring
document or prompt egress.

The target workstation has approximately 128 GB RAM and 16 GB GPU VRAM. Speed is secondary to
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

## Scope

The first production-shaped release includes:

- recursive archive inventory with stable identities, MIME/encoding/language detection, hashes,
  exact deduplication, and quarantines;
- text and metadata extraction from common office, text, email, archive, image, and PDF formats,
  with OCR/layout lanes selected by policy;
- normalized partitioned Parquet datasets and optional Avro object containers;
- Russian-aware BM25 search, metadata filters, snippets, and hybrid retrieval;
- selective multilingual embeddings, reranking, and local RAG;
- topic discovery, entity mentions, entity resolution, provenance-bearing fact extraction, ontology
  assets, and graph projection;
- PostgreSQL/ParadeDB as the canonical service; optional AGE, AGE Viewer, Grafana, and vLLM
  profiles;
- a typed Python CLI, standardized Make targets, Docker Compose, `.env.example`, progress logs, run
  manifests, and operator reports;
- deterministic unit/contract/integration tests plus representative corpus evaluations.

The initial release does not promise:

- embedding or LLM-processing every byte in a multi-terabyte archive;
- horizontal scale, high availability, or zero-downtime disaster failover on one workstation;
- automatic acceptance of LLM-generated facts or ontology axioms as truth;
- full Neo4j Graph Data Science parity, OpenSearch cluster parity, or Qdrant billion-vector parity;
- automatic destructive schema migration;
- lossless extraction from every proprietary, corrupt, encrypted, or handwriting-heavy document;
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
SSD A: ARCHIVE_DIR (read-only)         SSD B: NORMALIZED_DIR
          |                                      |
          v                                      v
 inventory -> extract -> normalize -> dedupe -> partitioned Parquet/Avro
                          |                       |
                          +---- run manifests ----+
                                      |
                                      v
SSD C: PGDATA_DIR          ParadeDB / PostgreSQL
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

The checkout can live on any fourth disk. No runtime path is derived from the checkout unless the
operator deliberately accepts a local default.

## Repository and package structure

The repository foundation was adapted from the pinned `agent-py` source above. Its active layout is:

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
  src/arxiv_int/
    cli.py
    config.py
    contracts/
    pipeline/
    stores/
    nlp/
    extraction/
    evaluation/
  tests/
  docs/
    design/spec.md
    impl/plan.md
    impl/current/
    guide/
  scripts/shared/common.sh
```

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
`docker compose config --environment`.

Required or prominent variables:

| Variable                                                | Purpose                                              | Default policy                                                 |
| ------------------------------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------- |
| `ARCHIVE_DIR`                                           | Immutable input tree; bind-mounted read-only         | Required for corpus stages                                     |
| `NORMALIZED_DIR`                                        | Parquet, Avro, extracted text, quarantine, manifests | Required; must not be inside source tree by accident           |
| `PGDATA_DIR`                                            | PostgreSQL data directory on fast local SSD/NVMe     | Required for services                                          |
| `RUNS_DIR`                                              | Run journals, logs, reports, checkpoints             | `${NORMALIZED_DIR}/runs`                                       |
| `MODEL_CACHE_DIR`                                       | Hugging Face/model cache                             | `${NORMALIZED_DIR}/models`                                     |
| `TMP_DIR`                                               | Bounded extraction and sort scratch                  | `${NORMALIZED_DIR}/tmp`                                        |
| `DATABASE_URL`                                          | Host-side application connection                     | Local-only default assembled from non-secret fields            |
| `POSTGRES_PASSWORD`                                     | Database secret                                      | No committed value; doctor rejects placeholder in non-dev mode |
| `OLLAMA_BASE_URL`                                       | Host Ollama endpoint                                 | `http://127.0.0.1:11434` for host CLI                          |
| `INFERENCE_BACKEND`                                     | `ollama` or `vllm`                                   | `ollama`                                                       |
| `EMBEDDING_MODEL`, `GENERATION_MODEL`, `RERANK_MODEL`   | Model identities                                     | Pinned by an evaluated profile, not silently floated           |
| `LOG_LEVEL`, `LOG_FORMAT`, `PROGRESS_INTERVAL_SEC`      | Operator feedback                                    | `INFO`, console plus JSONL, 30 seconds                         |
| `PIPELINE_WORKERS`, `BATCH_SIZE`, `GPU_MAX_CONCURRENCY` | Resource bounds                                      | Auto-detected conservative values; GPU concurrency `1`         |

Path preflight must resolve symlinks, prove source and destinations are distinct, verify the archive
mount is readable, verify outputs are writable, record filesystem/device identifiers, estimate free
space, and refuse dangerous roots such as `/`. Docker receives absolute bind-mount sources, even
when `.env` contains paths relative to the project root.

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

`NORMALIZED_DIR` is organized by contract id/version and stable partitions, never by an ephemeral
checkout path:

```text
normalized/
  inventory/contract_version=.../scan_id=.../*.parquet
  documents/contract_version=.../bucket=ab/*.parquet
  spans/contract_version=.../bucket=ab/*.parquet
  chunks/chunker_id=.../bucket=ab/*.parquet
  mentions/extractor_id=.../bucket=ab/*.parquet
  facts/extractor_id=.../bucket=ab/*.parquet
  embeddings/profile_id=.../bucket=ab/*.parquet
  quarantine/reason=.../
  runs/<run-id>/
```

Parquet is the default bulk format because it supports column pruning, partitioning, and DuckDB or
PyArrow out-of-core processing. Avro object container files are emitted where writer/reader schema
resolution or row transport is useful. Extracted large text can be stored as compressed Parquet
large strings or content-addressed compressed blobs referenced from rows; the pilot decides which
layout provides acceptable scan and repair behavior.

### PostgreSQL schemas

| Schema     | Canonical contents                                                                                   |
| ---------- | ---------------------------------------------------------------------------------------------------- |
| `ctl`      | Contract versions, migrations, runs, stages, shards, leases, checkpoints, errors, artifact manifests |
| `corpus`   | Documents, editions, source paths, spans, chunks, language, quality, duplicate groups                |
| `search`   | Search projection rows, embedding profiles, selected embeddings, topic assignments                   |
| `kg`       | Canonical objects, aliases, mentions, facts, qualifiers, review state, source evidence               |
| `ontology` | Terms, classes, predicates, mappings, axioms, ontology versions                                      |
| `eval`     | Frozen gold items, query sets, labels, run metrics, paired comparisons                               |

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
| `inventory`    | Walk archive, stat, MIME, encoding, hashes, archive-member policy           | Inventory Parquet             |
| `extract`      | Tika baseline; Docling/OCR/layout fallback; source coordinates              | Extracted documents/spans     |
| `normalize`    | UTF-8, Unicode normalization, boilerplate policy, language, metadata        | Canonical document records    |
| `dedupe`       | Exact, normalized, lexical/MinHash, edition groups; no destructive deletion | Duplicate overlays            |
| `chunk`        | Structure/table/sentence-aware chunks with overlap and source spans         | Chunk Parquet                 |
| `load-lexical` | PostgreSQL bulk load and ParadeDB index build/refresh                       | Lexical search projection     |
| `nlp`          | Russian morphology, NER, terminology, mention candidates                    | Mentions and term statistics  |
| `embed`        | Selective embeddings and optional reranker candidates                       | Versioned embedding artifacts |
| `load-vector`  | pgvector baseline and experimental ParadeDB vector projection               | Semantic search projection    |
| `topics`       | Sample/incremental clustering, labels, drift and hierarchy                  | Topics and assignments        |
| `entities`     | Blocking, probabilistic linkage, aliases, reversible clusters               | Canonical objects             |
| `facts`        | Rule/model/LLM structured extraction, validation, conflicts                 | Proposed facts with evidence  |
| `ontology`     | Vocabulary, class/predicate mappings, SHACL/OWL-compatible checks           | Versioned ontology assets     |
| `graph`        | Build and validate AGE projection                                           | Active versioned graph        |
| `evaluate`     | Retrieval, extraction, linkage, graph, cost, and resource metrics           | Immutable evaluation bundle   |
| `report`       | Coverage, failures, topics, objects, facts, equipment/suppliers             | HTML/JSON/Parquet reports     |

The end-to-end command runs the dependency closure, not a hardcoded shell chain.

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
arxiv-int pipeline run --archive-dir PATH --normalized-dir PATH [--from STAGE] [--to STAGE]
arxiv-int stage STAGE --archive-dir PATH --normalized-dir PATH [stage options]
arxiv-int run status RUN_ID
arxiv-int run resume RUN_ID
arxiv-int search lexical|semantic|hybrid QUERY
arxiv-int graph rebuild|check|query
arxiv-int report build RUN_ID
```

Standard Make targets are thin, documented wrappers:

```text
make help                  make bootstrap             make doctor
make config                make contracts             make contracts-gen
make contracts-evolution  make services-up           make services-down
make services-status      make logs                   make pipeline
make stage STAGE=...       make resume RUN_ID=...     make search QUERY=...
make graph-up              make ui-up                  make eval
make test                  make integration-test      make ci
make backup                make restore-check
```

The primary path contract works in both forms:

```bash
make pipeline ARCHIVE_DIR=/mnt/archive NORMALIZED_DIR=/mnt/normalized

arxiv-int pipeline run \
  --archive-dir /mnt/archive \
  --normalized-dir /mnt/normalized
```

Command-line values override `.env`; resolved non-secret values and path device ids are written into
the run manifest. Make never embeds machine-specific absolute paths.

## Resumability, idempotency, and provenance

A run id identifies an immutable requested configuration. Each stage is divided into stable shards
derived from content hashes or partition buckets. `ctl.run`, `ctl.stage_run`, and `ctl.shard_run`
record states such as `pending`, `running`, `succeeded`, `failed`, `quarantined`, and `superseded`.

A shard identity includes:

- ordered input artifact hashes and upstream manifest ids;
- contract, schema, code, tool, model, prompt, and configuration fingerprints;
- stage name/version and deterministic parameters;
- output manifest and row/file checksums.

Successful identical shards are reused. Failed or expired leases are resumable. Outputs are written
to temporary sibling paths, validated, then atomically renamed; database loads use staging tables
and transactions. Retries are bounded and classify permanent versus transient failures. `--force`
creates a new attempt but does not overwrite accepted evidence. `--invalidate STAGE` shows the
downstream closure and requires confirmation before marking reusable artifacts stale.

The archive is never modified. Duplicate resolution, suppression, entity merges, and fact review are
overlays with audit trails and rollback.

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

No fixed multiplier is universally safe. The preflight estimator must calculate a corpus-specific
budget for normalized data, PostgreSQL heap, ParadeDB covering index, vector index, AGE projection,
WAL, temporary build space, and backup. The initial planning envelope is **2.5-4.0 times the
normalized indexed subset in addition to the raw archive**, and a full run is refused until the
pilot replaces that envelope with measured amplification and a safety margin. Concurrent index
rebuild may temporarily require a second full index.

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

## Reuse map

| Source         | Reuse                                                                                                                                                                                                                             | Do not carry forward                                                                                               |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `agent-py`     | Template structure, project rename, Python/uv/Make gates, typed CLI seam, doc-link and spec-plan integrity, AGENTS policy                                                                                                         | Starter identity and example-only behavior                                                                         |
| `fl-op`        | ODCS registry, canonical model, namespaced generation hints, deterministic multi-format generators, fingerprints, semantic mapping, reviewed evolution baselines, compatibility tests                                             | Fleet domain, optimization solver, ES generator as an active target                                                |
| `selfsuvis`    | Layered env/path helper, cross-filesystem cache handling, preflight/resource checks, queued logging, step timing, partial results, GPU/model lifecycle patterns                                                                   | Video/IoT pipeline, Qdrant production dependency, monolithic 35-step orchestration                                 |
| `loc-lm-bench` | Citation-preserving ingestion where applicable, conflict/dedup audit, Splink linkage seam, retrieval metrics and paired verdicts, local backend abstraction, model fit/VRAM telemetry, ontology/fact gates, immutable run bundles | Ukrainian-only defaults, robotics lanes, FAISS as production store, the full benchmark CLI inside the core package |
| Upstream OSS   | Tika, Docling, OCRmyPDF/Tesseract, PyArrow, DuckDB, Data Contract CLI, ParadeDB, pgvector, AGE, rdflib/pySHACL, Ollama/vLLM                                                                                                       | Thin local rewrites of their core engines                                                                          |

Reuse is by dependency or a small, attributed extraction at a stable seam. Copying an entire
application into `arxiv_int` is not reuse. License notices and behavioral tests accompany copied MIT
code.

## Evaluation and acceptance

### Evaluation datasets

Before store or model promotion, freeze a representative corpus manifest and reviewable gold sets:

- file-format/extraction set with expected text, tables, page/offset anchors, and failures;
- Russian lexical query set including inflection, identifiers, abbreviations, OCR noise, e/yo
  variants,
  keyboard-layout mistakes, and mixed-language queries;
- semantic and multi-hop query set with exact source spans;
- entity pairs/clusters with match/non-match labels;
- entity and relation/fact extraction set by high-value type;
- ontology constraint and contradiction cases;
- graph path/query answers checked against relational SQL;
- equipment and supplier report cases with evidence and completeness review.

Gold creation and threshold setting use separate tuning and final partitions. LLM-drafted items do
not become scoring truth without review.

### Required acceptance gates

| Area              | Gate                                                                                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Fresh setup       | From a copied repo and edited `.env`, `make bootstrap`, `make doctor`, `make services-up`, a smoke pipeline, and `make ci` succeed without paths tied to the original disk.                      |
| Contracts         | ODCS lint, generation drift, Avro round-trip/compatibility, evolution policy, migration status, and live Postgres schema tests pass.                                                             |
| Idempotency       | Re-running an unchanged successful shard writes no duplicate canonical rows or artifacts and reports a cache hit; interrupted stages resume from completed shards.                               |
| Provenance        | Every sampled search result, mention, fact, topic assignment, graph edge, and report row resolves to source evidence and a complete transformation fingerprint.                                  |
| Extraction        | Per-format text/table/anchor coverage and quarantine reasons meet thresholds declared before the full run.                                                                                       |
| Lexical retrieval | Russian BM25 recall@k, MRR, evidence intactness, p95 latency, and index amplification pass on the final query set.                                                                               |
| Vector/hybrid     | Candidate must beat or complement lexical retrieval with a paired confidence interval and remain within build, storage, latency, and VRAM/RAM budgets; otherwise lexical-only is a valid result. |
| Entity resolution | Precision at the proposed auto-merge threshold meets the predeclared high-precision target; uncertain pairs remain unmerged.                                                                     |
| Facts             | Per-type precision/recall and citation-span validity meet declared thresholds; invalid structured output and ontology violations are accounted for.                                              |
| Graph             | Counts reconcile with relational projection inputs; sampled SQL/Cypher paths agree; rebuild and backup/restore tests pass.                                                                       |
| Scale             | Two staged pilots complete within measured disk/RAM/VRAM envelopes with no unbounded queue, transaction, temp, or WAL growth.                                                                    |
| Privacy           | Network-denied integration run succeeds after required images/models are present; logs and reports contain no secrets or unintended corpus content.                                              |

Each comparison ends in `adopt`, `retain baseline`, or `inconclusive`; a negative result is valid
and must not be hidden by choosing a convenient threshold.

## Operations, backup, and security

The archive mount is read-only. Service ports bind to loopback. Database roles separate migration,
pipeline writes, read-only UI, and backup. Secrets live in `.env` or operator-provided secret files,
never generated artifacts or logs. Containers run non-root where upstream images permit, have
bounded resources, and receive only required mounts.

Backups include:

- ODCS contracts, migrations, configuration template, and code in version control;
- normalized manifests and portable datasets through filesystem snapshots or another disk;
- PostgreSQL logical/physical backup appropriate to the pinned extension versions;
- extension/image/model digests and a restore runbook;
- restore verification that rebuilds or validates ParadeDB and AGE projections.

Because Community ParadeDB does not promise enterprise HA/read-replica support, local recovery is
based on tested backup plus projection rebuild, not an assumed replica.

## Delivery strategy

| Phase                       | Outcome                                                          | Capability span                                          | Exit signal                                                     |
| --------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------- |
| 0 - Foundation              | Personalized repo, portable paths, contracts, one database image | `project-foundation` through `canonical-store`           | Fresh-copy service and contract smoke passes                    |
| 1 - Local evidence seams    | Local inference adapters and replayable evaluation fixtures      | `local-inference`, `evaluation-foundation`               | Provider and metric conformance tests pass                      |
| 2 - Corpus substrate        | Rebuildable normalized lake and restartable stages               | `corpus-foundation`, `pipeline-control`                  | Representative extraction run resumes without duplication       |
| 3 - Retrieval and NLP       | Russian lexical baseline, selected vectors, mentions             | `lexical-retrieval` through `russian-nlp`                | Held-out lexical and NLP baselines are readable                 |
| 4 - Knowledge and discovery | Facts, identity, ontology, graph, topics, reports, UI            | `knowledge-extraction` through `discovery-visualization` | Evidence-bearing operator scenarios pass                        |
| 5 - Evidence and operations | Comparative scale evidence and recovery                          | `evaluation-evidence`, `operational-recovery`            | Staged pilot and restore drill support an adopt/retain decision |

The critical path is:

```text
project foundation
  -> portable runtime
  -> contract governance
  -> canonical store
  -> local inference and evaluation foundation
  -> corpus foundation
  -> pipeline control
  -> lexical retrieval
  -> Russian NLP
  -> knowledge extraction
  -> identity/ontology/graph
  -> discovery and visualization
  -> evaluation and operational recovery
```

Semantic retrieval and vLLM are evaluated branches. They must not block a useful lexical, CPU-first
system when their valid result is `retain baseline`.

## Capability Registry

Every capability appears once. Status is `planned` until current-state documentation and acceptance
evidence exist. Registry order is the implementation line used by `plan.md`.

| #   | Capability                | Status  | How it is evaluated                                                                          | Implementation                                               |
| --- | ------------------------- | ------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 1   | `project-foundation`      | planned | Fresh copy, rename, locked bootstrap, CLI identity, docs integrity, and CI pass              | `plan.md#project-foundation----project-foundation`           |
| 2   | `portable-runtime`        | planned | Multi-SSD path and Compose profile smoke tests pass from two checkout locations              | `plan.md#portable-runtime----portable-runtime`               |
| 3   | `contract-governance`     | planned | ODCS lint/generation/evolution/Avro/migration/live-store gates pass                          | `plan.md#contract-governance----contract-governance`         |
| 4   | `canonical-store`         | planned | ParadeDB/pgvector/AGE compatibility, schema, backup, restore, and projection checks pass     | `plan.md#canonical-store----canonical-store`                 |
| 5   | `local-inference`         | planned | Ollama/vLLM conformance, structured outputs, model-fit, and local-only endpoint gates pass   | `plan.md#local-inference----local-inference`                 |
| 6   | `evaluation-foundation`   | planned | Frozen fixtures, replayable metrics, split guards, and paired verdict utilities pass         | `plan.md#evaluation-foundation----evaluation-foundation`     |
| 7   | `corpus-foundation`       | planned | Representative inventory, extraction, normalization, dedupe, and chunk gold sets pass        | `plan.md#corpus-foundation----corpus-foundation`             |
| 8   | `pipeline-control`        | planned | Sharded stage, resume, retry, invalidation, idempotency, and progress tests pass             | `plan.md#pipeline-control----pipeline-control`               |
| 9   | `lexical-retrieval`       | planned | Held-out Russian relevance, latency, index size, and rebuild gates pass                      | `plan.md#lexical-retrieval----lexical-retrieval`             |
| 10  | `semantic-retrieval`      | planned | Selected-tier vector and hybrid candidates receive paired adopt/retain verdicts              | `plan.md#semantic-retrieval----semantic-retrieval`           |
| 11  | `russian-nlp`             | planned | Language, morphology, terminology, and NER metrics pass per type                             | `plan.md#russian-nlp----russian-nlp`                         |
| 12  | `knowledge-extraction`    | planned | Structured extraction, evidence, fact quality, and contradiction gates pass                  | `plan.md#knowledge-extraction----knowledge-extraction`       |
| 13  | `identity-ontology-graph` | planned | Linkage, ontology, SQL/Cypher parity, rebuild, and bounded traversal gates pass              | `plan.md#identity-ontology-graph----identity-ontology-graph` |
| 14  | `discovery-visualization` | planned | Topic stability plus operator completion of search, graph, equipment, and supplier scenarios | `plan.md#discovery-visualization----discovery-visualization` |
| 15  | `evaluation-evidence`     | planned | Provenance audit and representative scale pilots produce readable, capacity-aware verdicts   | `plan.md#evaluation-evidence----evaluation-evidence`         |
| 16  | `operational-recovery`    | planned | Security checks, backup/restore drill, disk exhaustion, interruption, and runbook tests pass | `plan.md#operational-recovery----operational-recovery`       |

## Success criteria

The project succeeds when an operator can copy the repository to any suitable disk, copy
`.env.example` to `.env`, point it at separate archive, normalized-data, and PostgreSQL disks, start
the selected local services, and run one stage or the complete pipeline with continuous progress and
safe resume. Search, topics, objects, facts, ontologies, graphs, and equipment/supplier reports are
useful on a representative Russian corpus, carry source evidence, and can be rebuilt from open,
versioned contracts and normalized artifacts. The simpler PostgreSQL architecture remains in place
only while measured quality, scale, and recovery evidence supports it.
