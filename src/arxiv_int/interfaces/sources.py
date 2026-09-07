"""Typed source-occurrence and evidence-anchor identities from canonical contracts.

Physical occurrence identity is `(silo_id, relative_path, scan_id)`. Content hash and extracted
rendition identity stay separate. Anchors carry page/character, table cell, bounding-box, and
container/member coordinates instead of string metadata blobs.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from arxiv_int.interfaces.tokens import require_relative_path, require_token

CoordinateSpace = Literal["original", "normalized"]


@dataclass(frozen=True, slots=True)
class SiloRoot:
    """One named archive silo and the local root that holds its files."""

    silo_id: str
    root: Path

    def __post_init__(self) -> None:
        require_token(self.silo_id, "silo_id")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned box in the declared coordinate space."""

    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True, slots=True)
class SourceOccurrence:
    """One physical source location, including virtual container members."""

    silo_id: str
    relative_path: str
    scan_id: str
    content_hash: str = ""
    container_path: str = ""
    member_path: str = ""
    status: str = ""

    def __post_init__(self) -> None:
        require_token(self.silo_id, "silo_id")
        require_relative_path(self.relative_path, "relative_path")
        require_token(self.scan_id, "scan_id")
        if self.container_path:
            require_relative_path(self.container_path, "container_path")
        if self.member_path:
            require_relative_path(self.member_path, "member_path")

    @property
    def identity(self) -> tuple[str, str, str]:
        """Return the physical occurrence key independent of content hash."""
        return (self.silo_id, self.relative_path, self.scan_id)

    @property
    def is_member(self) -> bool:
        """Report whether this occurrence is a virtual container member."""
        return bool(self.member_path)

    def resolve(self, silo_root: Path) -> Path:
        """Join the silo root with the relative path without reading the file."""
        return silo_root.joinpath(*self.relative_path.split("/"))


@dataclass(frozen=True, slots=True)
class SourceAnchor:
    """Structured evidence coordinates on one source occurrence."""

    occurrence: SourceOccurrence
    space: CoordinateSpace = "original"
    start_char: int | None = None
    end_char: int | None = None
    page: int | None = None
    sheet: str = ""
    cell_range: str = ""
    row: int | None = None
    column: int | None = None
    bbox: BoundingBox | None = None
    kind: str = ""

    def __post_init__(self) -> None:
        if (
            self.start_char is not None
            and self.end_char is not None
            and self.end_char < self.start_char
        ):
            raise ValueError("end_char must be greater than or equal to start_char")
        if self.page is not None and self.page < 0:
            raise ValueError("page must be >= 0")
        if self.row is not None and self.row < 0:
            raise ValueError("row must be >= 0")
        if self.column is not None and self.column < 0:
            raise ValueError("column must be >= 0")

    @property
    def is_cell(self) -> bool:
        """Report whether this anchor names a spreadsheet or table cell."""
        return bool(
            self.sheet or self.cell_range or self.row is not None or self.column is not None
        )
