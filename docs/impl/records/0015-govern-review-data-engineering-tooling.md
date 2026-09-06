# Task Record

## Task and scope

- Id / capability / checkpoint: `review-data-engineering-tooling` / `governance` /
  `review-foundation-and-store-boundaries`
- State: accepted; the bounded review/documentation gates pass; tool implementation remains open.
- Source: ad hoc user request; code revision `981c7d3`; initially clean working tree.
- Initial count: 81 tasks (70 agent, 11 human); next agent task reported by `make plan-status`:
  `build-pinned-paradedb-age-image`.
- Original user request (wording preserved; line wrapping and Markdown autolinks only):

> Please pick lightweight, Pythonic migration tools:
> <https://github.com/vajol/python-data-engineering-resources/blob/main/resources/db-migration.md>,
> e.g.   Alembic: update spec and implement migration using migration tools, e.g., generating
> migrations from contract, but not just SQL. Also, we have some tasks involving SQL. Please use
> <https://github.com/dbt-labs/dbt-core> to avoid embedded SQL transformations, and
> <https://github.com/Great-Expectations-Data> for data quality checks or an equivalent. Please
> review the design and use lightweight tools to ensure best practices for a data engineering
> project, with maintainable and descriptive code and data operations. Review the
> implementation, update the spec, add a refactoring task, and update the remaining tasks to use
> proper schema and data-transformation Python tools, libraries, and best practices.

- Working scope: review existing implementation and upstream tool constraints, update target design,
  add bounded implementation tasks and route affected remaining work. Migration implementation is
  the new prerequisite refactor; this review does not claim that the tools are installed or running.
  An optional scope question was offered while independent review continued.
- Amendments: none.

- Selected bounded review task, written from this ad hoc request before implementation work:

