# Task Record

## Task and scope

- Id / capability / checkpoint: `bind-real-owned-stage-fingerprints` / `pipeline-control` /
  `review-corpus-and-control-integrity`
- State: accepted
- Source: `docs/impl/plan.md`, revision `e9cc68e9b1df026df93e826dd86b49390358e48c`; clean tree.
- Initial count: 68 tasks (58 agent, 10 human). All six dependencies are accepted.
- Accepted task:

```markdown
#### bind-real-owned-stage-fingerprints

Replace the placeholder stage identity so a changed contract, validator, transformation, tool or
model invalidates the shards it actually affects.

- Serves: `pipeline-control` --
[Resumability, idempotency, and provenance](../design/spec.md#resumability-idempotency-and-provenance)
- Agent status: CLEAR
- Dependencies: [Run ledger and atomic artifacts](records/0041-pipeline-implement-run-ledger-and-atomic-artifacts.md);
[Stage DAG CLI and Make targets](records/0042-pipeline-implement-stage-dag-cli-and-make-targets.md);
[Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
[Contract data-quality checks](records/0019-contract-gov-implement-contract-data-quality-checks.md);
[dbt transformation foundation](records/0024-store-implement-dbt-transformation-foundation.md);
[Control integration checkpoint](records/0054-pipeline-review-control-integration-boundaries.md).
- User-visible outcome: Editing a contract, a Pandera rule, a dbt model, a pinned tool or a model
makes the next run recompute exactly the affected shards instead of serving a cache hit produced
under the previous definitions.
- Scope boundary: Populate the existing `OWNED_FINGERPRINT_FIELDS` identity from the assets that
already exist and let each stage declare its own model/prompt/tool values; do not add a new
fingerprint field, a new registry, or a corpus stage. Fixture stages may still declare fixture
values, but they must be real values for those fixtures rather than one shared constant.
- Data and artifact paths: `src/arxiv_int/pipeline/run/context.py`,
`src/arxiv_int/pipeline/control/fingerprints.py`, `src/arxiv_int/pipeline/dag/execute.py`,
existing contract, rule-catalog and dbt asset roots; mirrored tests under `tests/pipeline/`.
- Execution path: Derive contract, schema and validation-catalog fingerprints from the registered
contract and rule assets, dbt model/input/rule fingerprints from the dbt project, code and
dependency fingerprints from the packaged distribution and lock, and let a stage supply
tool/model/prompt values through its spec; keep `configuration_fingerprint` as it is. Record which
asset each field reads so a reviewer can reproduce it.
- Acceptance gates: Every owned field has a documented source and no field is a shared literal;
changing one contract, one rule, one dbt model or one declared tool changes only the reuse keys of
the shards that depend on it and leaves the others cached; an unchanged tree still cache-hits with
zero workers; `stale_closure()` still walks consumer edges from the changed field. Run the pipeline
suites and `make ci`; a provided-archive rerun is tracked separately.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-corpus-and-control-integrity`.

