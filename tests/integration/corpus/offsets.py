"""Source-anchor and offset cross-checks for provided-archive corpus results."""

from pathlib import Path
from typing import Any

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.normalize.artifacts import view_path
from arxiv_int.pipeline.normalize.text import canonical_view, load_offset_map, search_view
from arxiv_int.pipeline.run.persist import load_json
from tests.integration.corpus.accounting import quarantine
from tests.integration.corpus.artifacts import require, rows


def check_spans(
    documents: dict[str, dict[str, Any]], summary: dict[str, Any], inventory: dict[str, Any]
) -> int:
    """Require each span to resolve to a document and exact inventory source anchor."""
    count = 0
    for row, extra in rows(Path(summary["roots"]["spans"]), "span_id"):
        document = documents.get(row["document_id"])
        require(document is not None, "span document is missing")
        assert document is not None
        start, end = row["start_char"], row["end_char"]
        require(0 <= start <= end <= document["text_chars"], "span offsets are outside document")
        source = inventory.get(extra["occurrence_id"])
        require(source is not None, "span source occurrence is missing")
        assert source is not None
        require(source["content_hash"] == document["content_hash"], "span source content mismatch")
        require(
            source["silo_id"] == extra["silo_id"]
            and source["relative_path"] == extra["relative_path"]
            and source["members"] == extra["member_path"],
            "span source anchor mismatch",
        )
        count += 1
    require(count == summary["spans"], "span count mismatch")
    return count


def check_views(
    normalized: dict[str, dict[str, Any]], extraction: dict[str, Any], normalization: dict[str, Any]
) -> None:
    """Replay canonical/search transforms and complete offset maps for every document."""
    root = Path(normalization["roots"]["normalized-documents"])
    original_root = Path(extraction["roots"]["documents"]) / "text"
    for document, row in normalized.items():
        identity = row["normalized_document_id"]
        original = (original_root / f"{document}.txt").read_bytes().decode("utf-8")
        require(
            hash_file(view_path(root, "canonical", identity))[0] == row["normalized_sha256"],
            "normalized content hash mismatch",
        )
        canonical = canonical_view(original)
        search = search_view(canonical.text)
        require(
            view_path(root, "canonical", identity).read_bytes().decode("utf-8") == canonical.text,
            "canonical view mismatch",
        )
        require(
            view_path(root, "search", identity).read_bytes().decode("utf-8") == search.text,
            "search view mismatch",
        )
        offsets = load_json(view_path(root, "offsets", identity))
        require(
            offsets["canonical_from_original"] == canonical.offsets.serialize(),
            "canonical offset map mismatch",
        )
        require(
            offsets["search_from_canonical"] == search.offsets.serialize(),
            "search offset map mismatch",
        )
        require(row["text_chars"] == len(canonical.text), "normalized text count mismatch")


def check_chunk_row(
    row: dict[str, Any],
    extra: dict[str, Any],
    text: str,
    offsets: dict[str, Any],
    original_chars: int,
) -> None:
    """Recover the exact canonical body and any repeated table header from source bounds."""
    start, end = extra["canonical_start"], extra["canonical_end"]
    require(0 <= start < end <= len(text), "chunk canonical bounds invalid")
    mapping = load_offset_map(offsets["canonical_from_original"])
    require(
        row["start_char"] == mapping.to_source(start) and row["end_char"] == mapping.to_source(end),
        "chunk source offset mismatch",
    )
    require(
        0 <= row["start_char"] <= row["end_char"] <= original_chars, "chunk source bounds invalid"
    )
    require(
        extra["original_start"] == row["start_char"] and extra["original_end"] == row["end_char"],
        "chunk sidecar source bounds mismatch",
    )
    prefix = ""
    if extra["repeated_prefix_chars"]:
        span = extra["repeated_prefix_span"]
        require(isinstance(span, list) and len(span) == 2, "missing repeated header span")
        require(0 <= span[0] < span[1] <= len(text), "repeated header bounds invalid")
        prefix = text[span[0] : span[1]] + "\n"
    require(len(prefix) == extra["repeated_prefix_chars"], "repeated header size mismatch")
    require(row["text"] == prefix + text[start:end], "chunk text does not match its source views")


def check_chunks(
    normalized: dict[str, dict[str, Any]],
    documents: dict[str, dict[str, Any]],
    suppressed: set[str],
    summary: dict[str, Any],
    normalization: dict[str, Any],
) -> int:
    """Account for every retained, suppressed, or refused document and verify chunk offsets."""
    root = Path(normalization["roots"]["normalized-documents"])
    represented: set[str] = set()
    count = 0
    current = ""
    text = ""
    offsets: dict[str, Any] = {}
    for row, extra in rows(Path(summary["roots"]["chunks"]), "chunk_id"):
        document = row["document_id"]
        require(
            document in normalized and document not in suppressed,
            "chunk references missing or suppressed document",
        )
        identity = normalized[document]["normalized_document_id"]
        require(identity == extra["normalized_document_id"], "chunk normalized identity mismatch")
        if document != current:
            text = view_path(root, "canonical", identity).read_bytes().decode("utf-8")
            offsets = load_json(view_path(root, "offsets", identity))
            current = document
        check_chunk_row(row, extra, text, offsets, documents[document]["text_chars"])
        represented.add(document)
        count += 1
    refused = quarantine(Path(summary["roots"]["quarantine"]), "document_id")
    require(
        not represented & refused.keys() and not suppressed & refused.keys(),
        "chunk accounting overlaps",
    )
    require(
        represented | suppressed | refused.keys() == normalized.keys(),
        "unaccounted normalized document",
    )
    require(
        count == summary["chunks"] and len(represented) == summary["chunked_documents"],
        "chunk count mismatch",
    )
    require(
        len(refused) == summary["quarantined"]
        and len(suppressed) == summary["suppressed_documents"],
        "chunk quarantine/suppression count mismatch",
    )
    return count
