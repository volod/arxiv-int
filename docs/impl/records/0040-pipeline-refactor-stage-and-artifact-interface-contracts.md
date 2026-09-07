# Task Record

## Task and scope

- Id / capability / checkpoint: `refactor-stage-and-artifact-interface-contracts` /
  `pipeline-control` / `review-pipeline-publication-and-reuse-boundaries`
- State: accepted; every required gate below passed.
- Source: [plan](../plan.md) task `refactor-stage-and-artifact-interface-contracts`; code revision
  `328994a` on a clean `ai-06-interface-contracts` working tree. Initial count: 77 tasks (67 agent,
  10 human); `make plan-status` selected this task.
- Audit inputs: [AUD-codebase-13](0001-govern-codebase-and-workflow-audit.md#audit-handoff).
- Amendments: none.

```markdown
#### refactor-stage-and-artifact-interface-contracts

Align foundational stage, extraction and artifact references before concrete adapters depend on them.

- Serves: `pipeline-control` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Audit inputs: [AUD-codebase-13](records/0001-govern-codebase-and-workflow-audit.md#audit-handoff).
- Dependencies: [Canonical contract registry](records/0010-contract-gov-establish-canonical-contract-registry.md);
[Contract identity and reference validation](records/0009-contract-gov-refactor-contract-identity-and-reference-validation.md).
[Inference and evaluation checkpoint](records/0038-eval-found-review-inference-and-evaluation-boundaries.md).
- User-visible outcome: Multi-silo inputs, structured source anchors, generation identities and honest
stage states
fit the shared interfaces rather than being hidden in string metadata or invented per adapter.
- Scope boundary: Refine existing Protocol/value types and fake conformance tests; do not implement domain
stages, a new orchestrator framework, or backend-specific logic in shared interfaces.
- Data and artifact paths: `src/arxiv_int/interfaces/{pipeline,stores,extraction}.py`, contract mappings,
`src/arxiv_int/features/catalog.py`, and `tests/interfaces/`.
- Execution path: Define typed source occurrences/anchors and generation-bearing artifact
references from
contracts; distinguish partial/empty/not-selected outcomes and conditional feature requirements;
keep fixture conformance dependency-light and adapters responsible for actual processing.
Include typed validation-result and transformation-run references in artifact interfaces; keep
Pandera/dbt implementation imports in optional adapters.
- Acceptance gates: Conformance fixtures cover duplicate paths across silos, cell/member anchors, distinct
generations of one partition, conditional GPU/UI features and failure/partial states; public
compatibility decisions are recorded; no optional heavy imports enter core; make ci passes.
- Documentation target: `docs/impl/current/pipeline-control.md`
- Review checkpoint: `review-pipeline-publication-and-reuse-boundaries`.
```

## Implementation

Refined the shared Protocol/value types so later adapters inherit one identity model instead of
string metadata and a single archive path.

- `SourceOccurrence` uses the source-occurrence contract identity
  `(silo_id, relative_path, scan_id)`, plus optional content hash, container/member paths, and
  status. Duplicate relative paths in different silos remain distinct. Relative paths are
  silo-relative POSIX paths; absolute, parent, and empty segments are refused.
- `SourceAnchor` carries page/character spans, sheet/cell ranges, bounding boxes, and original
  versus normalized coordinate space. `DocumentExtractor.extract` takes the occurrence; backend
  `metadata` is only for extras that are not identity or coordinates.
- `StageContext` takes `silos: tuple[SiloRoot, ...]` and a required `generation_id`.
  `archive_dir` is removed. `source_path()` joins a silo root without reading files.
- `DatasetRef` requires `generation_id`. Same dataset/contract/partition with different generations
  are different refs. `ArtifactStore.locate` must not collide them. Partition and option maps are
  frozen after construction.
- `StageOutcome` is `produced`, `partial`, `empty`, `failed`, or `not-selected`. `completed` and
  `skipped` are gone; cache hits belong to the later run ledger.
- `ValidationResultRef` and `TransformationRunRef` are identity/status pointers. Interface modules
  do not import Pandera or dbt. Failed/not-run validation cannot be publishable; only status `ok`
  transformation runs can be activatable.
- `STAGE_FEATURES` is a `StageFeatureSet` of required and conditional groups. GPU is conditional
  on `embed` and `facts`; UI is conditional on `report`. Setup profile requirements collect
  required groups only.
- Existing callers (`EvaluateStage`, Polars prepare) use the new constructors. No domain stage,
  orchestrator, or backend processing was added.

Public compatibility decisions are recorded in
[Pipeline control](../current/pipeline-control.md#compatibility).

Reused ODCS field names from `contracts/datasets/source-occurrences.odcs.yaml` and
`contracts/datasets/spans.odcs.yaml` without changing those documents. Reused
`EvaluateStage` and `run_polars_prepare` as the only in-tree `StageRunner` / `DatasetRef`
callers.

## Acceptance evidence

Commands use `DATA_DIR=/tmp/arxiv-int-interfaces-0040`. Fixtures are network-free and do not
prove real-archive quality or CUDA fit. The host has an NVIDIA GeForce RTX 4060 Ti (16380 MiB,
driver 595.84); this task did not run GPU workers.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Duplicate paths across silos | `tests/interfaces/test_source_identity.py` | pass |
| Cell and member anchors | `test_cell_anchor_names_sheet_range_and_grid`; `test_member_anchor_keeps_container_and_nested_path` | pass |
| Distinct generations of one partition | `tests/interfaces/test_artifact_refs.py` | pass |
| Failure/partial/empty/not-selected | `tests/interfaces/test_stage_outcomes.py` | pass |
| Conditional GPU/UI features | `tests/features/test_catalog.py`; `tests/features/test_report.py`; setup requirements | pass; investigation profile does not require `gpu` or `ui` |
| No optional heavy imports in core | `tests/interfaces/test_optional_imports.py` | pass; no pandera/dbt/polars in `interfaces/` |
| Public compatibility decisions | [Pipeline control](../current/pipeline-control.md#compatibility) | recorded |
| Documentation links and plan integrity | `make lint-doc-links`; `make lint-spec-plan`; `make plan-status` | pass; 76 tasks (66 agent, 10 human); next `implement-run-ledger-and-atomic-artifacts` |
| Formatting and required CI | `make format`; `make ci DATA_DIR=/tmp/arxiv-int-interfaces-0040` | pass; 912 tests, 45 heavy deselected |

## Audit handoff

Reviewed interface identity, frozen maps, dishonest publishable/activatable flags, catalog
conditionals, caller updates, and documentation links.

AUD-codebase-13 is resolved by typed multi-silo occurrences, structured anchors, generation-bearing
`DatasetRef`, honest stage outcomes, and conditional GPU/UI groups. No new orchestrator framework
was introduced.

`none identified` beyond the recorded compatibility breaks and the still-planned run ledger, DAG,
and publication work. No service, model job, port, or archive walk was started.

## Close or resume

Accepted. Plan task removed; dependents link this record. Counts moved from 77 to 76 tasks
(67 to 66 agent; 10 human unchanged). `pipeline-control` remains planned; typed interfaces are
available on [Pipeline control](../current/pipeline-control.md). Next agent work:
`implement-run-ledger-and-atomic-artifacts`. No review-owned service remains running. CUDA host
inventory was inspected (`nvidia-smi`: RTX 4060 Ti, 16380 MiB, about 14.5 GiB free) and was not
used as acceptance evidence. Whole-repo `make lint-md` still reports two pre-existing MD013
findings in unrelated `plan.md` evaluation-evidence tasks; edited pages pass pymarkdown.
