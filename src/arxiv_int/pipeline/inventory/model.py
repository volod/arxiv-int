"""Bounded inventory policy and provenance-bearing observations."""

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class InventoryPolicy:
    """Fixed resource ceilings, fingerprinted with the producing code."""

    batch_rows: int = 256
    read_bytes: int = 1_048_576
    sample_bytes: int = 65_536
    directory_depth: int = 64
    archive_depth: int = 3
    archive_members: int = 10_000
    member_bytes: int = 67_108_864
    expanded_bytes: int = 268_435_456
    central_directory_bytes: int = 4_194_304
    expansion_ratio: int = 100

    def __post_init__(self) -> None:
        if any(value < 1 for value in asdict(self).values()):
            raise ValueError("inventory limits must be positive")


@dataclass(frozen=True, slots=True)
class Observation:
    """A location or member; a missing digest never invents content identity."""

    silo_id: str
    relative_path: str
    members: tuple[str, ...] = ()
    content_hash: str | None = None
    size: int = 0
    mime: str = "application/octet-stream"
    encoding: str | None = None
    status: str = "ready"
    reason: str | None = None
    parent_hash: str | None = None

    @property
    def occurrence_id(self) -> str:
        identity = json.dumps([self.silo_id, self.relative_path, self.members], ensure_ascii=True)
        return hashlib.sha256(identity.encode("ascii")).hexdigest()

    def contract_row(self, scan_id: str, generation_id: str) -> dict[str, str | None]:
        """Use the existing canonical source-occurrences schema without extra columns."""
        return {
            "occurrence_id": self.occurrence_id,
            "bucket": self.occurrence_id[0],
            "silo_id": self.silo_id,
            "relative_path": self.relative_path,
            "scan_id": scan_id,
            "content_hash": self.content_hash,
            "container_path": self.relative_path if self.members else None,
            "member_path": json.dumps(self.members, ensure_ascii=True) if self.members else None,
            "status": self.status,
            "generation_id": generation_id,
            "contract_version": "1.0.0",
        }

    def metadata(self) -> dict[str, object]:
        """Operational sidecar metadata joined by the canonical occurrence key."""
        return {"occurrence_id": self.occurrence_id, **asdict(self)}


DEFAULT_POLICY = InventoryPolicy()
