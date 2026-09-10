# Tiered Text Extraction

## Task and scope

- Id: `integrate-tiered-text-extraction`; capability: `corpus-foundation`.
- Checkpoint: `review-corpus-and-control-integrity`.
- State: accepted; deterministic and bounded CUDA-host fixture evidence passed.
- Source: `docs/impl/plan.md`; code revision `42f5a8a`; initially clean working tree.
- Initial count: 65 tasks (55 agent, 10 human).
- Amendments: none.

```markdown
#### integrate-tiered-text-extraction

Compose Tika, Docling, and OCR/layout fallbacks behind one evidence-preserving extractor interface.

- Serves: `corpus-foundation` --
[Russian-language and document analysis](../design/spec.md#russian-language-and-document-analysis)
- Agent status: RUN NEEDED
- Dependencies: [Streaming inventory](records/0060-corpus-implement-streaming-inventory.md);
[Deterministic schema generation](records/0011-contract-gov-implement-deterministic-schema-generation.md).
- User-visible outcome: Supported documents become normalized source spans with page/table/offset
evidence; failures are quarantined with actionable reasons.
- Scope boundary: Integrate existing engines and selection policy; do not build a new parser or
promise every proprietary format.
- Data and artifact paths: `$RESULTS_DIR/normalized/documents/`, `$RESULTS_DIR/normalized/spans/`,
`$RESULTS_DIR/quarantine/`, `src/arxiv_int/extraction/`, and representative format fixtures.
- Execution path: Run Tika as breadth baseline; route layout/table PDFs to Docling and scanned PDFs
to OCR; preserve tool versions, page/table/bounding-box and spreadsheet sheet/cell anchors,
container/member paths, raw hashes, and extraction quality; never execute macros or active content;
bound temp files,
child processes, timeouts, and decompression; register `extract` with the normal stage interface and
run it against a bounded authorized archive when available after deterministic checks pass.
Validate emitted document/span batches with shared Pandera schemas and existing source-anchor
checks; preserve explicit quarantine and incomplete-coverage results.
- Acceptance gates: The reviewed extraction fixture reports per-format text, table, and anchor
coverage; corrupt/encrypted/oversized inputs fail safely; repeated content hashes reuse outputs;
source files remain unchanged; the normal `make stage STAGE=extract` run produces inspectable
artifacts on the declared fixture or authorized archive, and its redacted result is recorded in current-state
documentation.
- Documentation target: `docs/impl/current/corpus-foundation.md`
- Review checkpoint: `review-corpus-and-control-integrity`.
```

## Implementation

`src/arxiv_int/extraction/` now owns one typed router over bounded plain-text, native `iscc-tika`,
Docling and Tesseract adapters. Tika runs in a killable subprocess with Office macros and inline
image extraction disabled; baseline parsing disables OCR and the scanned-PDF lane explicitly enables
Tesseract with `rus+eng+deu+ukr`. Docling runs offline against setup-prefetched layout/table models.
Images enforce a pixel budget before Tesseract TSV extraction. Time, input, output, span and
inventory decompression limits are explicit.

The stage consumes the exact checksum-validated upstream inventory artifact, including safe
cross-run inventory reuse, materializes source/member bytes only into bounded scratch, extracts each
content hash once and preserves every occurrence. It writes contract-derived Parquet batches, text,
rich anchor sidecars, actionable quarantine and a checksum index into immutable generation/snapshot
roots. Cache reuse rehashes every referenced artifact. The extraction quality boundary records the
already executed Pandera and source-anchor checks instead of the generic unexecuted placeholder.

Setup now includes the locked extraction extra. It verifies Tesseract plus Russian, English, German
and Ukrainian language data without invoking `sudo`, reports the exact Debian/Ubuntu install command,
and prefetches or offline-checks Docling assets under `$MODEL_CACHE_DIR/docling/`. The setup,
operator and development guides document the portable CUDA-host procedure.

## Acceptance evidence

Evidence root: `$DATA_DIR/extraction/0061/`.

