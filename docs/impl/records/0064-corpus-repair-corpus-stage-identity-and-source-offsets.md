# Corpus Stage Identity and Source Offset Repair

## Task and scope

- Id: `repair-corpus-stage-identity-and-source-offsets`; capability: `corpus-foundation`;
  checkpoint: [review-corpus-and-control-integrity](0063-corpus-review-corpus-and-control-integrity.md).
- State: accepted; the three reproduced defects have failing-then-passing regressions and required
  CI passes.
- Source: `docs/impl/plan.md`, `corpus-foundation`; created as the focused prerequisite repair for
  the three blocking findings of checkpoint
  [0063](0063-corpus-review-corpus-and-control-integrity.md). Code revision `d413383`; working tree
  clean at task start except the checkpoint's own documentation edits.
- Accepted task: the full block created for this repair.

```markdown
#### repair-corpus-stage-identity-and-source-offsets

Repair the three blocking findings of `review-corpus-and-control-integrity` before the corpus proof
and the lexical, classification and NLP consumers read corpus artifacts.

- Serves: `corpus-foundation` -- [Development integrity](../design/spec.md#development-integrity-and-review-checkpoints)
- Agent status: CLEAR
- Task kind: refactor
- Dependencies: `review-corpus-and-control-integrity`.
- User-visible outcome: A changed reviewed asset recomputes the stages that executed it, published
chunk source offsets address the extracted artifact a consumer actually reads, and inspection never
reports a superseded attempt with the accepted attempt's identity.
- Scope boundary: The three named defects and their regressions only. No new stage, contract,
migration, model or dependency; no reshaping of the stage-owner boundary beyond completing the
declarations it already requires.
- Data and artifact paths: `src/arxiv_int/pipeline/dag/stages.py`,
`src/arxiv_int/pipeline/control/owned.py`, `src/arxiv_int/pipeline/normalize/`,
`src/arxiv_int/extraction/publish.py`, `src/arxiv_int/pipeline/chunk/source.py`,
`src/arxiv_int/pipeline/dedupe/stage.py`, `src/arxiv_int/inspect/`, mirrored tests, and
`$DATA_DIR/architecture-review/<run-id>/`.
- Execution path: Reproduce each defect as a failing regression; complete the executed-asset
declarations; read and write document text without newline translation; bind each ledger row to the
attempt directory it names. Replay the fixture corpus chain and the operator Make workflow.
- Acceptance gates: Each defect has a regression that fails on the pre-repair tree and passes after;
a reviewed language-profile edit recomputes `normalize`, `dedupe` and `chunk` while `inventory` and
`extract` stay cached; published chunk source offsets select the same text in the extracted artifact
for a document containing carriage returns; superseded attempts report their own attempt number and
no ledger status. `make ci` passes.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

- Amendments: none.

## Implementation

### 1. Executed assets that no stage owned

`pipeline/control/owned.py` hashed only `pipeline/control`, `pipeline/dag`, `pipeline/run`,
`pipeline/quality` and `interfaces` as shared code, plus each stage's own `code_paths` and its
runner file. Every production stage executes far more first-party code than that, so a change to an
executed module left the reuse key unchanged and the next run reused stale artifacts.

`_SHARED_CODE` now also names the modules every stage executes through the run context, feature
gating, contract catalog and source-set snapshot (`contracts/catalog`, `contracts/generate`,
`contracts/sqlalchemy`, `features`, `metadata.py`, `pipeline/inventory/{model,snapshot,walk}.py`,
`pipeline/stage_paths.py`, `resources/paths.py`, `runtime/{config_model,containment}.py`). The
`pipeline/dag/stages.py` and `pipeline/run/fixtures.py` declaration files stay excluded as before,
so declaring a stage still cannot churn every other stage.

`pipeline/dag/stages.py` completes the per-stage declarations. `_LAKE_PATHS` now names the inventory
publication, validation and probing helpers the lake publisher reuses. `extract` owns
`pipeline/inventory/stage.py`; `normalize` owns `extraction/{artifacts,model}.py` and the reviewed
`resources/language` profiles; `dedupe` owns `pipeline/normalize/artifacts.py`; `chunk` owns
`pipeline/{dedupe/artifacts,normalize/artifacts,normalize/text}.py`; `evaluate` owns `retrieval` and
the three runtime configuration modules it reads. Declarations stay per-file where the dependency is
narrow, so an inventory-only edit does not recompute chunking.

The reviewed language profiles were the sharpest case: `normalizer_id` already mixes
`profile_fingerprint` into every published normalized document, but nothing in the reuse key
observed the file, so an edited profile produced a cached snapshot with the previous language
labels and no signal.

### 2. Newline translation across the extraction seam

`NormalizeStage._read` used `Path.read_text`, which applies universal newlines. Extraction publishes
the decoded text verbatim, so a Windows-authored document keeps its `\r\n` in the artifact and in the
`text_chars`/`text_sha256` the extract manifest records. Normalization saw a shorter view, produced
an identity offset map instead of the `\r\n` to `\n` runs `canonical_view` is written to record, and
`chunk` published `start_char`/`end_char` shifted by the number of preceding carriage returns.

Document text is now read and written as bytes at every seam: `normalize/stage.py`,
`normalize/publish.py`, `extraction/publish.py`, `dedupe/stage.py` and `chunk/source.py`. Contracts,
manifests and JSON sidecars are unchanged; they were already ASCII with explicit encodings.

### 3. Superseded attempts borrowing the accepted attempt's identity

`inspect/summarize.py` keyed ledger rows by stage name, then applied the current row to every attempt
directory the manifests walk returned. A retried stage therefore reported its superseded attempt
directory with the accepted attempt's number, status and cache decision. `inspect/lookup.py` gains
`ledger_attempts`, which maps each readable attempt directory onto the ledger row that actually names
it; `attempt_locations` reuses it. `_stage_rows` binds each directory to its own row, so a superseded
attempt keeps its directory-derived attempt number and the existing unclaimed-attempt rendering, and
a ledger row with no readable tree still falls through to `missing_attempt`.

Compatibility: no contract, migration, artifact layout or CLI change. Reuse keys change once, so the
first run after this repair recomputes; that is the intended effect of completing the declarations.
Current-state page: [corpus foundation](../current/corpus-foundation.md).

Limitations: the declaration set is enforced against the static first-party import closure of each
runner, so a module reached only through a runtime string import would still need a manual
declaration. Byte-exact IO fixes the translation defect; it does not make extraction emit a
normalized newline convention, which stays normalization's job.

## Acceptance evidence

Evidence root: `$DATA_DIR/architecture-review/0063/`.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Declaration completeness reproduces | `pytest tests/pipeline/dag/test_stage_declarations.py -q` on the pre-repair tree | 8 failed; every stage with a runner listed undeclared executed modules |
| Declaration completeness repaired | same command after the repair | 8 passed |
| Language profile is owned by normalize alone | `test_reviewed_language_profiles_are_owned_by_normalize_alone` | Pass; the declared digest equals `profile_fingerprint()` and no other corpus stage owns it |
| Language edit recomputes the right closure | `make forecast` then `make stage` for `inventory..chunk` after appending a newline to `resources/language/profiles.json` (`RUN_ID=run-9e4fddc56bc548cd9e735c90d2aeca7d`) | Pass; `inventory` and `extract` `cache_hit=true`, `normalize`/`dedupe`/`chunk` `cache_hit=false attempt=2`; the file was restored and `git diff` is empty |
| CR offsets reproduce | `pytest tests/pipeline/chunk -q` on the pre-repair `normalize/stage.py` | Fail; the chain retained no shifted offset map at all |
| CR offsets repaired | `test_source_offsets_address_carriage_returns_in_the_extracted_artifact` | Pass; the CRLF document yields a five-run offset map and two chunks whose published offsets select the same text in the extracted artifact |
| Pre-repair misalignment measured | scripted replay of the fixture chain on the pre-repair tree | Valid negative; offsets `12-81` and `48-105` selected text starting two characters early, versus `14-83` and `50-107` after the repair |
| Superseded attempt reproduces | `pytest tests/inspect/test_summarize.py -q` with `src/arxiv_int/inspect/` stashed | Fail on `test_superseded_attempt_never_borrows_the_accepted_attempt_identity` |
| Superseded attempt repaired | same test after the repair; `make inspect RUN_ID=run-9e4fddc56bc548cd9e735c90d2aeca7d` | Pass; `attempt-1` rows report `attempt=1 status=unknown` instead of the accepted `attempt=2 status=succeeded` |
| Operator workflow after repair | `make run-create`; `make forecast`; `make stage STAGE=preflight..chunk`; `make inspect` | Pass; see [checkpoint 0063](0063-corpus-review-corpus-and-control-integrity.md#acceptance-evidence) for the run ids and counts |
| Required repository gate | `make ci` | Pass; recorded in [checkpoint 0063](0063-corpus-review-corpus-and-control-integrity.md#acceptance-evidence) |

Fixture evidence only. No provided-archive corpus proof, extraction-quality, CUDA-throughput or
multi-terabyte claim follows from this repair.

## Audit handoff

Unresolved task-local audit notes: `none identified`.

Reviewed scope: the owned-asset declaration path, the document-text IO seams between extraction,
normalization, grouping and chunking, and the inspection attempt binding. The nonblocking notes the
checkpoint raised stay with their named owners; this repair does not touch reconciliation
materialization, the local control lock, duplicate-group chaining or Docling model identity.

## Close or resume

All acceptance gates pass. Next action: none; the repair is complete and
[checkpoint 0063](0063-corpus-review-corpus-and-control-integrity.md) closes on it. Indexed in the
[record index](README.md). Plan counts are reported by the checkpoint record. Capability change:
none added; the corpus stages' existing reuse, offset and inspection promises now hold.
