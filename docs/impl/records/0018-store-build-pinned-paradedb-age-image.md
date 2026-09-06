# Task Record

## Task and scope

- Id / capability / checkpoint: `build-pinned-paradedb-age-image` / `canonical-store` /
  `review-foundation-and-store-boundaries`
- State: accepted
- Source: [plan](../plan.md) (task removed on acceptance); working tree also contains unrelated
  contract-migration work from `0017` that this task did not absorb.
- Initial count: 84 tasks (73 agent, 11 human).
- Accepted task:

```markdown
#### build-pinned-paradedb-age-image

Build and verify a project-owned image containing one PostgreSQL major, ParadeDB/`pg_search`,
pgvector, and Apache AGE.

- Serves: `canonical-store` -- [Architecture decision](../design/spec.md#architecture-decision)
- Agent status: RUN NEEDED
- Research: yes
- Dependencies: Compose profiles and operator wrappers documented in
[Portable runtime](current/portable-runtime.md).
- User-visible outcome: The core database starts from a reproducible image and reports exact
extension/build identities; graph mode is enabled only when its compatibility suite passes.
- Scope boundary: Test extension coexistence, licensing, initialization, upgrade seam, and basic
operations; do not claim production multi-TB scale.
- Data and artifact paths: `docker/postgres/Dockerfile`, `docker/postgres/initdb/`,
`docker/postgres/NOTICE`, `tests/integration/extensions/`, and `$PGDATA_DIR` for the declared
disposable run.
- Execution path: Derive from a pinned ParadeDB Community digest; install a pinned AGE release for
the same PostgreSQL major; merge preload requirements; create `vector`, `pg_search`, and `age` in
order; run SQL, BM25, vector, Cypher, dump/restore, restart, and transaction probes.
- Acceptance gates: Image builds from a clean cache; extension versions match pins; combined probes
pass across restart and dump/restore; licenses are present. A valid negative result disables the
AGE profile and records the incompatibility without blocking relational graph work.
- Documentation target: `docs/impl/current/canonical-store.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

- Amendments: none. Research selected AGE `PG17/v1.7.0-rc0` because design-table master commit
  `0e305662` (1.8.0) does not compile on PostgreSQL 17; documented in pins/NOTICE/current page.

## Implementation

- Image: `docker/postgres/{Dockerfile,pins.env,NOTICE,initdb/,scripts/merge_preload.sh}`
- Gate: `docker/postgres/age-compatibility.json` (AGE enabled after successful probes)
- Compose `database` image: `arxiv-int/postgres:17-0.25.6-age1.7.0`
- Modules: `arxiv_int.stores.postgres_image` (pins, build, probes, compatibility, CLI);
  `arxiv_int.runtime.host_identity` for Compose/`docker run --user`
- Entrypoints: `make postgres-image`, `make postgres-image-probe`, `arxiv-int store ...`
- Graph gate: `require_graph_age` refuses `up` when AGE disabled; readiness degrades for graph
- Ownership: writable Compose services require `RUNTIME_UID`/`RUNTIME_GID` from the operator
  wrapper (no silent `1000` default); disposable probes pass `--user` so PGDATA stays host-owned
- Docs: [canonical-store.md](../current/canonical-store.md); portable-runtime image and ownership notes
- Reuse: existing Compose/runtime readiness; ParadeDB bootstrap order; disposable Docker probe style
  from contract SQL validation
- Limits: no multi-TB claim; AGE Viewer image still downstream; live probe test is opt-in via
  `ARXIV_INT_RUN_EXTENSION_PROBES=1`

## Acceptance evidence

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Clean-cache image build | `make postgres-image NO_CACHE=1` | pass; tag `arxiv-int/postgres:17-0.25.6-age1.7.0` |
| Extension versions match pins | probe `versions` + image `/usr/share/arxiv-int/extension-pins.json` | pass; pg_search 0.25.6, vector 0.8.4, age 1.7.0, preload merged |
| Combined probes | `arxiv-int store probe-image --write-gate` on disposable `$DATA_DIR/.../pgdata` | pass; SQL, BM25, vector, Cypher, txn, restart, dump/restore |
| Licenses present | `docker/postgres/NOTICE` + image `/usr/share/arxiv-int/licenses/` | pass; AGPL/Apache/PostgreSQL/AGE named |
| AGE gate recorded | `docker/postgres/age-compatibility.json` | pass; `age_enabled: true` at `2026-09-06T11:21:50Z` |
| Host-owned PGDATA | disposable probe with `--user`; `stat` uid/gid == host; `rmtree` without root | pass; smoke under `$DATA_DIR/postgres-image-probe/ownership-smoke-*` |
| Master AGE compile (research) | Dockerfile build of `0e305662` on PG17 | valid-negative research; switched to PG17/v1.7.0-rc0 |
| Unit/CI gates | `make ci DATA_DIR=/tmp/arxiv-int-store-image`; `make lint-doc-links`; `make lint-spec-plan` | pass; 530 passed, 1 skipped (opt-in live probe) |
| Multi-TB scale | not claimed | out of scope |

## Audit handoff

none identified. Reviewed image build, preload merge, init order, graph gate refusal, host-UID
ownership for bind mounts, and probe suite boundaries; relational schema application remains owned
by `create-canonical-relational-schema`.

## Close or resume

Accepted after probes, ownership fix, documentation, and `make ci`. Plan counts: 84 tasks before,
83 after (agent lane 73 to 72; human 11 unchanged). Capability `canonical-store` gains a verified
store image; not marked shipped (schema/projection work remains). Next agent work:
`implement-contract-data-quality-checks` per `make plan-status`.
