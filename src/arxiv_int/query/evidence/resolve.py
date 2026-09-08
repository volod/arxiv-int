"""Resolve citations to original and current source locations."""

from collections.abc import Mapping
from pathlib import Path

from arxiv_int.query.evidence.model import (
    COPY_KIND,
    Citation,
    DocumentRecord,
    EvidenceCatalog,
    EvidenceError,
    EvidenceResolution,
    SourceLocation,
)
from arxiv_int.query.evidence.overlay import LocationTrack, overlay_events
from arxiv_int.query.evidence.validate import location_status

_CONTENT = "content"
_FACT = "fact"
_REPORT = "report"


def resolve_citation(
    catalog: EvidenceCatalog,
    token: str,
    *,
    kind: str = _CONTENT,
    silo_roots: Mapping[str, Path] | None = None,
) -> EvidenceResolution:
    """Map one content, fact, or report citation to every known source location."""
    citation, citation_ambiguous = _select_citation(catalog, token, kind)
    findings: list[str] = []
    document = _document_for(catalog, citation.document_id)
    if document is None:
        findings.append(f"unknown document {citation.document_id or token}")
        return EvidenceResolution(
            citation=citation,
            document_id=citation.document_id,
            content_hash="",
            locations=(),
            original_anchor=citation.original,
            normalized_anchor=citation.normalized,
            ambiguous=citation_ambiguous,
            findings=tuple(findings),
        )
    occurrences = tuple(
        item for item in catalog.occurrences if item.document_id == document.document_id
    )
    if not occurrences:
        findings.append(f"no source occurrences for {document.document_id}")
    tracks = overlay_events(occurrences, catalog.events, document.document_id)
    roots = silo_roots or {}
    locations = tuple(item for track in tracks for item in _expand_track(track, document, roots))
    ambiguous = citation_ambiguous or _colliding_currents(tracks)
    if ambiguous:
        findings.append("ambiguous source locations")
    return EvidenceResolution(
        citation=citation,
        document_id=document.document_id,
        content_hash=document.content_hash,
        locations=locations,
        original_anchor=citation.original,
        normalized_anchor=citation.normalized,
        extractor_profile=document.extractor_profile,
        ambiguous=ambiguous,
        findings=tuple(findings),
    )


def _select_citation(catalog: EvidenceCatalog, token: str, kind: str) -> tuple[Citation, bool]:
    if kind not in {_CONTENT, _FACT, _REPORT}:
        raise EvidenceError(f"unknown citation kind {kind!r}")
    if kind == _CONTENT:
        matches = [
            item
            for item in catalog.citations
            if item.kind == _CONTENT and item.document_id == token
        ]
        if len(matches) == 1:
            return matches[0], False
        return Citation(kind=_CONTENT, citation_id=token, document_id=token), False
    key = "fact_id" if kind == _FACT else "report_id"
    matches = [
        item
        for item in catalog.citations
        if item.kind == kind and token in {item.citation_id, getattr(item, key)}
    ]
    if not matches:
        raise EvidenceError(f"unknown {kind} citation {token}")
    documents = {item.document_id for item in matches}
    return matches[0], len(documents) > 1


def _document_for(catalog: EvidenceCatalog, document_id: str) -> DocumentRecord | None:
    if not document_id:
        return None
    found = [item for item in catalog.documents if item.document_id == document_id]
    return found[0] if found else None


def _expand_track(
    track: LocationTrack,
    document: DocumentRecord,
    silo_roots: Mapping[str, Path],
) -> tuple[SourceLocation, ...]:
    content_hash = track.occurrence.content_hash or document.content_hash
    primary = _location(
        track,
        current_path=track.current_path,
        role="source",
        content_hash=content_hash,
        silo_roots=silo_roots,
    )
    copies = tuple(
        _location(
            track,
            current_path=path,
            role=COPY_KIND,
            content_hash=content_hash,
            silo_roots=silo_roots,
        )
        for path in track.copies
    )
    return (primary, *copies)


def _location(
    track: LocationTrack,
    *,
    current_path: str,
    role: str,
    content_hash: str,
    silo_roots: Mapping[str, Path],
) -> SourceLocation:
    if role == COPY_KIND:
        physical = current_path
    elif track.occurrence.is_member:
        physical = track.occurrence.physical_path
    else:
        physical = current_path
    status = location_status(
        silo_roots.get(track.occurrence.silo_id),
        physical,
        content_hash,
    )
    return SourceLocation(
        silo_id=track.occurrence.silo_id,
        original_path=track.original_path,
        current_path=current_path,
        content_hash=content_hash,
        status=status,
        scan_id=track.occurrence.scan_id,
        occurrence_id=track.occurrence.identity,
        container_path=track.occurrence.container_path,
        member_path=track.occurrence.member_path,
        role=role,
    )


def _colliding_currents(tracks: tuple[LocationTrack, ...]) -> bool:
    seen: set[tuple[str, str]] = set()
    for track in tracks:
        if track.occurrence.is_member:
            continue
        key = (track.occurrence.silo_id, track.current_path)
        if key in seen:
            return True
        seen.add(key)
    return False
