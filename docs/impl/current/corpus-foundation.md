# Corpus Foundation

Streaming inventory, tiered text extraction, normalization, reversible duplicate overlays, and
structure-aware chunking are available through the normal stage interface. The integration
checkpoint and provided-archive corpus proof remain
[planned](../plan.md#corpus-foundation----corpus-foundation). Implementation and acceptance
evidence: [record 0060](../records/0060-corpus-implement-streaming-inventory.md),
[record 0061](../records/0061-corpus-integrate-tiered-text-extraction.md), and
[record 0062](../records/0062-corpus-implement-normalization-dedupe-and-chunking.md).

## Operator workflow

Use the configured archive silos and operator roots. A created run and covering forecast are required:

```bash
make run-create
# Set RUN_ID to the id printed above.
make forecast RUN_ID="$RUN_ID"
make stage STAGE=preflight RUN_ID="$RUN_ID"
make stage STAGE=inventory RUN_ID="$RUN_ID"
make stage STAGE=extract RUN_ID="$RUN_ID"
make stage STAGE=normalize RUN_ID="$RUN_ID"
make stage STAGE=dedupe RUN_ID="$RUN_ID"
make stage STAGE=chunk RUN_ID="$RUN_ID"
make inspect RUN_ID="$RUN_ID" JSON=1
```

Refresh `make forecast` before repeating a completed stage, because the cache plan has changed.
An interrupted inventory retains completed file transactions; repeating the stage resumes after
metadata verification. Source changes require `make update` or a new run. A changed producer or
policy uses a separate checkpoint. The source archive is never modified, links are never followed,
and members are never extracted into source paths. Inventory uses CPU and storage, with no CUDA
worker or inference service.

## Tiered extraction

The `extract` stage consumes a checksum-validated inventory snapshot, including a reused upstream
snapshot from another run. It extracts each unique content hash once and maps duplicate physical
occurrences to that document. Plain text uses bounded codecs; the breadth lane runs Apache Tika
3.3.x through `iscc-tika` in an isolated subprocess; Docling supplies PDF/spreadsheet layout and
table cells; scanned PDFs opt into Tika's Tesseract OCR strategy; PNG/JPEG images use Tesseract TSV
word coordinates. Baseline and failed-lane reasons remain in tool metadata.

The stage writes immutable snapshots below `$RESULTS_DIR/normalized/{documents,spans,extraction}/`
and `$RESULTS_DIR/quarantine/extract/`. Documents retain raw/text hashes, extractor/version metadata
and quality counters. Spans retain offsets plus available page, sheet, row/column, cell range and
bounding-box anchors. Manifests report per-media-type text, anchor and table-cell coverage, and
rehash every referenced artifact before cache reuse. Generated Pandera document/span schemas and
source-anchor checks run before publication.

Inputs, extracted text, span counts, child execution time and captured output are bounded. Inventory
decompression limits still apply to members; macros and active Office content remain disabled.
Corrupt, encrypted, unsupported, empty and oversized inputs are quarantined with actionable reasons.
A completed extract that published documents is `produced` even when some inputs were quarantined,
so `normalize` consumes the snapshot. Incomplete scans remain `partial` and still halt.

For a new CUDA host, install Tesseract and the `rus`, `eng`, `deu`, and `ukr` language packs before
`make setup`; see [Workstation setup](../../guide/setup.md). Setup verifies those packs, installs the
locked extraction extra, and prefetches Docling layout/table assets under
`$MODEL_CACHE_DIR/docling/`. Extraction currently uses CPU/RAM; CUDA is available to later lanes but
is not required by this stage.

## Normalization, grouping and chunking

The `normalize` stage consumes a checksum-validated extraction snapshot and writes immutable views
below `$RESULTS_DIR/normalized/normalized-documents/` and `$RESULTS_DIR/quarantine/normalize/`.
Original extracted text is preserved. Canonical NFC text, a search/casefold view, and a reversible
offset map are stored per document. Language is scored against packaged offline profiles; short or
mixed snippets may remain `und`. Empty canonical text is quarantined without a content payload.

The `dedupe` stage proposes exact, normalized, MinHash/lexical, and edition groups into
`$RESULTS_DIR/normalized/duplicate-groups/` without deleting source or extracted records. One
representative is elected per group. Members may be suppressed from chunking only when the overlay
names that representative. Byte-identical files already collapse during extraction, so exact-hash
groups can be empty on a fixture that reuses content hashes.

The `chunk` stage reads normalized views and the duplicate overlay, skips suppressed members, and
writes `$RESULTS_DIR/normalized/chunks/`. Structure, table, and sentence chunkers keep source
character offsets. Table chunks repeat the header in every row group. Generated Pandera checks and
cross-partition identity uniqueness run before publication. Unchanged inputs reuse validated
snapshots. These stages use CPU and storage; CUDA is not required.

A bounded fixture Make run on this host published 14 normalized documents, four duplicate groups
with nine memberships and three suppressed members, and 91 chunks (one table, ninety text) over ten
representatives. Redacted counts live in
[record 0062](../records/0062-corpus-implement-normalization-dedupe-and-chunking.md). That result
does not establish provided-archive quality; the corpus proof remains open.

## Identities, coverage and storage

`pipeline/inventory/` streams descriptor-relative directory entries with a 64-level depth ceiling.
Each physical file is opened without following links, read in 1 MiB chunks and hashed with SHA-256.
Device, inode, mode, size, mtime and ctime checks bracket the read; a second descriptor verifies the
current pathname still identifies that file. A source-set metadata check compares the scan start
to the frozen run and catches observed changes
elsewhere during the scan. Such a change prevents sealing a snapshot.

Silo id, root-relative path and the ordered container-member address identify an occurrence.
Member addresses include their header ordinal, so duplicate names and nesting stay distinct.
Content hashes identify bytes independently of filenames and silo ids. Members retain their parent
content hash. SQLite scratch tables provide transactional file checkpoints, fixed-cache disk indexes,
exact duplicate counts and global occurrence-key uniqueness; they are not canonical store tables.
Only successful stable file transactions are reused. Failed reads are retried.

Physical artifacts live below:

```text
$RESULTS_DIR/normalized/inventory/contract_version=1.0.0/scan_id=<generation>/
  checkpoint-<producer-identity>.sqlite
  snapshot=<id>/
    bucket-<hex>-part-<sequence>.parquet
    bucket-<hex>-part-<sequence>.metadata.jsonl
    partitions.jsonl
    inventory.json
```

The Parquet rows implement the existing `source-occurrences` contract, including its partition key.
There is no canonical schema or migration change. The operational metadata sidecars join on
`occurrence_id` and retain size, MIME, encoding, parent hash, status and quarantine reason.
Archive-member temporary files use the resolved `TMP_DIR` and are closed on failure or cancellation.
Sixteen stable occurrence-id buckets use at most 256 rows per file; each PyArrow writer closes after
one batch, bounding both data and footer memory. Contract-derived Pandera schemas and batch rules,
plus inventory provenance checks, run before each partition is sealed. Invalid provenance fails
publication. The disk primary key covers the complete source set, including cross-batch duplicates.

`inventory.json` seals the streamed partition checksum index last. It records completed directory
scope, per-silo and global counts, physical source bytes separately from member-inclusive bytes,
duplicates, unsupported/encrypted inputs, and executed batch/global validation evidence. Incomplete
snapshots have no accepted manifest. Files already written by an interrupted publication are
unreferenced; inspection excludes these and checkpoint scratch. Later attempts write new snapshots.
The normal stage attempt and quality evidence remain under `$RUNS_DIR/<run-id>/`. Cache acceptance
rehashes every referenced Parquet and metadata file; a missing or corrupt partition triggers repair.

Completed directory scope means enumeration completed, not that every input was readable or
supported. Explicit quarantine rows preserve links, special files, unreadable files and archive
policy refusals. Missing/unreadable directories produce partial stage outcomes. The reconciliation
adapter consumes verified inventory classifications and withholds removals when source content
could not be observed, including file-to-link replacements. Its existing delta interface still
materializes source occurrences; this does not establish bounded-memory reconciliation at scale.

## Format policy and limits

Magic signatures recognize ZIP, TAR, gzip, PDF, OLE, RAR, 7z, PNG and JPEG. Text detection recognizes
ASCII, UTF-8 and Unicode BOMs, with bounded `charset-normalizer` candidates for Windows-1251 and
KOI8-R. Encoding detection is heuristic; ambiguous samples remain unknown. Inventory does not
classify language; extraction records normalized text without claiming language identification. A
PDF encryption marker is a conservative quarantine signal, not a complete PDF parser.

ZIP stored/deflated members and streaming TAR/TAR.gz members are inspected recursively. Limits per
physical container are 10,000 members, three nesting levels, 64 MiB per member, 256 MiB expanded
member bytes, a 100:1 expansion ratio and a 4 MiB ZIP central directory. TAR header reads and gzip
expansion are bounded too. ZIP64/multidisk, other ZIP compression methods, encrypted ZIP members,
unsafe member paths and links are explicitly refused. RAR, 7z, OLE and unknown binary formats retain
strong physical hashes with unsupported-format quarantine metadata. Corrupt containers and exceeded
budgets retain explicit incomplete-member evidence. No macros or embedded programs are executed.

## Quality and verification

The normal Make workflow has passed fixture and full operator-provided archive validation.
Physical files were accounted for and strongly hashed; published partitions passed checksum and
contract checks, metadata matched Parquet rows, and unchanged reruns reused validated outputs.
Tests cover source stability, provenance, multiple silos, duplicate content, unsafe or invalid
containers, interruption, resume and bounded working memory. Required CI passed.

Unsupported formats, encryption indicators and incomplete member coverage remain explicit
quarantine outcomes. These results do not establish extraction quality, universal container support,
multi-terabyte throughput or GPU fit. Validate each deployment against its own configured roots
using the operator workflow above; historical run artifacts are not required.

The [quality conclusion](../records/0060-corpus-implement-streaming-inventory.md#archive-inventory-quality-conclusion)
records inventory acceptance and its limits.
Normalization, grouping and chunking fixture evidence is in
[record 0062](../records/0062-corpus-implement-normalization-dedupe-and-chunking.md).
[Provided-archive corpus proof](../plan.md#prove-corpus-foundation-on-provided-archive) remains open.