| Gate | Exact command/test/artifact | Result and limit |
| --- | --- | --- |
| Prerequisites and selection | `make plan-status`; records 0011 and 0060 | Pass; task selected with 65 open tasks |
| Portable host setup | `make setup-config`; `make setup-env`; `make setup-models`; `tesseract --list-langs` | Pass; Tesseract 5.3.4 has `deu`, `eng`, `osd`, `rus`, `ukr`; extraction extra installed and Docling cache reused |
| Deterministic behavior | `pytest tests/extraction tests/runtime/setup tests/pipeline/dag tests/features/test_report.py -q` | Pass; routing, bounds, corruption, deduplication, contracts, anchors, setup remediation and upstream reuse covered |
| Multi-format stage run | `make stage STAGE=extract RUN_ID=run-657a927dec0741fe9acc94c748e25986` | Stage published successfully with honest partial outcome: 7 unique documents, 19 spans, 2 expected quarantines and 1 duplicate reuse |
| Format coverage | `.../generation_id=run-657a927dec0741fe9acc94c748e25986/snapshot=7889b78d2c09425e883408f5278733bd/extraction.json` | Pass: PDF 66/70 anchored chars with 4 table cells; XLSX 20/23 with 4 table cells; ZIP 50/50; PNG 27/32 with 6 word boxes; text 61/61 |
| Safe failures and source integrity | fixture `corrupt.pdf`, `encrypted.pdf`; `$DATA_DIR/extraction/0061/source-after.check` | Pass; corrupt input exhausted all lanes, encryption was quarantined by inventory, and all fixture SHA-256 checks matched |
| Required repository gate | `make ci` | Pass on 2026-09-09 after optional-backend isolation; final post-review rerun recorded below |
| Dependency/setup diagnostics | `make quality`; `make build`; `make quality-report` | Coverage passed 1,218 tests at 86%; `make quality` stopped only on 23 pre-existing Markdown line-length findings, then source/wheel build passed separately; no extraction file exceeds 250 lines |

## Audit handoff

Unresolved task-local audit notes: `none identified`.

Self-review found and repaired three host-only integration defects: production extraction was blocked
by the generic unexecuted quality boundary; cross-run inventory reuse did not expose its producer
manifest to extraction; and zero-valued Tika page counts created zero-length OCR anchors. The final
fixture proves the first two and reports full PDF offset coverage after the third. Quarantine tool
errors retain the final parser reason while removing host-specific executable and scratch paths.

The late independent audit was based on the pre-acceptance tree. Its remaining concrete consistency
findings were repaired: source-facing member anchors now use the innermost relative member path while
sidecars retain the full ordered archive address, and project/operator current-state guidance names
the shipped extraction feature and runner. An empty OCR document is not truth-tested back to sparse
baseline text because `ExtractedDocument` has normal dataclass truth semantics; the stage explicitly
quarantines empty text. The standard `.venv` path is the repository's documented Make/uv contract.

The representative table evidence includes spreadsheet cells. PDF table recovery depends on Docling
recognizing the source layout; malformed or unusually sparse PDFs can still fall back to OCR or
baseline text and are not promised universal table recovery. OCR and Docling are CPU/RAM lanes in
this stage; this run is not a CUDA throughput or multi-terabyte quality claim.

## Close or resume

Accepted. The next consumer is `implement-normalization-dedupe-and-chunking`; the milestone review
`review-corpus-and-control-integrity` remains responsible for cross-task corpus/control concerns.

Updated corpus current-state and setup/operator/development guidance, replaced the downstream raw
task dependency with this accepted record, and removed only `integrate-tiered-text-extraction` from
the forward plan. Counts moved from 65 to 64 tasks (55 to 54 agent; 10 human unchanged). The next
eligible agent task is `implement-normalization-dedupe-and-chunking`.

No human-review handoff applies. No service was started. All task processes exited; immutable product
artifacts remain under the configured results root and tool evidence under `$DATA_DIR/extraction/0061/`.
No commit or push was made.