```

- Amendments: none.

## Implementation

`pipeline.control.owned` replaces the `stage-v1` filler removed from run context. Stage identity
reads declared assets at every lookup, before workers or optional backends load. The existing
`ReuseIdentity`, owned field list, reuse index, executor and lineage closure remain unchanged.
`StageSpec` gains contract, code/dependency and dbt asset declarations plus frozen tool/model/prompt
maps. Runner rebinding uses `dataclasses.replace` so it preserves every declaration. Fixture tool
values describe the actual fixture runner, feature and outcome; empty unused asset sets hash with
stage/field identity. The evaluate runner declares its evaluation helper tree.

Sources are documented field by field in the
[current-state page](../current/pipeline-control.md). Reused components: `FileRegistry`, the existing
resource overlay helpers, rooted-reference validation, bounded `hash_file`, canonical JSON/SHA-256,
and the original consumer-edge invalidation. No new dependency, owned field, registry, corpus stage,
configuration behavior or migration is introduced. Existing placeholder keys intentionally miss
once without overwriting accepted artifacts.

Self-review improvements within the accepted scope:

- A whole-lock digest would invalidate unrelated tools. The final implementation selects declared
  package records and their transitive locked dependencies, retaining all resolved platform/extra
  variants conservatively. Installed distribution metadata and Python version also bind identity.
- Shared code excludes production/fixture declaration modules; each stage's selected declarations
  bind separately. Explicit helper paths and the runner source file still bind executable code.
- dbt identity reads the selected contracts' tables from the combined `generated/dbt/sources.yml`
  actually copied by project assembly, as well as individual generated source/test definitions.
  Unrelated combined-source tables stay outside the identity.
- Missing contracts, schemas, rules, paths, lockfiles and declared locked packages refuse reuse.
  Root escapes and directory symlink traversal refuse. Content paths are portable across overlays.
- Synthetic forecast checkouts now carry the real lock. A generation-mismatch regression declares
  the registered `documents` validator instead of the nonexistent `beta` contract; its original
  quality refusal remains tested.

Stage owners declare the complete helper and dbt dependency set, including upstream model files,
source/test YAML and runtime packages. This is explicit ownership on the existing spec, not another
Jinja dependency resolver or dbt selector implementation. A wheel workspace must supply `uv.lock`;
disposable overlays without a project/lock can use the editable distribution checkout. No archive
rerun or GPU model workload is part of this task's acceptance.

## Acceptance evidence

Evidence: `$DATA_DIR/stage-fingerprints/0058-host/`. Host GPU queried outside the restricted sandbox:
RTX 4060 Ti, 16380 MiB VRAM, driver 595.84 (`cuda-host.csv`). These are deterministic synthetic runs
on the CUDA host, not real-archive quality or CUDA model-fit evidence.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Failing regression before repair | `pytest tests/pipeline/dag/test_owned_assets.py`; `regression-before.log` | Two expected failures: changed contract/rules still returned all cache hits |
| Every owned field has a real documented source | `tests/pipeline/control/test_owned.py`; `owned-sources.json`; current-state source table | Pass; exact field set, portable sources, stage-specific empty sets and immutable declarations |
| Contract/rule/dbt/tool/model/prompt edits affect only consumers | `tests/pipeline/dag/test_owned_assets.py`; `owned-assets.log` | Pass; affected producer and consumer rerun, unaffected stage stays cached, unchanged rerun invokes zero workers |
| Owned field still selects consumer closure | `test_dbt_edits_and_stale_closure` | Pass for model, input and rule fields using actual execution keys |
| Code/schema/source selection and missing assets | `tests/pipeline/control/test_owned.py` | Pass; unowned code/docs/contracts/tables stay unchanged, missing and escaping references refuse |
| Selected/transitive lock changes | `tests/pipeline/control/test_dependency_assets.py` | Pass; unrelated pin excluded, consumed transitive pin included, missing lock/package refuses |
| Pipeline suites | `pytest tests/pipeline -m 'not heavy' -o addopts='' -q`; `pipeline.log` | Pass; 184 passed, 1 CUDA-visibility skip in sandbox; host CI also covers that test |
| Backend-free identity lookup | Fresh Python process binds a documents validator and checks `sys.modules` and fixture call counters | Pass; no dbt, Pandera, torch or transformers imports and zero workers |
| Format, typing and complexity | `make format typecheck complexity-gate` | Pass; no policy gate weakened |
| Required CI | `UV_CACHE_DIR="$DATA_DIR/cache/uv" make ci`; `ci-host.log` | Pass; 1134 passed, 50 heavy tests deselected; CUDA forecast host check included |
| Documentation integrity | `make lint-doc-links lint-spec-plan`; narrow pymarkdown scan | Pass; final links, plan integrity and narrow edited-page Markdown checks pass |
| Auxiliary repository Markdown lint | `make lint-md`; `markdown.log`, `markdown-baseline.log` | Fails with 23 pre-existing MD013 line-length findings, reproduced from HEAD; changed current page and record pass |

Initial sandbox CI could not write the default uv cache, then could not bind synthetic localhost
HTTP sockets (`ci-socket-diagnostic.log`). The socket-restricted full test run was interrupted and
replaced by the complete host-permission CI; the writable uv cache uses the existing DATA_DIR root.
No acceptance test is skipped to bypass these restrictions. `make quality` was not required for
this non-infrastructure task and was not run. The optional repository Markdown findings are outside
this task; their HEAD reproduction is retained rather than changing unrelated documents.

## Audit handoff

`none identified` in the reviewed task scope: selected asset provenance, owned-key propagation,
consumer closure, missing-source refusal, immutable spec values, optional imports, lock selection,
portable resource overlays and configuration compatibility. The explicit declaration completeness
rule is part of the existing stage-owner boundary; future real producers must supply their complete
helper/dbt/model/tool assets at the planned corpus/control checkpoint. No human review handoff is
required for this task, and this work approves no corpus, model or provided-archive gate.

## Close or resume

Accepted after complete host `make ci`: 1134 passed, 50 heavy tests deselected, with the CUDA forecast
host check executed. All task acceptance gates pass. Current-state sources and the record index are
updated; the satisfied task is removed and the corpus/control checkpoint dependency links this
record. Plan counts move from 68 to 67 tasks (58 to 57 agent, 10 human unchanged). The next eligible
agent task is `bound-archive-snapshot-hashing`; it is not started here.

Capability change: stage reuse now binds actual declared assets and invalidates only affected
producers/consumers. `pipeline-control` retains its existing capability status and remaining work.
No archive rerun, CUDA model-fit or human approval is claimed. No commit or push was made. Test-owned
synthetic HTTP fixtures exited; no task service remains. Evidence is retained under the tool root.

The source evidence JSON has SHA-256
`6af22a5eed8e26902011e7942d2d5e6308ad9dbf1b4baccb1ac9c13f6eefd9dc`.
Final `make lint-doc-links lint-spec-plan plan-status`, narrow Markdown scan and `git diff --check`
verify the acceptance transition. The 23 HEAD Markdown line-length findings remain outside scope.
