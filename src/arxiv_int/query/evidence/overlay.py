"""Apply portable path events onto sealed source occurrences."""

from dataclasses import dataclass, replace

from arxiv_int.query.evidence.model import COPY_KIND, OccurrenceRecord, PathEvent


@dataclass(frozen=True, slots=True)
class LocationTrack:
    """Original, current, and copy paths for one occurrence."""

    occurrence: OccurrenceRecord
    original_path: str
    current_path: str
    copies: tuple[str, ...]


def overlay_events(
    occurrences: tuple[OccurrenceRecord, ...],
    events: tuple[PathEvent, ...],
    document_id: str,
) -> tuple[LocationTrack, ...]:
    """Overlay ordered path events without rewriting occurrence provenance."""
    ordered = tuple(
        sorted(
            (item for item in events if item.document_id == document_id),
            key=lambda item: (item.recorded_at, item.event_id),
        )
    )
    tracks = [
        LocationTrack(item, item.relative_path, item.relative_path, ()) for item in occurrences
    ]
    for event in ordered:
        tracks = [_apply_event(track, event) for track in tracks]
    return tuple(tracks)


def _apply_event(track: LocationTrack, event: PathEvent) -> LocationTrack:
    if event.silo_id != track.occurrence.silo_id:
        return track
    if event.occurrence_id and event.occurrence_id != track.occurrence.identity:
        return track
    if event.kind == "initial":
        return replace(track, original_path=event.relative_path, current_path=event.relative_path)
    if event.kind in {"rename", "import"} and _rename_matches(track, event):
        return replace(track, current_path=event.relative_path)
    if event.kind == COPY_KIND:
        if event.relative_path in track.copies or event.relative_path == track.current_path:
            return track
        return replace(track, copies=(*track.copies, event.relative_path))
    return track


def _rename_matches(track: LocationTrack, event: PathEvent) -> bool:
    previous = event.previous_relative_path
    if not previous:
        return event.kind == "import"
    return previous in {
        track.current_path,
        track.original_path,
        track.occurrence.relative_path,
    }
