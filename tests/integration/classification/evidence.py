"""Resolve classifier evidence through normalized views to original source occurrences."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from arxiv_int.classification.features import SPACE_PATH, SPACE_SEARCH, SPACE_TITLE
from arxiv_int.classification.text_features import word_spans
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.normalize.artifacts import view_path
from arxiv_int.pipeline.normalize.text import load_offset_map
from arxiv_int.pipeline.run.persist import load_json
from arxiv_int.query.evidence.model import EvidenceCatalog
from arxiv_int.query.evidence.resolve import resolve_citation
from arxiv_int.query.evidence.schema import parse_row
from tests.integration.corpus.artifacts import require, rows


def check_evidence(
    mappings: list[tuple[dict[str, Any], dict[str, Any]]],
    normalized: dict[str, dict[str, Any]],
    documents: dict[str, dict[str, Any]],
    normalization: dict[str, Any],
    inventory_manifest: Path,
    silos: tuple[SiloRoot, ...],
) -> dict[str, Any]:
    """Check every emitted span and every referenced document's initial source lookup."""
    catalog = EvidenceCatalog(
        documents=tuple(parse_row("documents", row) for row in documents.values()),
        occurrences=tuple(
            parse_row("source-occurrences", row)
            for row, _ in rows(inventory_manifest.parent, "occurrence_id")
        ),
    )
    root = Path(normalization["roots"]["normalized-documents"])
    spaces: Counter[str] = Counter()
    resolved: set[str] = set()
    member_locations = 0
    for row, extra in mappings:
        document_ids = set(extra["document_ids"])
        for document_id in sorted(document_ids - resolved):
            member_locations += _locate_document(catalog, document_id, row, silos)
            resolved.add(document_id)
        for evidence in json.loads(row["evidence_json"]):
            text = _evidence_text(evidence, row, document_ids, normalized, root)
            require(_addresses_token(evidence, text), "evidence span is not its exact token")
            if evidence["space"] == SPACE_SEARCH:
                source = evidence["source"]
                _check_original_offsets(
                    evidence,
                    root,
                    normalized[source]["normalized_document_id"],
                    documents[source]["text_chars"],
                )
            spaces[evidence["space"]] += 1
    return {
        "spansBySpace": dict(sorted(spaces.items())),
        "resolvedDocuments": len(resolved),
        "resolvedMemberLocations": member_locations,
        "sourceByteValidation": "complete inventory rehash; lookup preserves member links",
    }


def _locate_document(
    catalog: EvidenceCatalog, document_id: str, row: dict[str, Any], silos: tuple[SiloRoot, ...]
) -> int:
    resolution = resolve_citation(catalog, document_id)
    require(
        bool(resolution.locations) and not resolution.findings,
        "classification document cannot resolve to initial sources",
    )
    require(
        all(
            location.silo_id in {silo.silo_id for silo in silos}
            for location in resolution.locations
        ),
        "source lookup names unknown silo",
    )
    require(
        any(
            location.silo_id == row["silo_id"] and location.original_path == row["relative_path"]
            for location in resolution.locations
        ),
        "source lookup lost physical container",
    )
    return sum(bool(location.member_path) for location in resolution.locations)


def _evidence_text(
    evidence: dict[str, Any],
    row: dict[str, Any],
    document_ids: set[str],
    normalized: dict[str, dict[str, Any]],
    root: Path,
) -> str:
    require(
        set(evidence) == {"space", "source", "start", "end", "term"},
        "evidence shape is not the declared coordinate convention",
    )
    space, source = evidence["space"], evidence["source"]
    if space == SPACE_PATH:
        require(source == "path", "path evidence names another coordinate source")
        return str(row["relative_path"])
    if space == SPACE_TITLE:
        require(source == "title", "title evidence names another coordinate source")
        titles = {normalized[item]["metadata"].get("title", "") for item in document_ids}
        matches = [text for text in titles if _addresses_token(evidence, text)]
        require(len(matches) == 1, "title evidence is ambiguous or cannot be resolved")
        return str(matches[0])
    require(
        space == SPACE_SEARCH and source in document_ids,
        "search evidence references foreign document or unknown space",
    )
    identity = normalized[source]["normalized_document_id"]
    return view_path(root, "search", identity).read_text(encoding="utf-8")


def _addresses_token(evidence: dict[str, Any], text: str) -> bool:
    start, end = evidence["start"], evidence["end"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        return False
    offset = max(0, start - 1)
    return (evidence["term"], start - offset, end - offset) in word_spans(text[offset : end + 1])


def _check_original_offsets(
    evidence: dict[str, Any], root: Path, identity: str, original_chars: int
) -> None:
    offsets = load_json(view_path(root, "offsets", identity))
    search_map = load_offset_map(offsets["search_from_canonical"])
    canonical_map = load_offset_map(offsets["canonical_from_original"])
    start = canonical_map.to_source(search_map.to_source(evidence["start"]))
    end = canonical_map.to_source(search_map.to_source(evidence["end"]))
    require(0 <= start <= end <= original_chars, "evidence cannot map to original text bounds")
