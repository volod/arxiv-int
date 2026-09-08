"""JSONL, latest-snapshot, and in-memory progress stores."""

import json
from pathlib import Path
from threading import Lock
from typing import Protocol

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.observability.logging.redact import redact_mapping
from arxiv_int.observability.metrics.constants import PROGRESS_LOG_NAME
from arxiv_int.observability.metrics.events import ProgressSnapshot, snapshot_from_mapping

_WRITE_LOCK = Lock()


class ProgressStore(Protocol):
    """Persist one throttled progress snapshot."""

    def record(self, snapshot: ProgressSnapshot) -> None:
        """Write or replace the latest snapshot for its run/stage."""


class MemoryProgressStore:
    """Keep snapshots in process for tests and file-less fixture runs."""

    def __init__(self) -> None:
        self.rows: list[ProgressSnapshot] = []

    def record(self, snapshot: ProgressSnapshot) -> None:
        self.rows.append(snapshot)

    def latest(self, stage: str | None = None) -> ProgressSnapshot | None:
        """Return the last snapshot, optionally for one stage."""
        rows = self.rows if stage is None else [row for row in self.rows if row.stage == stage]
        return rows[-1] if rows else None


class FileProgressStore:
    """Append JSONL under ``$RUNS_DIR/<run-id>/logs/`` and replace latest.json."""

    def __init__(self, run_dir: Path) -> None:
        self._directory = run_dir / "logs"
        self.path = self._directory / PROGRESS_LOG_NAME
        self.latest_path = self._directory / "latest.json"

    def record(self, snapshot: ProgressSnapshot) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        payload = redact_mapping(snapshot.as_dict())
        line = json.dumps(payload, sort_keys=True) + "\n"
        with _WRITE_LOCK, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        self.latest_path.write_text(normalize_json(payload) + "\n", encoding="utf-8")

    def load_latest(self) -> ProgressSnapshot | None:
        """Return the last on-disk snapshot when present."""
        if not self.latest_path.is_file():
            return None
        loaded = json.loads(self.latest_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return None
        return snapshot_from_mapping(loaded)


class FanoutProgressStore:
    """Write every snapshot to each configured store."""

    def __init__(self, stores: tuple[ProgressStore, ...]) -> None:
        self._stores = stores

    def record(self, snapshot: ProgressSnapshot) -> None:
        for store in self._stores:
            store.record(snapshot)
