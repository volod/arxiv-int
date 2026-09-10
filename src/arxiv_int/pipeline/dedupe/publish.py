"""Publish reversible duplicate and edition memberships as one immutable snapshot."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.dedupe.artifacts import (
    CONTRACT,
    DATASETS,
    GROUPS_KIND,
    LAYOUT,
    MANIFEST_KIND,
    PAIRS_FILE,
    SCHEMA,
)
from arxiv_int.pipeline.dedupe.group import Edge, method_counts
from arxiv_int.pipeline.dedupe.model import GroupMember, membership_id
from arxiv_int.pipeline.lake.artifacts import write_json_line
from arxiv_int.pipeline.lake.publish import SnapshotPublisher
from arxiv_int.pipeline.lake.validate import SnapshotValidator


class DedupePublisher:
    """Write one bounded duplicate-group snapshot beside its pair evidence."""

    def __init__(
        self,
        results: Path,
        generation: str,
        validator: SnapshotValidator,
        dedupe: str,
        batch_rows: int,
    ) -> None:
        self.dedupe = dedupe
        self.generation = generation
        self.snapshot = SnapshotPublisher(
            results, "dedupe", generation, validator, LAYOUT, DATASETS, batch_rows
        )
        self.groups: set[str] = set()
        self.memberships = 0
        self.suppressed = 0
        self.pairs = 0
        self._pairs: TextIO = self.snapshot.open_stream(MANIFEST_KIND, PAIRS_FILE)

    def add_members(self, members: Sequence[GroupMember], family: str) -> None:
        """Queue every membership of one grouping family as canonical rows."""
        for member in members:
            identity = membership_id(member.group_id, member.document_id)
            row: dict[str, object] = {
                "duplicate_membership_id": identity,
                "group_id": member.group_id,
                "document_id": member.document_id,
                "method": member.method,
                "role": member.role,
                "score": member.score,
                "suppressed": member.suppressed,
                "generation_id": self.generation,
                "contract_version": "1.0.0",
                "bucket": identity[0],
            }
            metadata: dict[str, object] = {
                "duplicate_membership_id": identity,
                "group_id": member.group_id,
                "document_id": member.document_id,
                "family": family,
                "dedupe_id": self.dedupe,
            }
            self.snapshot.add_row(CONTRACT, row, metadata)
            self.groups.add(member.group_id)
            self.memberships += 1
            self.suppressed += int(member.suppressed)

    def add_pair(self, edge: Edge, family: str) -> None:
        """Retain one proposed relation so every grouping decision stays auditable."""
        write_json_line(
            self._pairs,
            {
                "left": edge.left,
                "right": edge.right,
                "method": edge.method,
                "score": round(edge.score, 6),
                "family": family,
            },
        )
        self.pairs += 1

    def finish(
        self,
        normalization: Mapping[str, str],
        members: Sequence[GroupMember],
        evidence: Mapping[str, object],
    ) -> Path:
        """Seal the snapshot and record the upstream normalization it grouped."""
        return self.snapshot.finish(
            SCHEMA,
            {
                "duplicate_memberships": self.memberships,
                "duplicate_groups": len(self.groups),
                "suppressed_documents": self.suppressed,
                "proposed_pairs": self.pairs,
            },
            {
                "dedupe_id": self.dedupe,
                "normalization": dict(normalization),
                "methods": method_counts(members),
                **dict(evidence),
            },
        )

    def abort(self) -> None:
        """Remove unpublished scratch and any root moved before a failed seal."""
        self.snapshot.abort()

    def directory(self) -> Path:
        """Return the scratch root backing published duplicate-group batches."""
        return self.snapshot.directory(GROUPS_KIND)


def manifest_reference(manifest: Path) -> dict[str, Any]:
    """Return the checksum-bound pointer downstream stages revalidate."""
    return {"manifest": str(manifest), "sha256": hash_file(manifest)[0]}
