"""Bounded staging, contract validation, and atomic publication of lake snapshots."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import TextIO
from uuid import uuid4

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.inventory.publish import atomic_json
from arxiv_int.pipeline.lake.artifacts import (
    abort_publication,
    record_file,
    snapshot_roots,
    snapshot_summary,
)
from arxiv_int.pipeline.lake.batches import write_batch
from arxiv_int.pipeline.lake.validate import SnapshotValidator

MANIFEST_KIND = "manifest"


class SnapshotPublisher:
    """Write validated batches into scratch and seal one immutable snapshot."""

    def __init__(
        self,
        results: Path,
        stage: str,
        generation: str,
        validator: SnapshotValidator,
        layout: Mapping[str, str],
        datasets: Mapping[str, str],
        batch_rows: int,
    ) -> None:
        if MANIFEST_KIND not in layout:
            raise ValueError("snapshot layout must declare a manifest root")
        self.results = results
        self.stage = stage
        self.generation = generation
        self.validator = validator
        self.layout = dict(layout)
        self.datasets = dict(datasets)
        self.batch_rows = batch_rows
        self.snapshot = uuid4().hex
        self.staging = results / f".{stage}-{self.snapshot}.tmp"
        self.staging.mkdir(parents=True)
        # The manifest kind is the staging root itself so that manifest-scoped
        # sidecars keep their recorded relative paths after the final move.
        self.kinds = {
            name: self.staging if name == MANIFEST_KIND else self.staging / name
            for name in self.layout
        }
        for path in self.kinds.values():
            path.mkdir(parents=True, exist_ok=True)
        self._rows: dict[str, list[dict[str, object]]] = {name: [] for name in self.datasets}
        self._metadata: dict[str, list[dict[str, object]]] = {name: [] for name in self.datasets}
        self._parts: dict[str, int] = {name: 0 for name in self.datasets}
        self._streams: dict[str, TextIO] = {}
        self._stream_kinds: dict[str, str] = {}
        self._moved: list[Path] = []
        self._sealed = False
        self._files = (self.kinds[MANIFEST_KIND] / "files.jsonl").open("w", encoding="ascii")

    def directory(self, kind: str) -> Path:
        """Return the scratch directory backing one logical artifact kind."""
        return self.kinds[kind]

    def open_stream(self, kind: str, name: str) -> TextIO:
        """Open one appended JSON-lines sidecar that is checksummed at seal time."""
        handle = (self.kinds[kind] / name).open("w", encoding="ascii")
        self._streams[name] = handle
        self._stream_kinds[name] = kind
        return handle

    def record(self, kind: str, path: Path) -> None:
        """Add one already written artifact to the streamed checksum index."""
        record_file(self._files, kind, path, self.kinds[kind])

    def add_row(self, contract: str, row: dict[str, object], metadata: dict[str, object]) -> None:
        """Queue one canonical row and its sidecar; flush when the batch is full."""
        self._rows[contract].append(row)
        self._metadata[contract].append(metadata)
        if len(self._rows[contract]) >= self.batch_rows:
            self.flush(contract)

    def flush(self, contract: str) -> None:
        """Validate and seal one buffered batch for a single contract."""
        rows = self._rows[contract]
        if not rows:
            return
        kind = self.datasets[contract]
        for path in write_batch(
            self.validator[contract],
            rows,
            self._metadata[contract],
            self.kinds[kind],
            self._parts[contract],
        ):
            self.record(kind, path)
        self._parts[contract] += 1
        rows.clear()
        self._metadata[contract].clear()

    def finish(self, schema: str, counts: Mapping[str, int], extra: Mapping[str, object]) -> Path:
        """Seal checksums last, then move every root into its immutable snapshot."""
        for contract, kind in self.datasets.items():
            self.flush(contract)
            self.validator.check_identities(contract, self.kinds[kind])
        for name, handle in self._streams.items():
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            kind = self._stream_kinds[name]
            record_file(self._files, kind, self.kinds[kind] / name, self.kinds[kind])
        self._files.flush()
        os.fsync(self._files.fileno())
        self._files.close()
        final = snapshot_roots(self.results, self.layout, self.generation, self.snapshot)
        for path in final.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        for name, source in self.kinds.items():
            if name == MANIFEST_KIND:
                continue
            source.replace(final[name])
            self._moved.append(final[name])
        summary = snapshot_summary(
            schema,
            self.generation,
            {contract: "1.0.0" for contract in self.datasets},
            final,
            counts,
            self.validator.fingerprint,
            hash_file(self.staging / "files.jsonl")[0],
        )
        summary.update(extra)
        atomic_json(self.staging / f"{self.stage}.json", summary)
        self.staging.replace(final[MANIFEST_KIND])
        self._sealed = True
        return final[MANIFEST_KIND] / f"{self.stage}.json"

    def abort(self) -> None:
        """Remove unpublished scratch while preserving already published roots."""
        abort_publication(
            self.staging, (self._files, *self._streams.values()), self._moved, self._sealed
        )
