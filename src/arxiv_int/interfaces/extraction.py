"""Seam between the extraction stage and one text-extraction backend."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from arxiv_int.interfaces.sources import SourceAnchor, SourceOccurrence
from arxiv_int.interfaces.tokens import freeze_str_mapping, require_token


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Backend output for one source occurrence, before contract mapping."""

    text: str
    media_type: str
    occurrence: SourceOccurrence
    extractor_profile: str
    anchors: tuple[SourceAnchor, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_token(self.media_type, "media_type")
        require_token(self.extractor_profile, "extractor_profile")
        object.__setattr__(self, "metadata", freeze_str_mapping(self.metadata))


@runtime_checkable
class DocumentExtractor(Protocol):
    """Turn one source file into text without owning corpus contracts or storage.

    `feature` names the feature group that must be installed before the backend runs.
    """

    name: str
    feature: str

    def supports(self, media_type: str) -> bool:
        """Report whether this backend handles one detected media type."""

    def extract(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        """Extract text and structured anchors from one readable source file."""
