"""Apply portable path events onto sealed source occurrences."""

from dataclasses import dataclass, replace

from arxiv_int.query.evidence.model import COPY_KIND
from arxiv_int.query.evidence.schema import ContractRow, occurrence_identity


@dataclass(frozen=True, slots=True)
class LocationTrack:
    """Original, current, and copy paths for one occurrence."""

    occurrence: ContractRow
    original_path: str
    current_path: str
    copies: tuple[str, ...]


def overlay_events(
    occurrences: tuple[ContractRow, ...],
    events: tuple[ContractRow, ...],
    document_id: str,
) -> tuple[LocationTrack, ...]:
    """Overlay ordered path events without rewriting occurrence provenance."""
    ordered = tuple(
        sorted(
            (item for item in events if item.get("document_id") == document_id),
            key=lambda item: (item.get("event_time"), item.get("event_id")),
        )
    )
    tracks = [
        LocationTrack(item, item.get("relative_path"), item.get("relative_path"), ())
        for item in occurrences
    ]
    for event in ordered:
        tracks = [_apply_event(track, event) for track in tracks]
    return tuple(tracks)


def _apply_event(track: LocationTrack, event: ContractRow) -> LocationTrack:
    if event.get("silo_id") != track.occurrence.get("silo_id"):
        return track
    event_occurrence = event.get("occurrence_id")
    if event_occurrence and event_occurrence != occurrence_identity(track.occurrence):
        return track
    kind = event.get("kind")
    relative_path = event.get("relative_path")
    if kind == "initial":
        return replace(track, original_path=relative_path, current_path=relative_path)
    if kind in {"rename", "import"} and _rename_matches(track, event):
        return replace(track, current_path=relative_path)
    if kind == COPY_KIND:
        if relative_path in track.copies or relative_path == track.current_path:
            return track
        return replace(track, copies=(*track.copies, relative_path))
    return track


def _rename_matches(track: LocationTrack, event: ContractRow) -> bool:
    previous = event.get("previous_relative_path")
    if not previous:
        return event.get("kind") == "import"
    return previous in {
        track.current_path,
        track.original_path,
        track.occurrence.get("relative_path"),
    }
