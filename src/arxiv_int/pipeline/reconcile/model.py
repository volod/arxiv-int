"""Typed source-manifest, delta, tombstone, and invalidation contracts."""

from collections.abc import Mapping
from dataclasses import dataclass

from arxiv_int.interfaces.tokens import require_relative_path, require_token

DELTA_SCHEMA = "arxiv-int.source-delta.v1"
MANIFEST_SCHEMA = "arxiv-int.source-manifest.v1"
TOMBSTONE_SCHEMA = "arxiv-int.source-tombstone.v1"
INVALIDATION_SCHEMA = "arxiv-int.invalidation.v1"
REBUILD_SCHEMA = "arxiv-int.rebuild.v1"
KINDS = frozenset({"add", "content-change", "path-rename", "remove"})


@dataclass(frozen=True, slots=True)
class SourceOccurrence:
    """One silo-relative file identity from a complete or partial scan."""

    silo_id: str
    relative_path: str
    content_hash: str
    stable: bool = True
    readable: bool = True
    container_path: str = ""
    member_path: str = ""

    def __post_init__(self) -> None:
        require_token(self.silo_id, "silo_id")
        require_relative_path(self.relative_path, "relative_path")
        require_token(self.content_hash, "content_hash")

    @property
    def path_key(self) -> str:
        """Stable path identity used to pair adds, changes, and removals."""
        return f"{self.silo_id}:{self.relative_path}"

    @property
    def occurrence_id(self) -> str:
        """Physical occurrence token including content identity."""
        return f"{self.path_key}:{self.content_hash}"


@dataclass(frozen=True, slots=True)
class SiloScan:
    """Per-silo completeness for one comparable source scan."""

    silo_id: str
    complete: bool
    readable: bool
    occurrences: tuple[SourceOccurrence, ...]
    reason: str = ""

    def __post_init__(self) -> None:
        require_token(self.silo_id, "silo_id")


@dataclass(frozen=True, slots=True)
class SourceManifest:
    """Complete comparable source inventory, or an explicit partial scan."""

    scan_id: str
    silos: tuple[SiloScan, ...]
    comparable: bool
    schema: str = MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        require_token(self.scan_id, "scan_id")
        if self.schema != MANIFEST_SCHEMA:
            raise ValueError(f"unsupported source-manifest schema {self.schema!r}")

    def occurrence_map(self) -> dict[str, SourceOccurrence]:
        """Index readable occurrences by path key."""
        found: dict[str, SourceOccurrence] = {}
        for silo in self.silos:
            for item in silo.occurrences:
                if item.readable:
                    found[item.path_key] = item
        return found

    def complete_silos(self) -> frozenset[str]:
        """Return silo ids whose scan may emit removal tombstones."""
        return frozenset(silo.silo_id for silo in self.silos if silo.complete and silo.readable)


@dataclass(frozen=True, slots=True)
class DeltaEvent:
    """One added, changed, renamed, or removed source occurrence."""

    kind: str
    silo_id: str
    relative_path: str
    content_hash: str
    previous_path: str = ""
    previous_hash: str = ""
    previous_silo_id: str = ""
    content_remains: bool = False

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"unknown delta kind {self.kind!r}")
        require_token(self.silo_id, "silo_id")
        require_relative_path(self.relative_path, "relative_path")
        require_token(self.content_hash, "content_hash")
        if self.previous_path and not self.previous_silo_id:
            raise ValueError("a previous path must name the silo it belonged to")


@dataclass(frozen=True, slots=True)
class SourceDelta:
    """Diff of two source manifests."""

    schema: str
    previous_scan_id: str
    current_scan_id: str
    comparable: bool
    events: tuple[DeltaEvent, ...]
    withheld_removals: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema != DELTA_SCHEMA:
            raise ValueError(f"unsupported source-delta schema {self.schema!r}")

    def of_kind(self, kind: str) -> tuple[DeltaEvent, ...]:
        """Return events of one kind."""
        return tuple(item for item in self.events if item.kind == kind)


@dataclass(frozen=True, slots=True)
class Tombstone:
    """Retained removal record; never a source-archive delete."""

    schema: str
    occurrence_id: str
    silo_id: str
    relative_path: str
    content_hash: str
    scan_id: str
    generation_id: str
    last_occurrence: bool
    reason: str = "remove"

    def __post_init__(self) -> None:
        if self.schema != TOMBSTONE_SCHEMA:
            raise ValueError(f"unsupported tombstone schema {self.schema!r}")
        require_token(self.occurrence_id, "occurrence_id")
        require_token(self.content_hash, "content_hash")


@dataclass(frozen=True, slots=True)
class InvalidationPlan:
    """Logical stale closure before physical prune."""

    schema: str
    stage: str
    roots: tuple[str, ...]
    marked: tuple[str, ...]
    bytes: int
    recompute_shards: int
    document_id: str = ""

    def __post_init__(self) -> None:
        if self.schema != INVALIDATION_SCHEMA:
            raise ValueError(f"unsupported invalidation schema {self.schema!r}")


@dataclass(frozen=True, slots=True)
class RebuildReport:
    """Isolated generation rebuild compared with a clean baseline."""

    schema: str
    run_id: str
    generation_id: str
    previous_generation_id: str
    checksums: Mapping[str, str]
    baseline_match: bool
    activated: bool
    quality_allowed: bool

    def __post_init__(self) -> None:
        if self.schema != REBUILD_SCHEMA:
            raise ValueError(f"unsupported rebuild schema {self.schema!r}")
        require_token(self.run_id, "run_id")
        require_token(self.generation_id, "generation_id")