```markdown
#### review-data-engineering-tooling

Review schema, migration, transformation and data-quality implementation; select lightweight
maintained tools and specify their adoption as prerequisite work.

- Serves: `governance` -- [Data operations](../../design/spec.md#data-transformations-and-quality)
- Agent status: CLEAR
- Dependencies: Existing contract generation/evolution and domain-contract records 0011, 0012, 0014;
read-only implementation inspection and the user-provided upstream references.
- User-visible outcome: The specification and remaining tasks require Python schema operations,
reviewable dbt models and reusable dataset-quality checks with honest current-state boundaries.
- Scope boundary: Review and documentation; create implementation owners and dependency gates for
migration, transformation and validation work. No production code, dependency or database changes.
- Data and artifact paths: `docs/design/spec.md`, `docs/impl/plan.md`, current contracts, database
README, record/index, and `$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Inspect relevant code/tests/records; verify upstream tool constraints; reproduce
bounded migration-check weaknesses with synthetic data; update specification before planning.
- Acceptance gates: Concrete findings have one owner each; tool scope/exclusions/evaluation are
specified; affected tasks use the shared tool design; current docs distinguish planned behavior;
format, CI, Markdown, links and spec-plan gates pass; record before/after counts and limitations.
- Documentation target: `docs/impl/current/contracts.md`
- Review checkpoint: `review-foundation-and-store-boundaries`.
```

## Implementation

Affected files: `docs/design/spec.md`, `docs/impl/plan.md`,
`docs/impl/current/contracts.md`, `docs/impl/records/README.md`, and `db/README.md`.
Reuse the existing ODCS registry/loaders, semantic/evolution policy, generated serialization
artifacts, runtime environment/root policy, feature catalog, stage interfaces, and ontology rules.
Keep production implementation and dependency changes in their owning tasks.

Selected SQLAlchemy Core metadata + Alembic Python revisions; Python dbt Core 1.x with
`dbt-postgres`; Polars/PyArrow batch operations; Pandera/Polars plus dbt data tests as the GX
alternative. This keeps ODCS authoritative and shares contract fields across generated schemas,
validation and dbt YAML. It does not replace existing domain/SHACL validation or held-out metrics.
No extra orchestration service or framework is introduced.

The migration shortlist supplied by the user includes Alembic, yoyo and framework-specific tools.
Alembic fits the existing framework-independent Python project because it compares SQLAlchemy
metadata and emits Python operations. dbt stores relational business SQL in described, tested
models; it does not make PostgreSQL transformations Python models. Local tabular Python work uses
Polars. Pandera + dbt tests is selected to reuse the same batch/model interfaces and avoid a second
quality-suite lifecycle; dependency size and runtime performance have not been benchmarked.

Upstream references inspected on 2026-09-06 (API/compatibility guidance, not installed pins):

- [Requested migration shortlist](https://github.com/vajol/python-data-engineering-resources/blob/main/resources/db-migration.md).
- [SQLAlchemy metadata](https://docs.sqlalchemy.org/en/20/core/metadata.html) and
  [Alembic candidate generation and limits](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).
- [Requested dbt Core repository](https://github.com/dbt-labs/dbt-core), whose default branch
  describes the Rust 2.0 beta and directs Python users to `1.latest`;
  [PostgreSQL adapter](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup) and
  [Python model constraints](https://docs.getdbt.com/docs/build/python-models).
- [Requested GX organization](https://github.com/Great-Expectations-Data) and
  [official GX workflows](https://docs.greatexpectations.io/docs/core/introduction/);
  [Pandera Polars checks](https://pandera.readthedocs.io/en/stable/polars.html),
  [dbt data tests](https://docs.getdbt.com/docs/build/data-tests), and
  [Polars streaming limits](https://docs.pola.rs/user-guide/concepts/streaming/).

Three prerequisite tasks own adoption: migration plumbing and metadata in contract-governance;
shared quality adapters in contract-governance; dbt project/execution in canonical-store.
Canonical schema acceptance now explicitly needs a declared live run, verified legacy adoption,
prior-release upgrade tests and catalog parity. Existing store/projection tasks and 29 downstream
execution paths now name their concrete tools. Pipeline publication/reuse, reconciliation,
extraction, identity, domain artifacts, anomaly cohorts, catalogs, reports, freshness, recovery,
embeddings and archive-ledger consumers reuse shared adapters. Proof tasks inherit the common
quality/fingerprint requirements. The foundation/store checkpoint reviews tool ownership and
integration before pipeline consumers proceed.

Existing historical records retain their original evidence. Current-state and database docs now
state the limitations of those checks; contract-governance is planned again for the new scope.

## Acceptance evidence

Commands use `DATA_DIR=/tmp/arxiv-int-tooling-review`. Retained outputs are under
`$DATA_DIR/architecture-review/20260906/`. No new production tests were added for this documentation
task; synthetic review probes exercise existing helpers and future refactoring tasks require the
corresponding failing regressions.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Review implementation and upstream tools | Sources and audit handoff; `review-probes.json` | Pass; four synthetic helper limitations reproduced, no operator data accessed |
| Specify tools, boundaries, and evaluation | Specification generation/evolution/data-quality sections and plan | Pass; three owners, explicit live acceptance and negative outcomes, 29 downstream execution paths updated |
| Preserve current capability claims | Contracts current-state page and database README | Pass; target tools are explicitly unimplemented; prior records retained |
| Formatting | `make format DATA_DIR=/tmp/arxiv-int-tooling-review` | Pass; 168 Python files unchanged |
| Documentation | `make lint-md DATA_DIR=/tmp/arxiv-int-tooling-review`; `lint-md.txt`; separate `pymarkdown scan db/README.md` | Pass; final record/index recheck is retained in `close-checks.txt` |
| Required CI | `make ci DATA_DIR=/tmp/arxiv-int-tooling-review`; `ci-restored.txt` | Pass; 432 tests, formatting/lint/type/complexity/shell, links/plan, contract generation/evolution and ontology checks |
| Environment failures and recovery | `ci.txt`, `ci-retry.txt`, `ci-final.txt`, `environment-restore.txt` | Initial sandbox cache/Docker denial; offline retry passed SQL apply but lacked cached graph dependencies; next attempt stopped at missing graph imports. Restored the unchanged locked dev/contracts/graph extras before final CI; no gates weakened |
| Links, task graph and counts | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status`; `close-checks.txt` | Pass; zero broken links/findings; 84 tasks, next agent is the migration refactor |

