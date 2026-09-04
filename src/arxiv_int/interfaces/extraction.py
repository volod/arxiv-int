"""Seam between the extraction stage and one text-extraction backend."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Backend output for one source file, before contract mapping and normalization."""

    text: str
    media_type: str
    metadata: Mapping[str, str]


@runtime_checkable
class DocumentExtractor(Protocol):
    """Turn one source file into text without owning corpus contracts or storage.

    `feature` names the feature group that must be installed before the backend runs.
    """

    name: str
    feature: str

    def supports(self, media_type: str) -> bool:
        """Report whether this backend handles one detected media type."""

    def extract(self, source: Path) -> ExtractedDocument:
        """Extract text and backend metadata from one readable source file."""
