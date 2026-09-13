"""Resolve citations to original and current source locations."""

from collections.abc import Mapping
from pathlib import Path

from arxiv_int.query.evidence.model import (
    COPY_KIND,
    Citation,
    EvidenceCatalog,
    EvidenceError,
    EvidenceResolution,
    SourceLocation,
)
from arxiv_int.query.evidence.overlay import LocationTrack, overlay_events
from arxiv_int.query.evidence.schema import (
    ContractRow,
    occurrence_identity,
    occurrence_is_member,
    occurrence_physical_path,
)
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
    document_id = document.get("document_id")
    content_hash = document.get("content_hash")
    occurrences = tuple(
        item for item in catalog.occurrences if item.get("content_hash") == content_hash
    )
    if not occurrences:
        findings.append(f"no source occurrences for {document_id}")
    tracks = overlay_events(occurrences, catalog.events, document_id)
    roots = silo_roots or {}
    locations = tuple(
        item
        for track in tracks
        for item in _expand_track(track, document, roots, catalog.occurrences)
    )
    ambiguous = citation_ambiguous or _colliding_currents(tracks)
    if ambiguous:
        findings.append("ambiguous source locations")
    return EvidenceResolution(
        citation=citation,
        document_id=document_id,
        content_hash=content_hash,
        locations=locations,
        original_anchor=citation.original,
        normalized_anchor=citation.normalized,
        extractor_profile=document.get("extractor_profile"),
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


def _document_for(catalog: EvidenceCatalog, document_id: str) -> ContractRow | None:
    if not document_id:
        return None
    found = [item for item in catalog.documents if item.get("document_id") == document_id]
    return found[0] if found else None


def _expand_track(
    track: LocationTrack,
    document: ContractRow,
    silo_roots: Mapping[str, Path],
    occurrences: tuple[ContractRow, ...],
) -> tuple[SourceLocation, ...]:
    content_hash = track.occurrence.get("content_hash") or document.get("content_hash")
    physical_hash = _physical_hash(track.occurrence, occurrences, content_hash)
    primary = _location(
        track,
        current_path=track.current_path,
        role="source",
        content_hash=content_hash,
        physical_hash=physical_hash,
        silo_roots=silo_roots,
    )
    copies = tuple(
        _location(
            track,
            current_path=path,
            role=COPY_KIND,
            content_hash=content_hash,
            physical_hash=physical_hash,
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
    physical_hash: str | None,
    silo_roots: Mapping[str, Path],
) -> SourceLocation:
    occurrence = track.occurrence
    if role == COPY_KIND:
        physical = current_path
    elif occurrence_is_member(occurrence):
        physical = occurrence_physical_path(occurrence)
    else:
        physical = current_path
    status = location_status(
        silo_roots.get(occurrence.get("silo_id")) if physical_hash is not None else None,
        physical,
        physical_hash or "",
    )
    return SourceLocation(
        silo_id=occurrence.get("silo_id"),
        original_path=track.original_path,
        current_path=current_path,
        content_hash=content_hash,
        status=status,
        scan_id=occurrence.get("scan_id"),
        occurrence_id=occurrence_identity(occurrence),
        container_path=occurrence.get("container_path"),
        member_path=occurrence.get("member_path"),
        role=role,
    )


def _physical_hash(
    member: ContractRow, occurrences: tuple[ContractRow, ...], content_hash: str
) -> str | None:
    """Bind inventory member validation to its physical container in the same snapshot."""
    if not member.get("member_path").startswith("["):
        return content_hash
    hashes = {
        item.get("content_hash")
        for item in occurrences
        if not occurrence_is_member(item)
        and item.get("silo_id") == member.get("silo_id")
        and item.get("relative_path") == occurrence_physical_path(member)
        and item.get("scan_id") == member.get("scan_id")
        and item.get("generation_id") == member.get("generation_id")
    }
    return next(iter(hashes)) if len(hashes) == 1 and "" not in hashes else None


def _colliding_currents(tracks: tuple[LocationTrack, ...]) -> bool:
    seen: set[tuple[str, str]] = set()
    for track in tracks:
        if occurrence_is_member(track.occurrence):
            continue
        key = (track.occurrence.get("silo_id"), track.current_path)
        if key in seen:
            return True
        seen.add(key)
    return False