## Audit handoff

Refactor needed before canonical-store acceptance. The bounded review may proceed with the
following repairs routed; it does not close the foundation/store integration checkpoint.

| Note | Observation, evidence and impact | Next check and sole owner | Disposition |
| --- | --- | --- | --- |
| `AUD-data-engineering-tooling-1` | Observed / blocking before live-store acceptance: `contracts/evolution/migrations.py` returns no findings for missing dbmate, a comment-only dump mentioning the expected table, and `TRUNCATE kg.items` without the TABLE keyword. `conformance.py` collapses `corpus.items` and `kg.items`; `check.py` only applies generated CREATE TABLE SQL, without applying revision history or querying catalog parity. `generate/pipeline.py` exports generic unqualified tables while `adapters.py` carries schema/partition hints separately. | [Migration refactor](0017-contract-gov-refactor-contract-schema-and-migration-tooling.md): replace regex/dump-name checks with owned SQLAlchemy metadata and Alembic history; add failing regressions for these cases, immutable revisions and legacy-adoption refusal. Its canonical-store consumer separately requires live upgrade/adoption evidence. | Resolved by [0017](0017-contract-gov-refactor-contract-schema-and-migration-tooling.md); dbmate checks and regex conformance removed, offline gates pass, live upgrade evidence stays with `create-canonical-relational-schema` |
| `AUD-data-engineering-tooling-2` | Observed planning gap / blocking before relational projection expansion: no dbt project or transformation implementation exists in the inspected source tree; store/projection/catalog/report tasks previously left set-based operations to ad hoc implementation. Readiness SQL is a diagnostic query, and generated index/Cypher SQL is engine-specific, so neither is business transformation SQL to relocate into models. | [dbt foundation](../plan.md#implement-dbt-transformation-foundation): verify local model build/test, clean/incremental/deletion parity, role isolation and retained lineage before consumers add business models. | Open; consumers updated |
| `AUD-data-engineering-tooling-3` | Observed / blocking before dataset publication: optional dependencies and contract checks cover schema documents, serialization and ontology; no Pandera/GX dataset adapter or dbt whole-relation test runner exists. Batch schema validity cannot establish global uniqueness, relationships or source-evidence validity. | [Shared data-quality checks](../plan.md#implement-contract-data-quality-checks): positive/negative and cross-batch fixtures, declared global-check execution, bounded results and explicit not-run status; producers retain their semantic rules. | Open; publication/checkpoint consumers updated |

Synthetic probe output is retained in `review-probes.json`. It proves these helper limitations
without accessing operator data, running dbmate, or changing production files. Existing CI exercises
disposable baseline SQL apply; it does not verify the planned Alembic/dbt/Pandera integrations.
No legacy migration adoption, real-archive conformance, model quality, CUDA fit, selected-tool
dependency compatibility or performance was tested in this review.

## Close or resume

Review accepted with three implementation owners still open. Current contracts, database README,
capability registry and record index link the findings and implementation boundaries. The plan
contains no completed review task or historical completion text, and no prior task was removed.

Counts: 81 to 84 tasks; 70 to 73 agent tasks, 11 human tasks unchanged. Status totals are 30 CLEAR,
43 RUN NEEDED, 10 HUMAN-GATED and 1 BLOCKED BY HUMAN; 79 tasks have open prerequisites. Next action:
`refactor-contract-schema-and-migration-tooling`, then shared quality and the canonical-store/dbt
integration chain. The image-build task remains independently eligible.

Runtime capabilities did not change. Contract-governance is marked planned for its added migration
and dataset-quality scope; existing serialization, contract and ontology behavior remains present.
No production code, dependencies/lock, applied database history, private data, or existing accepted
record was changed. `make format` left source/tests untouched; CI's locked environment was restored.
`make quality` was not required for this documentation-only change. Final `git status` contains only
the six intended documentation files. CI-owned disposable processes complete through existing
cleanup; review artifacts are retained at the configured root. No commit or push was made.
